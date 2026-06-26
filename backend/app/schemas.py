from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, PlainSerializer, model_validator


def _as_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


UtcDatetime = Annotated[
    datetime, PlainSerializer(_as_utc_iso, return_type=str, when_used="json")
]


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
    created_at: UtcDatetime

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
    is_default: bool = False
    created_at: UtcDatetime

    model_config = {"from_attributes": True}

    @model_validator(mode="wrap")
    @classmethod
    def _from_orm(cls, data, handler):
        if hasattr(data, "user_id"):
            data.is_default = data.user_id is None
        return handler(data)


class WebhookPayload(BaseModel):
    sender: str = Field(min_length=1)
    content: str = Field(min_length=1)
    timestamp: int | None = None


class WebhookSettingsResponse(BaseModel):
    webhook_url: str
    webhook_token: str


class MetadataBlacklistResponse(BaseModel):
    senders: list[str]


class MetadataBlacklistUpdateRequest(BaseModel):
    senders: list[str]


class SmsMessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    received_at: UtcDatetime
    category: CategoryResponse | None
    created_at: UtcDatetime

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
    last_balance_at: UtcDatetime | None
    created_at: UtcDatetime

    model_config = {"from_attributes": True}
