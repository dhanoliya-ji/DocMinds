from fastapi import APIRouter, status
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.tasks.test import add_numbers_task, dummy_process_document_task

router = APIRouter()

@router.post("/trigger-add", status_code=status.HTTP_202_ACCEPTED)
async def trigger_add_task(x: int, y: int):
    """
    Enqueue the async addition task in the Celery worker queue.
    """
    task = add_numbers_task.delay(x, y)
    return {"task_id": task.id, "status": task.status}

@router.post("/trigger-document", status_code=status.HTTP_202_ACCEPTED)
async def trigger_document_task(document_id: str):
    """
    Enqueue the async dummy document processing task.
    """
    task = dummy_process_document_task.delay(document_id)
    return {"task_id": task.id, "status": task.status}

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Query the current status and outputs of an enqueued task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None,
        "error": None
    }
    
    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)
        
    return response
