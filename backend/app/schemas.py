from datetime import datetime
from decimal import Decimal

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


class WebhookPayload(BaseModel):
    sender: str = Field(min_length=1)
    content: str = Field(min_length=1)
    timestamp: int | None = None


class WebhookSettingsResponse(BaseModel):
    webhook_url: str
    webhook_token: str


class SmsMessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    received_at: datetime
    category: CategoryResponse | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedMessagesResponse(BaseModel):
    messages: list[SmsMessageResponse]
    total: int
    page: int
    page_size: int


class BankCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class BankUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    last_balance: Decimal | None = Field(default=None, ge=0)


class BankResponse(BaseModel):
    id: int
    name: str
    last_balance: Decimal | None
    last_balance_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
