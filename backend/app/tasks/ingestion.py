import os
import uuid
import asyncio
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.project import Project
from app.models.chunk import Chunk, ChunkEmbedding
from app.services.extractor import DocumentExtractor
from app.services.chunker import ChunkerService
from app.services.embedding import EmbeddingService
from app.core.config import settings


async def async_process_document(document_id: str):
    """
    Asynchronous runner for document ingestion.
    Performs text extraction, then partitions text into semantic chunks and bulk inserts them.
    """
    async with SessionLocal() as db:
        # Fetch document from DB
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            print(f"[Ingestion] Document ID '{document_id}' not found.")
            return

        print(f"[Ingestion] Starting processing pipeline for: {doc.filename}")
        doc.status = "processing"
        await db.commit()

        try:
            # 1. File Validation
            if not os.path.exists(doc.file_path):
                raise FileNotFoundError(f"Raw file missing from uploads: {doc.file_path}")

            # 2. Virus Scan Mock
            print(f"[Ingestion] Scanning {doc.filename} for malware...")
            await asyncio.sleep(0.5)

            # 3. Text & Layout Extraction
            print(f"[Ingestion] Extracting text from {doc.filename} (Type: {doc.file_type})")
            extraction_result = DocumentExtractor.extract(doc.file_path, doc.file_type)

            # Resolve chunking config (Fallback cascade: Document -> Global Default)
            doc_meta = doc.meta_data if doc.meta_data else {}
            chunk_strategy = doc_meta.get("chunk_strategy") or "fixed_size"
            chunk_size = int(doc_meta.get("chunk_size") or 500)
            chunk_overlap = int(doc_meta.get("chunk_overlap") or 50)


            # 4. Text Chunking
            print(f"[Ingestion] Chunking text via strategy: {chunk_strategy} (size: {chunk_size}, overlap: {chunk_overlap})")
            chunks_data = ChunkerService.chunk_document(
                text=extraction_result.text,
                strategy=chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # Delete any existing chunks for this document (re-processing support)
            stmt_delete = select(Chunk).where(Chunk.document_id == doc.id)
            existing_chunks_res = await db.execute(stmt_delete)
            for old_chunk in existing_chunks_res.scalars().all():
                await db.delete(old_chunk)
            await db.flush()

            # 5. Bulk Create Chunk Records
            chunk_objects = []
            for item in chunks_data:
                chunk_obj = Chunk(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    content=item["content"],
                    chunk_index=item["chunk_index"],
                    page_number=item["page_number"],
                    meta_data=item["meta_data"]
                )
                chunk_objects.append(chunk_obj)
            
            db.add_all(chunk_objects)
            await db.flush()

            # 6. Generate Vector Embeddings in batches
            if chunk_objects:
                chunk_texts = [c.content for c in chunk_objects]
                print(f"[Ingestion] Generating embeddings for {len(chunk_texts)} chunks using: {settings.EMBEDDING_PROVIDER}")
                embeddings = EmbeddingService.get_embeddings(chunk_texts)
                
                # Bulk Create ChunkEmbedding Records
                embedding_objects = []
                for i, chunk_obj in enumerate(chunk_objects):
                    model_name = settings.OPENAI_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "openai" else settings.HUGGINGFACE_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "huggingface" else "mock-embedding-1536"
                    emb_obj = ChunkEmbedding(
                        id=uuid.uuid4(),
                        chunk_id=chunk_obj.id,
                        embedding=embeddings[i],
                        model_name=model_name
                    )
                    embedding_objects.append(emb_obj)
                
                db.add_all(embedding_objects)
                await db.flush()

            # 7. Compile Metadata & Analytics
            full_metadata = doc.meta_data.copy() if doc.meta_data else {}
            full_metadata.update(extraction_result.metadata)
            
            full_metadata["language"] = extraction_result.language
            full_metadata["needs_ocr"] = extraction_result.needs_ocr
            full_metadata["word_count"] = len(extraction_result.text.split())
            full_metadata["char_count"] = len(extraction_result.text)
            
            # Chunking and Embedding stats
            full_metadata["chunk_count"] = len(chunk_objects)
            full_metadata["chunk_strategy"] = chunk_strategy
            full_metadata["chunk_size"] = chunk_size
            full_metadata["chunk_overlap"] = chunk_overlap
            
            model_name = settings.OPENAI_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "openai" else settings.HUGGINGFACE_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "huggingface" else "mock-embedding-1536"
            full_metadata["embedding_model"] = model_name
            full_metadata["embedding_provider"] = settings.EMBEDDING_PROVIDER

            # Update Document fields
            doc.meta_data = full_metadata
            doc.status = "completed"
            
            await db.commit()
            print(f"[Ingestion] Pipeline successfully completed for {doc.filename}. Generated {len(chunk_objects)} chunks and embeddings.")

            
        except Exception as e:
            print(f"[Ingestion] Ingestion pipeline failed for {doc.filename}: {e}")
            import traceback
            traceback.print_exc()
            doc.status = "failed"
            error_metadata = doc.meta_data.copy() if doc.meta_data else {}
            error_metadata["error"] = str(e)
            doc.meta_data = error_metadata
            await db.commit()

@celery_app.task(name="app.tasks.ingestion.process_document_task")
def process_document_task(document_id: str):
    """
    Celery entrypoint wrapping the async DB execution in an asyncio event loop.
    """
    asyncio.run(async_process_document(document_id))
