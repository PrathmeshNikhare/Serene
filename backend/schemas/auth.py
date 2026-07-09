from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    persona: Optional[str] = "Teenager"
    age: Optional[int] = 20
    gender: Optional[str] = "Female"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: uuid.UUID
    email: str
    persona: Optional[str] = None
    age: int
    gender: str
    wellness_points: int

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    persona: Optional[str] = None
    age: int
    gender: str
    wellness_points: int

    class Config:
        from_attributes = True
