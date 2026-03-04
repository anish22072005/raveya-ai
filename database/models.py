"""
ORM models for all modules.
"""
from datetime import datetime
import json

from sqlalchemy import (
    Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


# ─────────────────────────────────────────────
# Shared: AI prompt/response log
# ─────────────────────────────────────────────
class AILog(Base):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module: Mapped[str] = mapped_column(String(50))          # "b2b_proposal" | "whatsapp_bot"
    model: Mapped[str] = mapped_column(String(80))
    system_prompt: Mapped[str] = mapped_column(Text)
    user_prompt: Mapped[str] = mapped_column(Text)
    raw_response: Mapped[str] = mapped_column(Text)
    latency_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# Module 2 – B2B Proposal
# ─────────────────────────────────────────────
class B2BProposal(Base):
    __tablename__ = "b2b_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(100))
    budget: Mapped[float] = mapped_column(Float)
    sustainability_goals: Mapped[str] = mapped_column(Text)
    product_preferences: Mapped[str] = mapped_column(Text, nullable=True)

    # AI output stored as JSON text
    product_mix: Mapped[str] = mapped_column(Text)           # JSON list
    budget_allocation: Mapped[str] = mapped_column(Text)     # JSON object
    cost_breakdown: Mapped[str] = mapped_column(Text)        # JSON list
    impact_summary: Mapped[str] = mapped_column(Text)
    full_response: Mapped[str] = mapped_column(Text)         # raw JSON from AI

    ai_log_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ai_logs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def product_mix_obj(self):
        return json.loads(self.product_mix)

    @property
    def budget_allocation_obj(self):
        return json.loads(self.budget_allocation)

    @property
    def cost_breakdown_obj(self):
        return json.loads(self.cost_breakdown)


# ─────────────────────────────────────────────
# Module 4 – WhatsApp Support Bot
# ─────────────────────────────────────────────
class Order(Base):
    """Seed data representing real orders in the system."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_phone: Mapped[str] = mapped_column(String(30), index=True)
    customer_name: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(50))   # pending | processing | shipped | delivered | cancelled
    total_amount: Mapped[float] = mapped_column(Float)
    items_summary: Mapped[str] = mapped_column(Text)  # plain-text summary
    tracking_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_delivery: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations: Mapped[list["WhatsAppConversation"]] = relationship(
        "WhatsAppConversation", back_populates="order"
    )


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(30), index=True)
    direction: Mapped[str] = mapped_column(String(10))          # "inbound" | "outbound"
    message_body: Mapped[str] = mapped_column(Text)
    intent_detected: Mapped[str | None] = mapped_column(String(100), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    ai_log_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ai_logs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["Order | None"] = relationship("Order", back_populates="conversations")
