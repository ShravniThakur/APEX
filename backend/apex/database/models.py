"""SQLAlchemy models — the 12 tables from specs/schema.md.

Substrate (stands in for SBI's CBS): PRODUCTS, CUSTOMERS, ACCOUNTS, TRANSACTIONS,
APP_SESSIONS, APPLICATIONS, HOLDINGS.
Operational (APEX's own audit log): SCORES, SIGNALS, DECISIONS, ACTIONS, OUTCOMES.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# --------------------------------------------------------------------------- #
# Substrate tables
# --------------------------------------------------------------------------- #
class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    depth: Mapped[str] = mapped_column(String, nullable=False)  # full | reference
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_source: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    eligibility_rules: Mapped[dict | None] = mapped_column(JSONB)
    key_facts: Mapped[dict | None] = mapped_column(JSONB)
    landing_url: Mapped[str | None] = mapped_column(String)
    primary_use: Mapped[str | None] = mapped_column(String)
    tax_saving: Mapped[bool] = mapped_column(Boolean, default=False)


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String)
    city_tier: Mapped[str | None] = mapped_column(String)  # metro|tier_2|tier_3|rural
    language_pref: Mapped[str | None] = mapped_column(String)
    occupation: Mapped[str | None] = mapped_column(String)
    account_opened_date: Mapped[date | None] = mapped_column(Date)
    kyc_status: Mapped[str | None] = mapped_column(String)
    customer_type: Mapped[str | None] = mapped_column(String)  # new|existing|dormant
    email: Mapped[str | None] = mapped_column(String)  # Analyser email channel; sink-routed in non-prod
    # Profile extensions (loan/inclusion enabling)
    monthly_income: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    owns_property: Mapped[bool] = mapped_column(Boolean, default=False)
    dependents: Mapped[int] = mapped_column(Integer, default=0)
    owns_gold: Mapped[bool] = mapped_column(Boolean, default=False)
    has_papl_offer: Mapped[bool] = mapped_column(Boolean, default=False)
    has_card_offer: Mapped[bool] = mapped_column(Boolean, default=False)


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    account_type: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    opened_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default="active")  # active|dormant|closed


class Transaction(Base):
    __tablename__ = "transactions"

    txn_id: Mapped[uuid.UUID] = _uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    direction: Mapped[str] = mapped_column(String)  # debit|credit
    merchant_category: Mapped[str | None] = mapped_column(String)
    payee_id: Mapped[str | None] = mapped_column(String, index=True)
    channel: Mapped[str | None] = mapped_column(String)  # upi|neft|cash|autopay|card
    txn_time: Mapped[datetime] = mapped_column(DateTime)
    is_manual_recurring: Mapped[bool] = mapped_column(Boolean, default=False)


class AppSession(Base):
    __tablename__ = "app_sessions"

    session_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    login_time: Mapped[datetime] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    features_used: Mapped[list | None] = mapped_column(JSONB)
    device_type: Mapped[str | None] = mapped_column(String)


class Application(Base):
    __tablename__ = "applications"

    application_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_ref: Mapped[str | None] = mapped_column(String)  # phone/PAN, may have no customer yet
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.product_id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    current_step: Mapped[str | None] = mapped_column(String)
    steps_completed: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str | None] = mapped_column(String)  # in_progress|abandoned|completed


class Holding(Base):
    __tablename__ = "holdings"

    holding_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    units: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    acquired_date: Mapped[date | None] = mapped_column(Date)


# --------------------------------------------------------------------------- #
# Operational tables (APEX audit log)
# --------------------------------------------------------------------------- #
class Score(Base):
    __tablename__ = "scores"

    score_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    score_type: Mapped[str] = mapped_column(String)  # stress|propensity|dormancy|anomaly
    value: Mapped[dict | None] = mapped_column(JSONB)  # float or per-category JSON
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"

    signal_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    signal_type: Mapped[str] = mapped_column(String)
    source_ref: Mapped[str | None] = mapped_column(String)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="new")  # new|processed|expired


class Decision(Base):
    __tablename__ = "decisions"

    decision_id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    mode: Mapped[str] = mapped_column(String)  # guide|analyser|concierge
    trigger_ref: Mapped[str | None] = mapped_column(String)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    critique_result: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    outcome: Mapped[str | None] = mapped_column(String)  # act|wait|escalate
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.product_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Action(Base):
    __tablename__ = "actions"

    action_id: Mapped[uuid.UUID] = _uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.decision_id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    authority_level: Mapped[int | None] = mapped_column(Integer)  # 1-3
    channel: Mapped[str | None] = mapped_column(String)  # website|email
    message_text: Mapped[str | None] = mapped_column(Text)
    deep_link: Mapped[str | None] = mapped_column(String)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Outcome(Base):
    __tablename__ = "outcomes"

    outcome_id: Mapped[uuid.UUID] = _uuid_pk()
    action_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("actions.action_id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    response_type: Mapped[str | None] = mapped_column(String)  # clicked|dismissed|ignored|completed
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    response_window_closed: Mapped[bool] = mapped_column(Boolean, default=False)
