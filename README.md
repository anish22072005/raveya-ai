# Raveya AI Platform

AI-powered modules for sustainable commerce — built for the Raveya Full Stack / AI Intern assignment.

## Modules Implemented

| Module | Status | Endpoint Prefix |
|--------|--------|-----------------|
| Module 2 — B2B Proposal Generator | ✅ Fully implemented | `/api/v1/proposals` |
| Module 4 — WhatsApp Support Bot | ✅ Fully implemented | `/api/v1/whatsapp` |
| Module 1 — Auto-Category & Tag Generator | 📐 Architecture outlined | — |
| Module 3 — Impact Reporting Generator | 📐 Architecture outlined | — |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (async) |
| AI Provider | OpenAI GPT-4o-mini |
| Database | SQLite + SQLAlchemy (async) |
| WhatsApp | Twilio WhatsApp API |
| Config | pydantic-settings + `.env` |

---

## Project Structure

```
raveya-ai/
├── main.py                          # FastAPI application entry point
├── seed.py                          # Demo data seeder
├── test_demo.py                     # Integration test suite
├── requirements.txt
├── .env.example
│
├── core/
│   ├── ai_client.py                 # Centralised OpenAI wrapper (logging, retries)
│   ├── config.py                    # Typed settings from .env
│   └── logger.py                    # Structured logging setup
│
├── database/
│   ├── database.py                  # Async engine, session factory, Base
│   └── models.py                    # ORM models: AILog, B2BProposal, Order, WhatsAppConversation
│
└── modules/
    ├── b2b_proposal/
    │   ├── prompts.py               # System + user prompt templates + catalog context
    │   ├── schemas.py               # Pydantic request/response models
    │   ├── service.py               # Business logic + AI orchestration
    │   └── router.py                # FastAPI routes
    │
    └── whatsapp_bot/
        ├── prompts.py               # System + user prompt templates
        ├── schemas.py               # Pydantic request/response models
        ├── service.py               # Intent detection, order lookup, escalation
        └── router.py                # Webhook + direct message endpoints
```

---

## Quick Start

### 1. Clone & install

```bash
cd raveya-ai
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY (required)
# Add Twilio credentials only if testing WhatsApp webhook
```

### 3. Run the server

