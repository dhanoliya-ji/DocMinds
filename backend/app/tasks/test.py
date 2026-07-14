import time
from app.core.celery_app import celery_app

@celery_app.task(name="app.tasks.test.add_numbers_task")
def add_numbers_task(x: int, y: int) -> int:
    """A simple test task that sums two numbers after a simulated delay."""
    print(f"Executing add_numbers_task with x={x}, y={y}")
    time.sleep(2)  # Simulate execution delay
    result = x + y
    print(f"add_numbers_task completed. Result: {result}")
    return result

@celery_app.task(name="app.tasks.test.dummy_process_document_task")
def dummy_process_document_task(document_id: str) -> dict:
    """A dummy task simulating a multi-step document processing pipeline."""
    print(f"Initializing dummy ingestion for document: {document_id}")
    
    steps = ["Virus Scanning", "Text Extraction", "Chunking", "Vector Embedding"]
    for i, step in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] Running {step}...")
        time.sleep(1)  # Simulate time spent in each pipeline phase
        
    print(f"Ingestion completed for document: {document_id}")
    return {
        "document_id": document_id,
        "status": "completed",
        "processed_chunks": 14,
        "embedding_model": "text-embedding-3-small"
    }
