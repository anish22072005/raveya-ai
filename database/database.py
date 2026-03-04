"""
MongoDB async client using Motor.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db_name]


async def get_db():
    """FastAPI dependency that returns the MongoDB database."""
    yield get_database()


async def init_db():
    """Create MongoDB indexes."""
    db = get_database()
    await db["orders"].create_index("order_number", unique=True)
    await db["orders"].create_index("customer_phone")
    await db["whatsapp_conversations"].create_index("phone_number")
    await db["whatsapp_conversations"].create_index("created_at")
    await db["b2b_proposals"].create_index("created_at")
    await db["ai_logs"].create_index("module")


async def close_db():
    """Close MongoDB connection on shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
