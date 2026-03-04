"""
Business logic for Module 4 â€” WhatsApp Support Bot.

Flow per message:
1. Look up customer orders by phone number.
2. Fetch last 3 conversation turns for context.
3. Build prompt including real order data.
4. Call AI â†’ parse intent + generate reply.
5. Log inbound + outbound messages.
6. Escalate if AI flags it (notify via Twilio).
7. Return reply to webhook handler.
"""
import logging
import re
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai_client import chat_completion
from core.config import get_settings
from database.models import AILogDoc, WhatsAppConversationDoc
from modules.whatsapp_bot.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)
settings = get_settings()

ORDER_PATTERN = re.compile(r"\b(ORD[-\s]?\d{3,})\b", re.IGNORECASE)


async def handle_inbound_message(
    phone_number: str,
    message_body: str,
    db: AsyncIOMotorDatabase,
) -> dict[str, Any]:
    clean_phone = phone_number.replace("whatsapp:", "").strip()

    order_context = await _build_order_context(clean_phone, message_body, db)
    history = await _get_conversation_history(clean_phone, db)

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

    ai_log = AILogDoc(module="whatsapp_bot", **log_record)
    ai_log_result = await db["ai_logs"].insert_one(ai_log.model_dump())
    ai_log_id = str(ai_log_result.inserted_id)

    intent = ai_data.get("intent", "out_of_scope")
    response_message = ai_data.get("response_message", _fallback_message())
    escalate = bool(ai_data.get("escalate", False))
    escalation_reason = ai_data.get("escalation_reason")
    order_number_mentioned = ai_data.get("order_number_mentioned")
    confidence = float(ai_data.get("confidence", 0.5))

    linked_order_id = await _resolve_order_id(order_number_mentioned, db)

    inbound_doc = WhatsAppConversationDoc(
        phone_number=clean_phone, direction="inbound", message_body=message_body,
        intent_detected=intent, escalated=False, order_id=linked_order_id, ai_log_id=ai_log_id,
    )
    await db["whatsapp_conversations"].insert_one(inbound_doc.model_dump())

    outbound_doc = WhatsAppConversationDoc(
        phone_number=clean_phone, direction="outbound", message_body=response_message,
        intent_detected=intent, escalated=escalate, order_id=linked_order_id, ai_log_id=ai_log_id,
    )
    out_result = await db["whatsapp_conversations"].insert_one(outbound_doc.model_dump())
    conversation_id = str(out_result.inserted_id)

    if escalate:
        await _trigger_escalation(clean_phone, message_body, escalation_reason)
        logger.warning("ESCALATION triggered for %s â€” reason: %s", clean_phone, escalation_reason)

    logger.info("WhatsApp [%s] intent=%s escalate=%s confidence=%.2f", clean_phone, intent, escalate, confidence)

    return {
        "phone_number": clean_phone,
        "response_message": response_message,
        "intent": intent,
        "escalated": escalate,
        "escalation_reason": escalation_reason,
        "order_number_mentioned": order_number_mentioned,
        "confidence": confidence,
        "conversation_id": conversation_id,
    }


async def get_conversation_history(
    phone_number: str,
    db: AsyncIOMotorDatabase,
    limit: int = 50,
) -> list[dict]:
    clean_phone = phone_number.replace("whatsapp:", "").strip()
    cursor = db["whatsapp_conversations"].find(
        {"phone_number": clean_phone}
    ).sort("created_at", 1).limit(limit)
    out = []
    async for doc in cursor:
        out.append({
            "id": str(doc["_id"]),
            "phone_number": doc["phone_number"],
            "direction": doc["direction"],
            "message_body": doc["message_body"],
            "intent_detected": doc.get("intent_detected"),
            "escalated": doc.get("escalated", False),
            "created_at": doc["created_at"],
        })
    return out


async def get_order_status(order_number: str, db: AsyncIOMotorDatabase) -> dict | None:
    doc = await db["orders"].find_one({"order_number": order_number.upper()})
    if not doc:
        return None
    return {
        "order_number": doc["order_number"],
        "customer_name": doc["customer_name"],
        "status": doc["status"],
        "items_summary": doc["items_summary"],
        "total_amount": doc["total_amount"],
        "tracking_number": doc.get("tracking_number"),
        "estimated_delivery": doc.get("estimated_delivery"),
        "created_at": doc["created_at"],
    }


# â”€â”€ Private helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _build_order_context(phone: str, message: str, db: AsyncIOMotorDatabase) -> str:
    lines: list[str] = []
    cursor = db["orders"].find({"customer_phone": phone}).sort("created_at", -1).limit(5)
    async for o in cursor:
        lines.append(
            f"Order {o['order_number']}: status={o['status']}, items={o['items_summary']}, "
            f"total=â‚¹{o['total_amount']:.2f}, tracking={o.get('tracking_number') or 'N/A'}, "
            f"ETA={o.get('estimated_delivery') or 'N/A'}"
        )
    match = ORDER_PATTERN.search(message)
    if match:
        order_num = match.group(1).replace(" ", "-").upper()
        extra = await db["orders"].find_one({"order_number": order_num})
        if extra:
            entry = (
                f"Order {extra['order_number']}: status={extra['status']}, "
                f"items={extra['items_summary']}, total=â‚¹{extra['total_amount']:.2f}, "
                f"tracking={extra.get('tracking_number') or 'N/A'}, "
                f"ETA={extra.get('estimated_delivery') or 'N/A'}"
            )
            if entry not in lines:
                lines.append(entry)
    return "\n".join(lines) if lines else ""


async def _get_conversation_history(phone: str, db: AsyncIOMotorDatabase) -> str:
    cursor = db["whatsapp_conversations"].find(
        {"phone_number": phone}
    ).sort("created_at", -1).limit(6)
    rows = []
    async for doc in cursor:
        rows.append(doc)
    rows = list(reversed(rows))
    if not rows:
        return ""
    parts = []
    for r in rows:
        role = "Customer" if r["direction"] == "inbound" else "Raveya Bot"
        parts.append(f"{role}: {r['message_body']}")
    return "\n".join(parts)


async def _resolve_order_id(order_number: str | None, db: AsyncIOMotorDatabase) -> str | None:
    if not order_number:
        return None
    doc = await db["orders"].find_one({"order_number": order_number.upper()})
    return str(doc["_id"]) if doc else None


async def _trigger_escalation(
    customer_phone: str,
    original_message: str,
    reason: str | None,
) -> None:
    s = get_settings()
    if not all([s.twilio_account_sid, s.twilio_auth_token, s.escalation_phone]):
        logger.info("Twilio not configured â€” escalation logged only.")
        return
    try:
        from twilio.rest import Client  # type: ignore
        client = Client(s.twilio_account_sid, s.twilio_auth_token)
        alert_body = (
            f"ESCALATION ALERT\n"
            f"Customer: {customer_phone}\n"
            f"Reason: {reason or 'High-priority complaint'}\n"
            f"Message: {original_message[:200]}"
        )
        client.messages.create(body=alert_body, from_=s.twilio_whatsapp_from, to=s.escalation_phone)
        logger.info("Escalation alert sent for %s", customer_phone)
    except Exception as exc:
        logger.error("Failed to send escalation alert: %s", exc)


def _fallback_message() -> str:
    return (
        "Hi! Thanks for reaching out to Raveya. "
        "I'm having trouble processing your request right now. "
        "Please try again or contact us at support@raveya.com."
    )

