"""
HTTP routes for Module 2 — B2B Proposal Generator.
All business logic lives in service.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.database import get_db
from modules.b2b_proposal import service
from modules.b2b_proposal.schemas import ProposalRequest, ProposalResponse, ProposalListItem

router = APIRouter(prefix="/api/v1/proposals", tags=["B2B Proposal Generator"])


@router.post("/generate", response_model=ProposalResponse, status_code=201)
async def generate_proposal(
    body: ProposalRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Generate a full AI-powered B2B sustainability procurement proposal.

    - Validates budget constraints
    - Returns product mix, cost breakdown, budget allocation, and impact positioning
    - Persists proposal + AI log to database
    """
    result = await service.generate_proposal(body, db)
    return result


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Retrieve a previously generated proposal by ID."""
    result = await service.get_proposal(proposal_id, db)
    if not result:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    return result


@router.get("/", response_model=list[ProposalListItem])
async def list_proposals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List all generated proposals (paginated, newest first)."""
    return await service.list_proposals(db, limit=limit, offset=offset)
