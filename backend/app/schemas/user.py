import uuid
import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    role: Literal["Admin", "Manager", "Employee"] = "Employee"

class UserCreate(UserBase):
    password: str
    org_name: Optional[str] = None  # If registering a brand new tenant organization
    org_id: Optional[uuid.UUID] = None  # If joining an existing organization

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[Literal["Admin", "Manager", "Employee"]] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    org_id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
