import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)          # 'free' | 'pro'
    name: Mapped[str] = mapped_column(String, nullable=False)
    api_call_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_token_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String, nullable=False)         # active | past_due | canceled
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    usage_type: Mapped[str] = mapped_column(String, nullable=False)     # api_call | ai_tokens
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_tenant_idempotency"),
    )


class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    stripe_event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())