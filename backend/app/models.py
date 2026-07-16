from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_token: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    metadata_blacklist: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="BDT"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    categories: Mapped[list["Category"]] = relationship(back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    banks: Mapped[list["Bank"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    bills: Mapped[list["Bill"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="categories")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="messages")
    category: Mapped["Category | None"] = relationship()


class Bank(Base):
    __tablename__ = "banks"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_bank_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="deposit"
    )
    card_digits: Mapped[str | None] = mapped_column(String(9), nullable=True)
    last_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    last_balance_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="banks")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_transaction_message_id"),
        Index("ix_transaction_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    bank_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("banks.id", ondelete="SET NULL"), nullable=True
    )
    paired_with_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    bill_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    normalized_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    normalized_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="BDT"
    )
    original_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    original_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="transactions")
    bank: Mapped["Bank | None"] = relationship()
    message: Mapped["Message"] = relationship()
    bill: Mapped["Bill | None"] = relationship(back_populates="linked_transactions")


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_bill_message_id"),
        Index("ix_bills_user_id", "user_id"),
        Index(
            "ix_bill_user_bank_period",
            "user_id",
            "bank_id",
            "statement_period",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    bank_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("banks.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    normalized_total_due: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    normalized_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="BDT"
    )
    original_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    original_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    statement_period: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="bills")
    bank: Mapped["Bank | None"] = relationship()
    message: Mapped["Message"] = relationship()
    linked_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="bill"
    )
