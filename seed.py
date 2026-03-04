"""
Seed demo data into MongoDB for development and testing.
Run standalone:  python seed.py
Or called automatically at startup.
"""
import asyncio
from datetime import datetime

from database.database import get_database, init_db
from database.models import OrderDoc


DEMO_ORDERS = [
    {"order_number": "ORD-001", "customer_phone": "+919876543210", "customer_name": "Priya Sharma",
     "status": "shipped", "total_amount": 4850.00,
     "items_summary": "BambooDesk Organiser Set x2, Refillable Soy-Ink Pen Pack x3",
     "tracking_number": "BLUEDRT1234567", "estimated_delivery": "2026-03-07"},
    {"order_number": "ORD-002", "customer_phone": "+919876543210", "customer_name": "Priya Sharma",
     "status": "delivered", "total_amount": 2400.00,
     "items_summary": "Organic Neem Hand Sanitiser 500ml x12",
     "tracking_number": "BLUEDRT9876543", "estimated_delivery": "2026-02-28"},
    {"order_number": "ORD-003", "customer_phone": "+918765432109", "customer_name": "Rahul Mehta",
     "status": "processing", "total_amount": 12300.00,
     "items_summary": "Solar Desk Lamp x2, Solar Power Bank x1, Plant-Based Cleaning Kit x1",
     "tracking_number": None, "estimated_delivery": "2026-03-10"},
    {"order_number": "ORD-004", "customer_phone": "+917654321098", "customer_name": "Ananya Iyer",
     "status": "pending", "total_amount": 3300.00,
     "items_summary": "EcoCraft Compostable Cutlery Set x2, Beeswax Food Wrap Set x3",
     "tracking_number": None, "estimated_delivery": "2026-03-12"},
    {"order_number": "ORD-005", "customer_phone": "+916543210987", "customer_name": "Vikram Nair",
     "status": "cancelled", "total_amount": 1800.00,
     "items_summary": "Recycled A4 Paper Ream x2, Seed Paper Notepad x2",
     "tracking_number": None, "estimated_delivery": None},
    {"order_number": "ORD-006", "customer_phone": "+915432109876", "customer_name": "Sneha Patel",
     "status": "shipped", "total_amount": 7050.00,
     "items_summary": "Bamboo Fibre T-Shirts Corporate Pack x1, Recycled Tote Bags x25",
     "tracking_number": "DTDC20260301", "estimated_delivery": "2026-03-06"},
]


async def seed_demo_data():
    """Insert demo orders if they don't already exist (idempotent)."""
    db = get_database()
    inserted = 0
    for data in DEMO_ORDERS:
        existing = await db["orders"].find_one({"order_number": data["order_number"]})
        if existing:
            continue
        doc = OrderDoc(**data)
        await db["orders"].insert_one(doc.model_dump())
        inserted += 1
    if inserted:
        print(f"Seeded {inserted} demo orders.")
    else:
        print("Demo orders already present  -  skipped.")


if __name__ == "__main__":
    async def main():
        await init_db()
        await seed_demo_data()
        print("Done.")
    asyncio.run(main())

