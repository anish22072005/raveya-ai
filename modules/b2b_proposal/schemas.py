"""
Pydantic schemas for Module 2 — B2B Proposal Generator.
Separates API contracts from ORM models.
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


# ── Request ──────────────────────────────────────────────
class ProposalRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200, examples=["GreenTech Solutions Pvt Ltd"])
    industry: str = Field(..., min_length=2, max_length=100, examples=["Information Technology"])
    budget: float = Field(..., gt=0, description="Total procurement budget in INR", examples=[150000])
    sustainability_goals: str = Field(
        ..., min_length=10,
        examples=["Reduce single-use plastic in office by 80%, achieve carbon-neutral operations by 2027"]
    )
    product_preferences: str | None = Field(
        None,
        examples=["Focus on office supplies and packaging; avoid apparel products"]
    )

    @field_validator("budget")
    @classmethod
    def budget_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Budget must be greater than 0")
        return v


# ── Nested response sub-models ────────────────────────────
class ProductMixItem(BaseModel):
    product_name: str
    category: str
    unit_price_inr: float
    recommended_quantity: int
    line_total_inr: float
    sustainability_benefit: str
    sustainability_tags: list[str]


class BudgetAllocation(BaseModel):
    total_budget_inr: float
    total_allocated_inr: float
    remaining_buffer_inr: float
    allocation_by_category: dict[str, float]


class CostBreakdownItem(BaseModel):
    line_item: str
    amount_inr: float
    percentage_of_budget: float


class ImpactPositioning(BaseModel):
    estimated_plastic_avoided_kg: float
    estimated_co2_avoided_kg: float
    sdg_alignment: list[str]
    headline_statement: str
    talking_points: list[str]


# ── Full proposal response ────────────────────────────────
class ProposalResponse(BaseModel):
    id: int
    company_name: str
    industry: str
    budget: float
    proposal_title: str
    executive_summary: str
    product_mix: list[ProductMixItem]
    budget_allocation: BudgetAllocation
    cost_breakdown: list[CostBreakdownItem]
    impact_positioning: ImpactPositioning
    next_steps: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── List response ─────────────────────────────────────────
class ProposalListItem(BaseModel):
    id: int
    company_name: str
    industry: str
    budget: float
    proposal_title: str
    created_at: datetime

    model_config = {"from_attributes": True}
