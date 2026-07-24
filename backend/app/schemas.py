from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, PlainSerializer, model_validator

from app.constants import CREDIT, DEPOSIT, AccountType, Currency, TransactionType

CARD_DIGITS_PATTERN = r"^\d{4}\|\d{4}$"


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
    is_admin: bool = False
    created_at: UtcDatetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


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


class CurrencySettingsResponse(BaseModel):
    currency: Currency


class CurrencySettingsUpdateRequest(BaseModel):
    currency: Currency


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
    account_type: AccountType = DEPOSIT
    card_digits: str | None = Field(default=None, pattern=CARD_DIGITS_PATTERN)

    @model_validator(mode="after")
    def _check_credit_card_shape(self):
        if self.account_type == CREDIT and self.card_digits is None:
            raise ValueError("credit accounts require card_digits")
        if self.account_type == DEPOSIT and self.card_digits is not None:
            raise ValueError("deposit accounts must not have card_digits")
        return self


class BankUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    last_balance: Decimal | None = Field(default=None, ge=0)
    account_type: AccountType | None = None
    card_digits: str | None = Field(default=None, pattern=CARD_DIGITS_PATTERN)

    @model_validator(mode="after")
    def _check_same_request_conflicts(self):
        # These are shape-only checks: same-request combinations that can never
        # be valid regardless of the stored bank. Stateful checks (existing-
        # credit + balance update, flip-to-credit without card_digits) live in
        # the service.
        if self.account_type == CREDIT and self.last_balance is not None:
            raise ValueError("credit accounts cannot have a balance")
        if self.account_type == DEPOSIT and self.card_digits is not None:
            raise ValueError("deposit accounts must not have card_digits")
        return self


class BankResponse(BaseModel):
    id: int
    name: str
    account_type: AccountType
    card_digits: str | None
    last_balance: Decimal | None
    last_balance_at: UtcDatetime | None
    created_at: UtcDatetime

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: int
    message_id: int
    bank_id: int | None
    bank_name: str | None
    bank_account_type: AccountType | None = None
    sender: str
    normalized_amount: Decimal
    normalized_currency: Currency
    original_amount: Decimal | None = None
    original_currency: str | None = None
    type: TransactionType
    date: UtcDatetime
    paired_with_id: int | None = None
    paired_with_message_id: int | None = None
    bill_id: int | None = None


class TransactionUpdateRequest(BaseModel):
    type: TransactionType


class TransactionTotals(BaseModel):
    income: Decimal
    expense: Decimal


class PaginatedTransactionsResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    totals: TransactionTotals


class BillResponse(BaseModel):
    id: int
    message_id: int
    sender: str
    received_at: UtcDatetime
    bank_id: int | None
    bank_name: str | None
    normalized_total_due: Decimal
    normalized_currency: Currency
    original_amount: Decimal | None = None
    original_currency: str | None = None
    statement_period: date | None = None
    paid_at: UtcDatetime | None = None
    linked_transaction_ids: list[int] = Field(default_factory=list)
    created_at: UtcDatetime


class PaginatedBillsResponse(BaseModel):
    bills: list[BillResponse]
    total: int
    page: int
    page_size: int


class BillUpdateRequest(BaseModel):
    unlink_transaction_ids: list[int] | None = None


class AdminListUsersResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class AdminUsageSummary(BaseModel):
    lifetime_cost_micros: int
    lifetime_tokens: int
    last30d_cost_micros: int
    last30d_tokens: int


class AdminUsageBucket(BaseModel):
    bucket_start: date
    cost_micros: int
    tokens: int


BucketSize = Literal["day", "week", "month"]


class AdminUserUsageDetailResponse(BaseModel):
    series: list[AdminUsageBucket]
    message_count: int
    bucket: BucketSize
