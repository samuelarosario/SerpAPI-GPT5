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
    # Relaxed to plain str so internal/demo accounts like 'user@local' validate.
    # Registration still uses EmailStr (UserCreate) to enforce proper emails for real users.
    email: str
    is_active: bool
    is_admin: bool | None = False
    created_at: datetime

    class Config:
        from_attributes = True
