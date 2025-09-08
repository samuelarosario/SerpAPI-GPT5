from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    # Use plain str here so internal/demo accounts like 'user@local' (no TLD) are accepted.
    # Registration still enforces a real email format via EmailStr in UserCreate.
    email: str
    password: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_admin: bool | None = False
    created_at: datetime

    class Config:
        from_attributes = True
