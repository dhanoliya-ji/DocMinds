import uuid
import datetime
from pydantic import BaseModel, ConfigDict

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
