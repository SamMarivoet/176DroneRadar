from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends
from .config import settings

# Singleton class to manage MongoDB client and database
class MongoDB:
    _client: AsyncIOMotorClient | None = None
    _db = None

    @classmethod
    async def init(cls, mongo_uri: str, db_name: str):
        if cls._client is None:
            cls._client = AsyncIOMotorClient(mongo_uri)
            cls._db = cls._client[db_name]
            # Verify connection and create geo index
            await cls._db.command("ping")
            await cls._db.planes.create_index([("position", "2dsphere")])

    @classmethod
    async def close(cls):
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None

    @classmethod
    def get_db(cls):
        if cls._db is None:
            raise RuntimeError("Database not initialized. Ensure MongoDB.init is called on startup.")
        return cls._db

# Dependency to inject the database
async def get_db():
    return MongoDB.get_db()

# Initialize database on startup
async def init_db():
    await MongoDB.init(settings.MONGO_URI, settings.MONGO_DB)

# Close database on shutdown
async def close_db():
    await MongoDB.close()