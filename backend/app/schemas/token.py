from typing import Optional
from pydantic import BaseModel, ConfigDict

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    org_id: Optional[str] = None
    type: Optional[str] = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str
