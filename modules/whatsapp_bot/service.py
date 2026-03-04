"""
Business logic for Module 4 — WhatsApp Support Bot.

Flow per message:
1. Look up customer orders by phone number.
2. Fetch last 3 conversation turns for context.
3. Build prompt including real order data.
4. Call AI → parse intent + generate reply.
5. Log inbound + outbound messages.
6. Escalate if AI flags it (notify via Twilio).
7. Return reply to webhook handler.
"""
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.ai_client import chat_completion
from core.config import get_settings
from database.models import Order, WhatsAppConversation, AILog
from modules.whatsapp_bot.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Regex patterns for order number detection ─────────────
ORDER_PATTERN = re.compile(r"\b(ORD[-\s]?\d{3,})\b", re.IGNORECASE)


async def handle_inbound_message(
    phone_number: str,
    message_body: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Core handler — processes a single inbound WhatsApp message.
    Returns a dict ready to send back as a Twilio TwiML / JSON reply.
    """
    # Normalise phone — strip whatsapp: prefix if present
    clean_phone = phone_number.replace("whatsapp:", "").strip()

    # ── 1. Fetch customer orders ──────────────────────────
    order_context = await _build_order_context(clean_phone, message_body, db)

    # ── 2. Fetch conversation history ─────────────────────
    history = await _get_conversation_history(clean_phone, db)

    # ── 3. AI call ────────────────────────────────────────
    user_prompt = build_user_prompt(
        customer_message=message_body,
        order_context=order_context,
        conversation_history=history,
    )

    ai_data, log_record = await chat_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=500,
    )

    # ── 4. Persist AI log ─────────────────────────────────
    ai_log = AILog(module="whatsapp_bot", **log_record)
    db.add(ai_log)
    await db.flush()

    # ── 5. Extract AI response fields ─────────────────────
    intent = ai_data.get("intent", "out_of_scope")
    response_message = ai_data.get("response_message", _fallback_message())
    escalate = bool(ai_data.get("escalate", False))
    escalation_reason = ai_data.get("escalation_reason")
    order_number_mentioned = ai_data.get("order_number_mentioned")
    confidence = float(ai_data.get("confidence", 0.5))

    # ── 6. Resolve linked order (if any) ──────────────────
    linked_order_id = await _resolve_order_id(order_number_mentioned, db)

    # ── 7. Log inbound message ────────────────────────────
    inbound_log = WhatsAppConversation(
        phone_number=clean_phone,
        direction="inbound",
        message_body=message_body,
        intent_detected=intent,
        escalated=False,
        order_id=linked_order_id,
        ai_log_id=ai_log.id,
    )
    db.add(inbound_log)
    await db.flush()

    # ── 8. Log outbound (bot reply) ───────────────────────
    outbound_log = WhatsAppConversation(
        phone_number=clean_phone,
        direction="outbound",
        message_body=response_message,
        intent_detected=intent,
        escalated=escalate,
        order_id=linked_order_id,
        ai_log_id=ai_log.id,
    )
    db.add(outbound_log)
    await db.flush()

    # ── 9. Escalation side-effect ─────────────────────────
    if escalate:
        await _trigger_escalation(clean_phone, message_body, escalation_reason, db)
        logger.warning(
            "ESCALATION triggered for %s — reason: %s", clean_phone, escalation_reason
        )

    logger.info(
        "WhatsApp [%s] intent=%s escalate=%s confidence=%.2f",
        clean_phone,
        intent,
        escalate,
        confidence,
    )

    return {
        "phone_number": clean_phone,
        "response_message": response_message,
        "intent": intent,
        "escalated": escalate,
        "escalation_reason": escalation_reason,
        "order_number_mentioned": order_number_mentioned,
        "confidence": confidence,
        "conversation_id": outbound_log.id,
    }


async def get_conversation_history(
    phone_number: str,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    clean_phone = phone_number.replace("whatsapp:", "").strip()
    result = await db.execute(
        select(WhatsAppConversation)
        .where(WhatsAppConversation.phone_number == clean_phone)
        .order_by(desc(WhatsAppConversation.created_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "phone_number": r.phone_number,
            "direction": r.direction,
            "message_body": r.message_body,
            "intent_detected": r.intent_detected,
            "escalated": r.escalated,
            "created_at": r.created_at,
        }
        for r in reversed(rows)
    ]


async def get_order_status(order_number: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(Order).where(Order.order_number == order_number.upper())
    )
    order = result.scalar_one_or_none()
    if not order:
        return None
    return {
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "status": order.status,
        "items_summary": order.items_summary,
        "total_amount": order.total_amount,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.estimated_delivery,
        "created_at": order.created_at,
    }


# ── Private helpers ───────────────────────────────────────

async def _build_order_context(
    phone: str, message: str, db: AsyncSession
) -> str:
    """
    Build a plain-text order context string to inject into the prompt.
    Looks up by phone number first; also scans message for an order number.
    """
    lines: list[str] = []

    # Orders by phone
    result = await db.execute(
        select(Order)
        .where(Order.customer_phone == phone)
        .order_by(desc(Order.created_at))
        .limit(5)
    )
    orders = result.scalars().all()
    for o in orders:
        lines.append(
            f"Order {o.order_number}: status={o.status}, items={o.items_summary}, "
            f"total=₹{o.total_amount:.2f}, tracking={o.tracking_number or 'N/A'}, "
            f"ETA={o.estimated_delivery or 'N/A'}"
        )

    # If a different order number is mentioned in message, look it up too
    match = ORDER_PATTERN.search(message)
    if match:
        order_num = match.group(1).replace(" ", "-").upper()
        r2 = await db.execute(select(Order).where(Order.order_number == order_num))
        extra = r2.scalar_one_or_none()
        if extra:
            entry = (
                f"Order {extra.order_number}: status={extra.status}, "
                f"items={extra.items_summary}, total=₹{extra.total_amount:.2f}, "
                f"tracking={extra.tracking_number or 'N/A'}, "
                f"ETA={extra.estimated_delivery or 'N/A'}"
            )
            if entry not in lines:
                lines.append(entry)

    return "\n".join(lines) if lines else ""


async def _get_conversation_history(phone: str, db: AsyncSession) -> str:
    result = await db.execute(
        select(WhatsAppConversation)
        .where(WhatsAppConversation.phone_number == phone)
        .order_by(desc(WhatsAppConversation.created_at))
        .limit(6)
    )
    rows = list(reversed(result.scalars().all()))
    if not rows:
        return ""
    parts = []
    for r in rows:
        role = "Customer" if r.direction == "inbound" else "Raveya Bot"
        parts.append(f"{role}: {r.message_body}")
    return "\n".join(parts)


async def _resolve_order_id(order_number: str | None, db: AsyncSession) -> int | None:
    if not order_number:
        return None
    result = await db.execute(
        select(Order).where(Order.order_number == order_number.upper())
    )
    order = result.scalar_one_or_none()
    return order.id if order else None


async def _trigger_escalation(
    customer_phone: str,
    original_message: str,
    reason: str | None,
    db: AsyncSession,
) -> None:
    """
    Send an escalation alert via Twilio WhatsApp to the support team.
    Gracefully fails if Twilio is not configured.
    """
    from core.config import get_settings
    s = get_settings()

    if not all([s.twilio_account_sid, s.twilio_auth_token, s.escalation_phone]):
        logger.info("Twilio not configured — escalation logged only.")
        return

    try:
        from twilio.rest import Client  # type: ignore
        client = Client(s.twilio_account_sid, s.twilio_auth_token)
        alert_body = (
            f"🚨 ESCALATION ALERT\n"
            f"Customer: {customer_phone}\n"
            f"Reason: {reason or 'High-priority complaint'}\n"
            f"Message: {original_message[:200]}"
        )
        client.messages.create(
            body=alert_body,
            from_=s.twilio_whatsapp_from,
            to=s.escalation_phone,
        )
        logger.info("Escalation alert sent for %s", customer_phone)
    except Exception as exc:
        logger.error("Failed to send escalation alert: %s", exc)


def _fallback_message() -> str:
    return (
        "Hi! Thanks for reaching out to Raveya 🌿. "
        "I'm having trouble processing your request right now. "
        "Please try again or contact us at support@raveya.com."
    )
