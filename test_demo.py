"""
Integration tests / demo script.
Tests all API endpoints with real HTTP calls.
Run AFTER starting the server:  python test_demo.py
"""
import httpx
import json
import asyncio

BASE = "http://localhost:8000"


async def test_b2b_proposal():
    print("\n" + "=" * 60)
    print("MODULE 2 — B2B Proposal Generator")
    print("=" * 60)

    payload = {
        "company_name": "EcoLogistics India Pvt Ltd",
        "industry": "Logistics & Supply Chain",
        "budget": 75000,
        "sustainability_goals": (
            "Eliminate single-use plastic in all warehouse operations, "
            "reduce corporate carbon footprint by 30% in 12 months, "
            "achieve 100% sustainable packaging by Q3 2026."
        ),
        "product_preferences": "Focus on packaging, office supplies and facility management products."
    }

    async with httpx.AsyncClient(timeout=60) as client:
        print(f"\nPOST {BASE}/api/v1/proposals/generate")
        print(f"Company: {payload['company_name']} | Budget: ₹{payload['budget']:,}")

        resp = await client.post(f"{BASE}/api/v1/proposals/generate", json=payload)

        if resp.status_code == 201:
            data = resp.json()
            print(f"\n✓ Proposal #{data['id']} generated: {data['proposal_title']}")
            print(f"\n  Executive Summary: {data['executive_summary']}")
            print(f"\n  Products ({len(data['product_mix'])} items):")
            for p in data["product_mix"]:
                print(f"    - {p['product_name']} x{p['recommended_quantity']} = ₹{p['line_total_inr']:,.2f}")
            alloc = data["budget_allocation"]
            print(f"\n  Budget: ₹{alloc['total_allocated_inr']:,.2f} / ₹{alloc['total_budget_inr']:,.2f}")
            print(f"  Buffer: ₹{alloc['remaining_buffer_inr']:,.2f}")
            impact = data["impact_positioning"]
            print(f"\n  Impact: {impact['headline_statement']}")
            print(f"  Plastic avoided: {impact['estimated_plastic_avoided_kg']}kg | CO₂ avoided: {impact['estimated_co2_avoided_kg']}kg")
            return data["id"]
        else:
            print(f"✗ Error {resp.status_code}: {resp.text}")
            return None


async def test_get_proposal(proposal_id: int):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE}/api/v1/proposals/{proposal_id}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✓ Retrieved proposal #{proposal_id}: {data['proposal_title']}")
        else:
            print(f"✗ Error {resp.status_code}")


async def test_whatsapp_bot():
    print("\n" + "=" * 60)
    print("MODULE 4 — WhatsApp Support Bot")
    print("=" * 60)

    test_cases = [
        {
            "label": "Order Status Query",
            "phone_number": "+919876543210",
            "message": "Hi, where is my order ORD-001? When will it arrive?",
        },
        {
            "label": "Return Policy Question",
            "phone_number": "+918765432109",
            "message": "What is your return policy? Can I return sanitisers?",
        },
        {
            "label": "Refund Request (escalation trigger)",
            "phone_number": "+916543210987",
            "message": "I want a refund for my cancelled order ORD-005 of ₹1800. I will take legal action if not resolved today.",
        },
        {
            "label": "Greeting",
            "phone_number": "+917654321098",
            "message": "Hello!",
        },
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        for case in test_cases:
            print(f"\n--- {case['label']} ---")
            print(f"  Phone: {case['phone_number']}")
            print(f"  Message: {case['message']}")

            resp = await client.post(
                f"{BASE}/api/v1/whatsapp/message",
                json={"phone_number": case["phone_number"], "message": case["message"]},
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"  Intent: {data['intent']} | Confidence: {data['confidence']:.2f} | Escalated: {data['escalated']}")
                print(f"  Reply: {data['response_message']}")
                if data["escalated"]:
                    print(f"  ⚠ Escalation reason: {data['escalation_reason']}")
            else:
                print(f"  ✗ Error {resp.status_code}: {resp.text}")


async def test_order_lookup():
    print("\n" + "=" * 60)
    print("Order Direct Lookup")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        for order_num in ["ORD-001", "ORD-003", "ORD-999"]:
            resp = await client.get(f"{BASE}/api/v1/whatsapp/orders/{order_num}")
            if resp.status_code == 200:
                o = resp.json()
                print(f"\n✓ {o['order_number']}: {o['status']} | Customer: {o['customer_name']} | ₹{o['total_amount']:,.2f}")
            else:
                print(f"\n✗ {order_num}: {resp.status_code}")


async def main():
    print("Raveya AI — Integration Test Suite")
    print(f"Target: {BASE}")

    # Health check
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{BASE}/health")
            print(f"\nHealth: {resp.json()}")
        except Exception as e:
            print(f"\n✗ Server not reachable: {e}")
            print("  Start the server first: python main.py")
            return

    proposal_id = await test_b2b_proposal()
    if proposal_id:
        await test_get_proposal(proposal_id)

    await test_order_lookup()
    await test_whatsapp_bot()

    print("\n" + "=" * 60)
    print("Test suite complete.")
    print(f"Interactive docs: {BASE}/docs")


if __name__ == "__main__":
    asyncio.run(main())
