from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from .config import settings
import asyncio
import logging
import bcrypt

logger = logging.getLogger('backend.database')

client: AsyncIOMotorClient = None
db = None
gridfs_bucket: AsyncIOMotorGridFSBucket = None


async def init_db(retries: int = 20, delay: float = 0.5):
    """Initialize MongoDB client and ensure required indexes.

    This function will retry connecting to Mongo for a short period to
    tolerate container startup ordering when running under Docker Compose.
    """
    global client, db, gridfs_bucket
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    # Wait for connection
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
    # Index source and last_seen for efficient archiving queries
    await db.planes.create_index([('source', 1), ('last_seen', 1)])
    # Additional indexes to speed statistics queries and admin filters
    await db.planes.create_index('drone_type')
    await db.planes.create_index('altitude')
    await db.planes.create_index('admin_visible')
    await db.planes.create_index([('created_at', -1)])

    # Ensure indexes for archive collection
    await db.archive.create_index([('position', '2dsphere')])
    await db.archive.create_index('archived_at')
    await db.archive.create_index('original_last_seen')

    # Ensure unique index on username in users collection
    await db.users.create_index('username', unique=True)

    # Initialize GridFS
    gridfs_bucket = AsyncIOMotorGridFSBucket(db)

    # Initialize default users if they don't exist
    await init_default_users()


async def init_default_users():
    """Create default users with passwords from config if they don't exist."""
    default_users = [
        {
            'username': 'admin',
            'password': settings.ADMIN_PASSWORD,
            'role': 'admin'
        },
        {
            'username': 'analyst',
            'password': settings.AIRPLANEFEED_PASSWORD,
            'role': 'analyst'
        },
        {
            'username': 'authority',
            'password': settings.OPERATOR_PASSWORD,
            'role': 'authority'
        }
    ]

    for user_data in default_users:
        existing = await db.users.find_one({'username': user_data['username']})
        if not existing:
            # Hash password before storing
            hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
            await db.users.insert_one({
                'username': user_data['username'],
                'password_hash': hashed_password,
                'role': user_data['role']
            })
            logger.info(f"Created default user: {user_data['username']}")


async def get_user(username: str):
    """Get user from database."""
    return await db.users.find_one({'username': username})


async def update_user_password(username: str, new_password: str):
    """Update user password in database."""
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    result = await db.users.update_one(
        {'username': username},
        {'$set': {'password_hash': hashed_password}}
    )
    return result.modified_count > 0


async def close_db():
    global client
    if client:
        client.close()