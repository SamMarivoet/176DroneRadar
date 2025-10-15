from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings


client: AsyncIOMotorClient = None
db = None


async def init_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    # Ensure indexes
    # unique on icao24
    await db.planes.create_index('icao24', unique=True)
    # Geo index on position (GeoJSON Point)
    await db.planes.create_index([('position', '2dsphere')])
    # Index last_seen to help with pruning and queries
    await db.planes.create_index('last_seen')


async def close_db():
    global client
    if client:
        client.close()