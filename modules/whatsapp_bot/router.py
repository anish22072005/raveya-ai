"""
HTTP routes for Module 4 — WhatsApp Support Bot.

Two integration modes:
  1. /webhook  — Twilio sends POST form-data here on every inbound WhatsApp message.
  2. /message  — Direct JSON API for testing without Twilio.
"""
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from modules.whatsapp_bot import service
from modules.whatsapp_bot.schemas import (
    BotReply,
    ConversationLogEntry,
    DirectMessageRequest,
    OrderStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/whatsapp", tags=["WhatsApp Support Bot"])


@router.post("/webhook", include_in_schema=True)
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio WhatsApp Webhook endpoint.
    Twilio sends form-encoded POST data; we reply with TwiML XML.

    Configure in Twilio Console:
    Messaging > WhatsApp Sandbox > When a message comes in → POST <your-host>/api/v1/whatsapp/webhook
    """
    form = await request.form()
    from_number = str(form.get("From", ""))
    body = str(form.get("Body", "")).strip()

    if not from_number or not body:
        return Response(content=_empty_twiml(), media_type="application/xml")

    logger.info("WhatsApp webhook received from %s: %s", from_number, body[:80])

    result = await service.handle_inbound_message(
        phone_number=from_number,
        message_body=body,
        db=db,
    )

    twiml = _build_twiml(result["response_message"])
    return Response(content=twiml, media_type="application/xml")


@router.post("/message", response_model=BotReply, status_code=200)
async def send_direct_message(
    body: DirectMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Direct JSON endpoint — test the bot without Twilio.
    Send a phone number and message; receive the full bot reply as JSON.
    """
    result = await service.handle_inbound_message(
        phone_number=body.phone_number,
        message_body=body.message,
        db=db,
    )
    return result


@router.get("/conversations/{phone_number}", response_model=list[ConversationLogEntry])
async def get_conversations(
    phone_number: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve full conversation history for a phone number.
    Useful for support agent review or audit trail.
    """
    return await service.get_conversation_history(phone_number, db, limit=limit)


@router.get("/orders/{order_number}", response_model=OrderStatusResponse)
async def get_order_status(
    order_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Direct order status lookup by order number."""
    result = await service.get_order_status(order_number.upper(), db)
    if not result:
        raise HTTPException(status_code=404, detail=f"Order {order_number} not found")
    return result


# ── TwiML helpers ─────────────────────────────────────────

def _build_twiml(message: str) -> str:
    safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{safe_msg}</Message>
</Response>"""


def _empty_twiml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""
