from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends
from .config import settings
import asyncio
import logging

<<<<<<< HEAD
logger = logging.getLogger('backend.database')
=======
# Singleton class to manage MongoDB client and database
class MongoDB:
    _client: AsyncIOMotorClient | None = None
    _db = None
>>>>>>> d2e8c31a6fe70289d93161a505fc1ed22bc7d81b

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

<<<<<<< HEAD
async def init_db(retries: int = 20, delay: float = 0.5):
    """Initialize MongoDB client and ensure required indexes.

    This function will retry connecting to Mongo for a short period to
    tolerate container startup ordering when running under Docker Compose.
    """
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    # Wait for the server to accept commands (ping)
    for attempt in range(1, retries + 1):
        try:
            await client.admin.command('ping')
            break
        except Exception as exc:
            logger.debug('Mongo ping failed (attempt %d/%d): %s', attempt, retries, exc)
            if attempt == retries:
                logger.exception('Could not connect to MongoDB after %d attempts', retries)
                raise
            await asyncio.sleep(delay)

    # Ensure indexes
    # unique on icao24
    await db.planes.create_index('icao24', unique=True)
    # Geo index on position (GeoJSON Point)
    await db.planes.create_index([('position', '2dsphere')])
    # Index last_seen to help with pruning and queries
    await db.planes.create_index('last_seen')

=======
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
>>>>>>> d2e8c31a6fe70289d93161a505fc1ed22bc7d81b

# Close database on shutdown
async def close_db():
    await MongoDB.close()