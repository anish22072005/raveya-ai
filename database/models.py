"""
MongoDB document schemas (Pydantic).
These define the shape of documents stored in each collection.
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from bson import ObjectId


def new_id() -> str:
    return str(ObjectId())


# ── Shared: AI log ────────────────────────────────────────
class AILogDoc(BaseModel):
    module: str
    model: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    latency_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Module 2: B2B Proposal ────────────────────────────────
class B2BProposalDoc(BaseModel):
    company_name: str
    industry: str
    budget: float
    sustainability_goals: str
    product_preferences: str = ""
    product_mix: list[dict] = []
    budget_allocation: dict = {}
    cost_breakdown: list[dict] = []
    impact_summary: dict = {}
    full_response: dict = {}
    ai_log_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Module 4: Order ───────────────────────────────────────
class OrderDoc(BaseModel):
    order_number: str
    customer_phone: str
    customer_name: str
    status: str
    total_amount: float
    items_summary: str
    tracking_number: str | None = None
    estimated_delivery: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Module 4: WhatsApp conversation ──────────────────────
class WhatsAppConversationDoc(BaseModel):
    phone_number: str
    direction: str          # "inbound" | "outbound"
    message_body: str
    intent_detected: str | None = None
    escalated: bool = False
    order_id: str | None = None
    ai_log_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
