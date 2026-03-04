"""
Prompt templates for the B2B Proposal Generator.
Keeping prompts in a dedicated file makes them easy to iterate and audit.
"""

SYSTEM_PROMPT = """
You are Raveya's B2B Sustainability Procurement Advisor.
Raveya is a sustainable e-commerce platform that sells eco-friendly products:
plastic-free packaging, compostable consumables, recycled-material office supplies,
vegan personal care, organic food products, and solar-powered gadgets.

Your role is to build personalised B2B procurement proposals that:
1. Match the client's industry and sustainability goals.
2. Respect the given budget strictly — total allocated budget MUST NOT exceed it.
3. Highlight environmental impact and ROI benefits.
4. Return ONLY valid JSON with no extra commentary.

Tone: Professional, consultative, data-informed.
""".strip()


def build_user_prompt(
    company_name: str,
    industry: str,
    budget: float,
    sustainability_goals: str,
    product_preferences: str,
    catalog_context: str,
) -> str:
    return f"""
Generate a complete B2B sustainability procurement proposal for the following client.

CLIENT DETAILS:
- Company Name: {company_name}
- Industry: {industry}
- Total Budget (INR): ₹{budget:,.2f}
- Sustainability Goals: {sustainability_goals}
- Product Preferences / Notes: {product_preferences or "None specified"}

RAVEYA PRODUCT CATALOG CONTEXT:
{catalog_context}

OUTPUT FORMAT — return strict JSON matching this exact schema:
{{
  "proposal_title": "<string>",
  "executive_summary": "<2-3 sentence summary>",
  "product_mix": [
    {{
      "product_name": "<name>",
      "category": "<category>",
      "unit_price_inr": <number>,
      "recommended_quantity": <integer>,
      "line_total_inr": <number>,
      "sustainability_benefit": "<brief benefit>",
      "sustainability_tags": ["<tag1>", "<tag2>"]
    }}
  ],
  "budget_allocation": {{
    "total_budget_inr": {budget},
    "total_allocated_inr": <number — must be <= {budget}>,
    "remaining_buffer_inr": <number>,
    "allocation_by_category": {{
      "<category>": <amount_inr>
    }}
  }},
  "cost_breakdown": [
    {{
      "line_item": "<label>",
      "amount_inr": <number>,
      "percentage_of_budget": <number>
    }}
  ],
  "impact_positioning": {{
    "estimated_plastic_avoided_kg": <number>,
    "estimated_co2_avoided_kg": <number>,
    "sdg_alignment": ["<SDG>"],
    "headline_statement": "<compelling 1-sentence impact claim>",
    "talking_points": ["<point1>", "<point2>", "<point3>"]
  }},
  "next_steps": ["<step1>", "<step2>", "<step3>"]
}}

Rules:
- total_allocated_inr must be <= {budget}
- All monetary values are in INR
- Return ONLY the JSON object, no markdown fences
""".strip()


# Representative catalog snippet fed as grounding context
CATALOG_CONTEXT = """
1. EcoCraft Compostable Cutlery Set (100 pcs) — ₹850 — Category: Food & Consumables — Tags: compostable, plastic-free, catering
2. GreenWrap Recycled Bubble Wrap (50m roll) — ₹1,200 — Category: Packaging — Tags: recycled, packaging, warehouse
3. BambooDesk Organiser Set — ₹1,800 — Category: Office Supplies — Tags: bamboo, recycled, zero-waste
4. Refillable Soy-Ink Pen Pack (10 pcs) — ₹650 — Category: Office Supplies — Tags: refillable, low-carbon, office
5. Solar Desk Lamp (USB charging) — ₹3,500 — Category: Energy & Tech — Tags: solar, energy-saving, office
6. Organic Neem Hand Sanitiser (500ml x 12) — ₹2,400 — Category: Personal Care — Tags: vegan, organic, plastic-free
7. Recycled A4 Paper Ream (500 sheets) — ₹420 — Category: Office Supplies — Tags: recycled, FSC-certified, office
8. Beeswax Food Wrap Set (3 pcs) — ₹990 — Category: Food & Consumables — Tags: plastic-free, reusable, kitchen
9. Compostable Mailer Bags (Pack of 50) — ₹1,100 — Category: Packaging — Tags: compostable, plastic-free, e-commerce
10. Bamboo Fibre T-Shirts (Corporate pack 12) — ₹4,800 — Category: Apparel & Merchandise — Tags: bamboo, vegan, corporate-gifting
11. Recycled Tote Bags (Pack of 25) — ₹2,250 — Category: Apparel & Merchandise — Tags: recycled, cotton, promotional
12. Cold-Press Organic Coffee (250g) — ₹680 — Category: Food & Consumables — Tags: organic, fair-trade, office
13. Plant-Based Cleaning Kit (5 products) — ₹3,100 — Category: Facility Management — Tags: vegan, non-toxic, plastic-free
14. Solar Power Bank (20,000 mAh) — ₹5,200 — Category: Energy & Tech — Tags: solar, renewable, gadget
15. Seed Paper Notepad (50 sheets) — ₹780 — Category: Office Supplies — Tags: plantable, zero-waste, promotional
""".strip()