```bash
python main.py
# Server starts at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 4. Run tests

```bash
# In a second terminal (server must be running):
python test_demo.py
```

---

## Module 2 — B2B Proposal Generator

### What it does

Given a company name, industry, budget (INR), and sustainability goals, the module:
1. Selects the best product mix from Raveya's catalog
2. Allocates budget across product categories
3. Produces itemised cost breakdown
4. Generates an impact positioning summary (plastic avoided, CO₂ avoided, SDG alignment)
5. Stores everything in SQLite and logs the full AI prompt+response

### API

```
POST /api/v1/proposals/generate    Generate a new proposal
GET  /api/v1/proposals/{id}        Retrieve proposal by ID
GET  /api/v1/proposals/            List all proposals (paginated)
```

### Sample Request

```json
POST /api/v1/proposals/generate
{
  "company_name": "EcoLogistics India Pvt Ltd",
  "industry": "Logistics & Supply Chain",
  "budget": 75000,
  "sustainability_goals": "Eliminate single-use plastic in warehouse, reduce carbon footprint 30% in 12 months",
  "product_preferences": "Focus on packaging and facility management"
}
```

### Sample Response (truncated)

```json
{
  "id": 1,
  "proposal_title": "Sustainable Procurement Proposal for EcoLogistics India 2026",
  "executive_summary": "This proposal outlines a comprehensive sustainable procurement strategy...",
  "product_mix": [
    {
      "product_name": "Compostable Mailer Bags (Pack of 50)",
      "category": "Packaging",
      "unit_price_inr": 1100,
      "recommended_quantity": 10,
      "line_total_inr": 11000,
      "sustainability_benefit": "Replaces 500 single-use plastic mailers per pack",
      "sustainability_tags": ["compostable", "plastic-free", "e-commerce"]
    }
  ],
  "budget_allocation": {
    "total_budget_inr": 75000,
    "total_allocated_inr": 72400,
    "remaining_buffer_inr": 2600,
    "allocation_by_category": {
      "Packaging": 28000,
      "Facility Management": 18600,
      "Office Supplies": 14200,
      "Energy & Tech": 11600
    }
  },
  "impact_positioning": {
    "estimated_plastic_avoided_kg": 42.5,
    "estimated_co2_avoided_kg": 68.3,
    "sdg_alignment": ["SDG 12", "SDG 13", "SDG 17"],
    "headline_statement": "This procurement saves 42.5kg of plastic and avoids 68kg of CO₂ emissions annually."
  }
}
```

### Prompt Design

**System Prompt Strategy:**
- Establishes the AI as "Raveya's B2B Sustainability Procurement Advisor" — grounds it in the business context
- Lists explicit capabilities and constraints (budget must not be exceeded)
- Enforces JSON-only output to prevent prose contamination

**User Prompt Strategy:**
- Injects real catalog data as grounding context (prevents hallucinated products)
- Provides the exact JSON schema the AI must match — reduces post-processing
- Repeats the budget constraint numerically in the field descriptions as a hard guardrail
- Temporal context: frames the proposal around the client's actual goals

**Business Logic Guardrails (service.py):**
- `_validate_and_fix_budget()` caps AI-returned totals at the client's budget if the AI over-allocates
- All monetary fields are validated as positive numbers via Pydantic

---

## Module 4 — WhatsApp Support Bot

### What it does

1. Receives inbound WhatsApp messages via Twilio webhook
2. Looks up customer orders by phone number from the real database
3. Feeds order data + conversation history into context-aware AI prompt
4. Detects intent: `order_status | return_policy | refund_request | complaint | greeting | escalate`
5. Generates a human-friendly WhatsApp reply
6. Escalates high-priority issues (refund disputes, legal threats) to the support team via Twilio
7. Logs every message turn (inbound + outbound) with intent, escalation flag, and linked order

### API

```
POST /api/v1/whatsapp/webhook                  Twilio webhook (form-encoded)
POST /api/v1/whatsapp/message                  Direct JSON test (no Twilio needed)
GET  /api/v1/whatsapp/conversations/{phone}    Full conversation history
GET  /api/v1/whatsapp/orders/{order_number}    Direct order status lookup
```

### Twilio Setup

1. Create a Twilio account at twilio.com
2. Enable WhatsApp Sandbox: Messaging > Try WhatsApp
3. Set webhook URL: `POST https://<your-host>/api/v1/whatsapp/webhook`
4. Use ngrok for local development: `ngrok http 8000`

### Intent Classification

| Intent | Trigger | Action |
|--------|---------|--------|
| `order_status` | "where is my order", order number mentioned | Queries DB, returns tracking + ETA |
| `return_policy` | "return", "refund policy" | Explains 14-day policy from prompt context |
| `refund_request` | Specific refund ask | Processes or escalates based on amount |
| `complaint` | Negative sentiment | Empathetic reply + possible escalation |
| `escalate` | Legal threats, high-value disputes | Notifies support team via Twilio SMS |
| `greeting` | "hi", "hello" | Friendly welcome |
| `out_of_scope` | Unrelated questions | Polite redirect |

### Prompt Design

**System Prompt Strategy:**
- Single source of truth for return policy — embedded directly so the AI never makes up policy details
- Explicit escalation criteria (amount threshold, threatening language) reduces false escalations
- WhatsApp-format guidance keeps replies under 300 chars and avoids markdown tables/headers

**User Prompt Strategy:**
- Real order data injected per-message — AI cannot hallucinate order status
- Last 3 conversation turns included for continuity (avoids customer repeating themselves)
- JSON output schema with `escalate: bool` field makes escalation decisions programmatically reliable

---

