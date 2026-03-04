"""
Business logic for Module 2 - B2B Proposal Generator.
AI calls are isolated to this service; routers contain only HTTP logic.
"""
import logging
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai_client import chat_completion
from database.models import AILogDoc, B2BProposalDoc
from modules.b2b_proposal.prompts import SYSTEM_PROMPT, build_user_prompt, CATALOG_CONTEXT
from modules.b2b_proposal.schemas import ProposalRequest

logger = logging.getLogger(__name__)


async def generate_proposal(
    request: ProposalRequest,
    db: AsyncIOMotorDatabase,
) -> dict[str, Any]:
    user_prompt = build_user_prompt(
        company_name=request.company_name,
        industry=request.industry,
        budget=request.budget,
        sustainability_goals=request.sustainability_goals,
        product_preferences=request.product_preferences or "",
        catalog_context=CATALOG_CONTEXT,
    )

    ai_data, log_record = await chat_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.4,
        max_tokens=2000,
    )

    # Persist AI log
    ai_log = AILogDoc(module="b2b_proposal", **log_record)
    ai_log_result = await db["ai_logs"].insert_one(ai_log.model_dump())
    ai_log_id = str(ai_log_result.inserted_id)

    # Budget guard
    _validate_and_fix_budget(ai_data, request.budget)

    # Persist proposal
    proposal = B2BProposalDoc(
        company_name=request.company_name,
        industry=request.industry,
        budget=request.budget,
        sustainability_goals=request.sustainability_goals,
        product_preferences=request.product_preferences or "",
        product_mix=ai_data.get("product_mix", []),
        budget_allocation=ai_data.get("budget_allocation", {}),
        cost_breakdown=ai_data.get("cost_breakdown", []),
        impact_summary=ai_data.get("impact_positioning", {}),
        full_response=ai_data,
        ai_log_id=ai_log_id,
    )
    result = await db["b2b_proposals"].insert_one(proposal.model_dump())
    proposal_id = str(result.inserted_id)

    logger.info("Proposal %s created for '%s' - budget INR %.2f", proposal_id, request.company_name, request.budget)
    return _build_response(proposal_id, proposal.model_dump(), ai_data)


async def get_proposal(proposal_id: str, db: AsyncIOMotorDatabase) -> dict[str, Any] | None:
    try:
        doc = await db["b2b_proposals"].find_one({"_id": ObjectId(proposal_id)})
    except Exception:
        return None
    if not doc:
        return None
    return _build_response(str(doc["_id"]), doc, doc.get("full_response", {}))


async def list_proposals(db: AsyncIOMotorDatabase, limit: int = 20, offset: int = 0) -> list[dict]:
    cursor = db["b2b_proposals"].find().sort("created_at", -1).skip(offset).limit(limit)
    out = []
    async for doc in cursor:
        out.append({
            "id": str(doc["_id"]),
            "company_name": doc["company_name"],
            "industry": doc["industry"],
            "budget": doc["budget"],
            "proposal_title": doc.get("full_response", {}).get("proposal_title", ""),
            "created_at": doc["created_at"],
        })
    return out


# Private helpers

def _validate_and_fix_budget(ai_data: dict, max_budget: float) -> None:
    allocation = ai_data.get("budget_allocation", {})
    allocated = float(allocation.get("total_allocated_inr", 0))
    if allocated > max_budget:
        logger.warning("AI over-allocated INR %.2f vs budget INR %.2f - capping.", allocated, max_budget)
        allocation["total_allocated_inr"] = max_budget
        allocation["remaining_buffer_inr"] = 0.0
        ai_data["budget_allocation"] = allocation


def _build_response(proposal_id: str, doc: dict, ai_data: dict) -> dict[str, Any]:
    return {
        "id": proposal_id,
        "company_name": doc["company_name"],
        "industry": doc["industry"],
        "budget": doc["budget"],
        "proposal_title": ai_data.get("proposal_title", ""),
        "executive_summary": ai_data.get("executive_summary", ""),
        "product_mix": ai_data.get("product_mix", []),
        "budget_allocation": ai_data.get("budget_allocation", {}),
        "cost_breakdown": ai_data.get("cost_breakdown", []),
        "impact_positioning": ai_data.get("impact_positioning", {}),
        "next_steps": ai_data.get("next_steps", []),
        "created_at": doc["created_at"],
    }