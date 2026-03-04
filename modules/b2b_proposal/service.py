"""
Business logic for Module 2 — B2B Proposal Generator.
AI calls are isolated to this service; routers contain only HTTP logic.
"""
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.ai_client import chat_completion
from database.models import B2BProposal, AILog
from modules.b2b_proposal.prompts import SYSTEM_PROMPT, build_user_prompt, CATALOG_CONTEXT
from modules.b2b_proposal.schemas import ProposalRequest

logger = logging.getLogger(__name__)


async def generate_proposal(
    request: ProposalRequest,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    1. Build prompt from request data + product catalog context.
    2. Call AI and get structured JSON.
    3. Validate budget constraint.
    4. Persist AILog + B2BProposal to database.
    5. Return full structured response.
    """
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

    # ── Persist AI log ────────────────────────────────────
    ai_log = AILog(
        module="b2b_proposal",
        **log_record,
    )
    db.add(ai_log)
    await db.flush()  # get ai_log.id

    # ── Business logic validation ─────────────────────────
    _validate_and_fix_budget(ai_data, request.budget)

    # ── Persist proposal ──────────────────────────────────
    proposal = B2BProposal(
        company_name=request.company_name,
        industry=request.industry,
        budget=request.budget,
        sustainability_goals=request.sustainability_goals,
        product_preferences=request.product_preferences or "",
        product_mix=json.dumps(ai_data.get("product_mix", [])),
        budget_allocation=json.dumps(ai_data.get("budget_allocation", {})),
        cost_breakdown=json.dumps(ai_data.get("cost_breakdown", [])),
        impact_summary=json.dumps(ai_data.get("impact_positioning", {})),
        full_response=json.dumps(ai_data),
        ai_log_id=ai_log.id,
    )
    db.add(proposal)
    await db.flush()

    logger.info(
        "Proposal #%d created for '%s' — budget ₹%.2f",
        proposal.id,
        request.company_name,
        request.budget,
    )

    return _build_response(proposal, ai_data)


async def get_proposal(proposal_id: int, db: AsyncSession) -> dict[str, Any] | None:
    result = await db.execute(
        select(B2BProposal).where(B2BProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        return None
    ai_data = json.loads(proposal.full_response)
    return _build_response(proposal, ai_data)


async def list_proposals(db: AsyncSession, limit: int = 20, offset: int = 0) -> list[dict]:
    result = await db.execute(
        select(B2BProposal)
        .order_by(desc(B2BProposal.created_at))
        .limit(limit)
        .offset(offset)
    )
    proposals = result.scalars().all()
    out = []
    for p in proposals:
        ai_data = json.loads(p.full_response)
        out.append({
            "id": p.id,
            "company_name": p.company_name,
            "industry": p.industry,
            "budget": p.budget,
            "proposal_title": ai_data.get("proposal_title", ""),
            "created_at": p.created_at,
        })
    return out


# ── Private helpers ───────────────────────────────────────

def _validate_and_fix_budget(ai_data: dict, max_budget: float) -> None:
    """
    Ensure AI-returned financials don't exceed the client's budget.
    If the AI hallucinated an over-budget figure, cap it and adjust.
    """
    allocation = ai_data.get("budget_allocation", {})
    allocated = float(allocation.get("total_allocated_inr", 0))

    if allocated > max_budget:
        logger.warning(
            "AI over-allocated ₹%.2f vs budget ₹%.2f — capping.",
            allocated,
            max_budget,
        )
        allocation["total_allocated_inr"] = max_budget
        allocation["remaining_buffer_inr"] = 0.0
        ai_data["budget_allocation"] = allocation


def _build_response(proposal: B2BProposal, ai_data: dict) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "company_name": proposal.company_name,
        "industry": proposal.industry,
        "budget": proposal.budget,
        "proposal_title": ai_data.get("proposal_title", ""),
        "executive_summary": ai_data.get("executive_summary", ""),
        "product_mix": ai_data.get("product_mix", []),
        "budget_allocation": ai_data.get("budget_allocation", {}),
        "cost_breakdown": ai_data.get("cost_breakdown", []),
        "impact_positioning": ai_data.get("impact_positioning", {}),
        "next_steps": ai_data.get("next_steps", []),
        "created_at": proposal.created_at,
    }
