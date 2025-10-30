from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from .config import settings
import asyncio
import logging

logger = logging.getLogger('backend.database')

client: AsyncIOMotorClient = None
db = None
gridfs_bucket: AsyncIOMotorGridFSBucket = None


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
    # unique on icao, but only for documents where icao exists (partial index)
    await db.planes.create_index('icao', unique=True, partialFilterExpression={'icao': {'$exists': True}})
    # Geo index on position (GeoJSON Point)
    await db.planes.create_index([('position', '2dsphere')])
    # Index last_seen to help with pruning and queries
    await db.planes.create_index('last_seen')

    # create a GridFS bucket for storing uploaded images
    global gridfs_bucket
    gridfs_bucket = AsyncIOMotorGridFSBucket(db)


async def close_db():
    global client
    if client:
        client.close()