## Architecture Outline — Modules 1 & 3

### Module 1 — AI Auto-Category & Tag Generator

**Data Flow:**
```
Product Input (name, description, image URL?)
      │
      ▼
  AI Prompt (GPT-4o-mini)
  System: "You are a product taxonomy expert for a sustainable e-commerce platform."
  User: "Classify this product, assign category/subcategory, generate 5-10 SEO tags,
         suggest sustainability filters."
      │
      ▼
  Structured JSON Output:
  {
    "primary_category": "<from predefined list>",
    "sub_category": "<suggested>",
    "seo_tags": ["tag1", ...],
    "sustainability_filters": ["plastic-free", "compostable", ...]
  }
      │
      ▼
  Business Logic Validation:
  - Validate primary_category is in ALLOWED_CATEGORIES list
  - Enforce minimum 5 tags
  - Dedup and normalise filter names
      │
      ▼
  Persist to products table (category, tags, filters columns)
  + ai_logs table
```

**Key Design Decisions:**
- Predefined category list injected into system prompt — AI picks from allowed values only
- Sustainability filters are a fixed enum set validated server-side (prevents free-form hallucinations)
- Batch processing endpoint supports up to 50 products per request for catalog imports

**Database Tables:** `products` (category, sub_category, seo_tags JSON, sustainability_filters JSON)

---

### Module 3 — AI Impact Reporting Generator

**Data Flow:**
```
Order Data (items, quantities, sourcing metadata)
      │
      ▼
  Rule-Based Pre-computation (business logic layer):
  - Plastic weight per product type (lookup table)
  - Carbon factor per product category (kg CO₂ per ₹1000)
  - Local sourcing flag per supplier
      │
      ▼
  AI Prompt (GPT-4o-mini)
  System: "You are Raveya's sustainability impact analyst."
  User: "Given these computed metrics, write a compelling human-readable
         impact statement and detailed breakdown."
  Context: Pre-computed numbers (AI does NOT calculate — it narrativises)
      │
      ▼
  Structured JSON Output:
  {
    "plastic_saved_kg": <pre-computed>,
    "carbon_avoided_kg": <pre-computed>,
    "local_sourcing_percentage": <pre-computed>,
    "local_sourcing_summary": "<AI-written narrative>",
    "headline_impact_statement": "<AI-written>",
    "detailed_breakdown": [...]
  }
      │
      ▼
  Stored with order record in order_impact table
  + PDF generation (optional: WeasyPrint)
```

**Key Design Decisions:**
- **AI does NOT do math** — numbers are computed by business logic from lookup tables.
  AI only converts numbers into compelling narrative. This prevents hallucinated impact figures.
- Carbon factors sourced from industry-standard lifecycle assessment data.
- Impact statements cached per order — not regenerated on every view.

---

## Database Schema

```
ai_logs              — All AI prompt+response pairs (shared across modules)
b2b_proposals        — Module 2 generated proposals
orders               — Customer order data (seeded / synced from order management)
whatsapp_conversations — Module 4 message log (inbound + outbound)
```

---

## Technical Requirements Checklist

| Requirement | Implementation |
|-------------|---------------|
| Structured JSON outputs | All AI responses parsed and validated via Pydantic schemas |
| Prompt + response logging | Every call writes to `ai_logs` table with tokens + latency |
| Environment-based API key management | `pydantic-settings` reads from `.env` via `get_settings()` |
| Separation of AI and business logic | `prompts.py` (AI) / `service.py` (business) / `router.py` (HTTP) per module |
| Error handling and validation | Pydantic validators + budget guardrails + try/except in AI client |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `TWILIO_ACCOUNT_SID` | For WhatsApp | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | For WhatsApp | e.g. `whatsapp:+14155238886` |
| `ESCALATION_PHONE` | For WhatsApp | Support team WhatsApp number |
| `DATABASE_URL` | No | Default: SQLite `./raveya.db` |
| `APP_ENV` | No | `development` \| `production` |
