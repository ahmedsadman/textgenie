from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CategoryUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CategoryResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
