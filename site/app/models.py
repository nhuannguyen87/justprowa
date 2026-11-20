"""Database tables."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AdminUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=now_utc)


class QuoteRequest(SQLModel, table=True):
    """A quote, call-out or subscriber request sent from the website."""
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(16), index=True, unique=True)
    kind: str = "quote"                      # quote | callout | subscriber
    subject: str
    description: str
    address: str = ""
    preferred_days: str = ""                 # comma separated ISO dates, or "flexible"
    full_name: str
    phone: str
    email: str
    contact_method: str = "phone"            # phone | sms | email
    status: str = Field(default="new", index=True)
    admin_notes: str = ""
    created_at: datetime = Field(default_factory=now_utc, index=True)
    updated_at: datetime = Field(default_factory=now_utc)

    attachments: list["Attachment"] = Relationship(back_populates="request")
    responses: list["QuoteResponse"] = Relationship(back_populates="request")

    @property
    def ref(self) -> str:
        return f"JPS-{self.id:04d}" if self.id else "JPS-new"


class Attachment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="quoterequest.id", index=True)
    original_name: str
    stored_name: str
    content_type: str = ""
    size: int = 0
    request: Optional[QuoteRequest] = Relationship(back_populates="attachments")

    @property
    def is_image(self) -> bool:
        return self.content_type.startswith("image/") and not self.original_name.lower().endswith((".heic", ".heif"))


class QuoteResponse(SQLModel, table=True):
    """A reply from JPS to a request (optionally with a quoted price)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="quoterequest.id", index=True)
    author: str
    message: str
    amount_cents: Optional[int] = None       # quoted price incl. GST, if any
    emailed: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    request: Optional[QuoteRequest] = Relationship(back_populates="responses")

    @property
    def amount(self) -> Optional[float]:
        return None if self.amount_cents is None else self.amount_cents / 100


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan: str                                # bronze | silver | gold
    services: str                            # comma separated service names
    full_name: str
    phone: str
    email: str
    address: str
    notes: str = ""
    status: str = Field(default="pending", index=True)   # pending | active | cancelled
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    created_at: datetime = Field(default_factory=now_utc, index=True)


class ContactMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    phone: str = ""
    email: str
    message: str
    handled: bool = False
    created_at: datetime = Field(default_factory=now_utc, index=True)


class Payment(SQLModel, table=True):
    """Ready for Stripe later – one row per checkout attempt."""
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: Optional[int] = Field(default=None, foreign_key="quoterequest.id")
    subscription_id: Optional[int] = Field(default=None, foreign_key="subscription.id")
    amount_cents: int
    status: str = "pending"                  # pending | paid | failed
    stripe_session_id: str = ""
    created_at: datetime = Field(default_factory=now_utc)
