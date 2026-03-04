"""
Pydantic schemas for Module 4 — WhatsApp Support Bot.
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ── Twilio incoming webhook body ──────────────────────────
class TwilioInboundMessage(BaseModel):
    """Mirrors key Twilio WhatsApp webhook form fields."""
    From: str = Field(..., description="Sender phone e.g. whatsapp:+919876543210")
    Body: str = Field(..., description="Raw message text")
    To: str = Field("", description="Raveya's WhatsApp number")
    MessageSid: str = Field("", description="Twilio message SID")


# ── AI-parsed intent ──────────────────────────────────────
IntentType = Literal[
    "order_status",
    "return_policy",
    "refund_request",
    "complaint",
    "greeting",
    "out_of_scope",
    "escalate",
]


# ── Bot reply (returned from webhook endpoint) ────────────
class BotReply(BaseModel):
    phone_number: str
    response_message: str
    intent: IntentType
    escalated: bool
    escalation_reason: str | None = None
    order_number_mentioned: str | None = None
    confidence: float
    conversation_id: int


# ── Conversation log entry ────────────────────────────────
class ConversationLogEntry(BaseModel):
    id: int
    phone_number: str
    direction: str
    message_body: str
    intent_detected: str | None
    escalated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Direct test request (no Twilio required) ─────────────
class DirectMessageRequest(BaseModel):
    phone_number: str = Field(..., examples=["+919876543210"])
    message: str = Field(..., min_length=1, examples=["Where is my order ORD-001?"])


# ── Order lookup response ─────────────────────────────────
class OrderStatusResponse(BaseModel):
    order_number: str
    customer_name: str
    status: str
    items_summary: str
    total_amount: float
    tracking_number: str | None
    estimated_delivery: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
