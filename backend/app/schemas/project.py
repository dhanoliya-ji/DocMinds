import uuid
import datetime
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
