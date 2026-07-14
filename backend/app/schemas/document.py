import uuid
import datetime
from pydantic import BaseModel, ConfigDict

class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    status: str
    version: int
    meta_data: dict

class DocumentOut(DocumentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
