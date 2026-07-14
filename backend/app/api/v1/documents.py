import os
import uuid
import hashlib
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import DocumentOut
from app.tasks.ingestion import process_document_task

router = APIRouter()

# Define local uploads path (backend/uploads/)
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=List[DocumentOut], status_code=status.HTTP_202_ACCEPTED)
async def upload_documents(
    project_id: uuid.UUID = Form(...),
    files: List[UploadFile] = File(...),
    chunk_strategy: str = Form("fixed_size"),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Upload one or more documents.
    Performs multi-tenant validation, SHA256 checksum duplicate checks, 
    automatic version increments for filename revisions, and triggers Celery background processing.
    """
    # 1. Multi-Tenant Project Check
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The specified project was not found."
        )
    if project.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload to this project."
        )

    processed_docs = []

    for file in files:
        # Read file contents and compute hash
        content = await file.read()
        sha256_hash = hashlib.sha256(content).hexdigest()
        
        # 2. Duplicate Check
        stmt_dup = select(Document).where(
            Document.project_id == project_id,
            Document.duplicate_hash == sha256_hash
        )
        res_dup = await db.execute(stmt_dup)
        duplicate_doc = res_dup.scalar_one_or_none()
        
        if duplicate_doc:
            # Skip duplicate files to prevent double-processing and save resources
            print(f"[Upload] Skipping duplicate file: {file.filename}")
            continue

        # 3. Version Control (Revision management)
        # Check if a file with the same name already exists in this project
        stmt_ver = select(func.max(Document.version)).where(
            Document.project_id == project_id,
            Document.filename == file.filename
        )
        res_ver = await db.execute(stmt_ver)
        max_version = res_ver.scalar() or 0
        new_version = max_version + 1

        # 4. Save to Disk
        ext = os.path.splitext(file.filename)[1].lstrip(".").lower()
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        file_size = len(content)

        # 5. Create Document DB record
        doc = Document(
            filename=file.filename,
            file_type=ext,
            file_size=file_size,
            file_path=file_path,
            status="pending",
            duplicate_hash=sha256_hash,
            version=new_version,
            meta_data={
                "original_filename": file.filename,
                "chunk_strategy": chunk_strategy,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            },
            project_id=project_id
        )
        db.add(doc)
        await db.flush()  # Populate doc.id

        
        # 6. Trigger Asynchronous Processing
        process_document_task.delay(str(doc.id))
        processed_docs.append(doc)

    if not processed_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files processed. All uploaded files were detected as duplicates."
        )

    await db.commit()
    for d in processed_docs:
        await db.refresh(d)
        
    return processed_docs

@router.get("/", response_model=List[DocumentOut])
async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    List all documents in a specific project.
    """
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    if project.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project's documents."
        )

    stmt_docs = select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    res_docs = await db.execute(stmt_docs)
    return res_docs.scalars().all()

@router.get("/{document_id}/preview")
async def preview_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Stream or download the original raw uploaded document.
    """
    stmt = select(Document).where(Document.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Multi-tenant context check via project lookup
    stmt_proj = select(Project).where(Project.id == doc.project_id)
    res_proj = await db.execute(stmt_proj)
    project = res_proj.scalar_one_or_none()
    
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to preview this document."
        )
        
    if not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File has been deleted from server storage."
        )
        
    return FileResponse(doc.file_path, filename=doc.filename)
