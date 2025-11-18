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
    # Index source and last_seen for efficient archiving queries
    await db.planes.create_index([('source', 1), ('last_seen', 1)])

    # Ensure indexes for archive collection
    await db.archive.create_index([('position', '2dsphere')])
    await db.archive.create_index('archived_at')
    await db.archive.create_index('original_last_seen')

    # create a GridFS bucket for storing uploaded images
    global gridfs_bucket
    gridfs_bucket = AsyncIOMotorGridFSBucket(db)

    # Initialize database users with roles (Possible implementation, now our API endpoints are protected using hardcoded users (much simpler), but if multiple users are needed with specific roles this would be an implementation)
#     await init_db_users()


# async def init_db_users():
#     """Create database users with appropriate roles if they don't exist."""
#     db_name = settings.MONGO_DB
    
#     try:
#         # Check if we have permission to create users (requires admin rights)
#         await client.admin.command('ping')
        
#         # Define custom roles for fine-grained permissions
#         roles_to_create = [
#             {
#                 'role': 'airplanefeedRole',
#                 'privileges': [
#                     {
#                         'resource': {'db': db_name, 'collection': 'planes'},
#                         'actions': ['find', 'insert', 'update', 'remove']
#                     }
#                 ],
#                 'roles': []
#             },
#             {
#                 'role': 'operatorRole',
#                 'privileges': [
#                     {
#                         'resource': {'db': db_name, 'collection': 'planes'},
#                         'actions': ['find', 'remove']
#                     },
#                     {
#                         'resource': {'db': db_name, 'collection': 'archive'},
#                         'actions': ['find']
#                     }
#                 ],
#                 'roles': []
#             },
#             {
#                 'role': 'publicRole',
#                 'privileges': [
#                     {
#                         'resource': {'db': db_name, 'collection': 'planes'},
#                         'actions': ['find', 'insert']  # read planes, insert single drone sightings
#                     }
#                 ],
#                 'roles': []
#             }
#         ]
        
#         # Create custom roles
#         for role_def in roles_to_create:
#             try:
#                 await db.command('createRole', role_def['role'], 
#                                 privileges=role_def['privileges'],
#                                 roles=role_def['roles'])
#                 logger.info(f"Created role: {role_def['role']}")
#             except Exception as e:
#                 if 'already exists' in str(e):
#                     logger.debug(f"Role {role_def['role']} already exists")
#                 else:
#                     logger.warning(f"Could not create role {role_def['role']}: {e}")
        
#         # Define users with their roles
#         users_to_create = [
#             {
#                 'user': 'airplanefeed',
#                 'pwd': settings.AIRPLANEFEED_PASSWORD,  # Add to config
#                 'roles': [{'role': 'airplanefeedRole', 'db': db_name}]
#             },
#             {
#                 'user': 'operator',
#                 'pwd': settings.OPERATOR_PASSWORD,  # Add to config
#                 'roles': [{'role': 'operatorRole', 'db': db_name}]
#             }
#         ]
        
#         # Create users
#         for user_def in users_to_create:
#             try:
#                 await db.command('createUser', user_def['user'],
#                                 pwd=user_def['pwd'],
#                                 roles=user_def['roles'])
#                 logger.info(f"Created user: {user_def['user']}")
#             except Exception as e:
#                 if 'already exists' in str(e):
#                     logger.debug(f"User {user_def['user']} already exists")
#                 else:
#                     logger.warning(f"Could not create user {user_def['user']}: {e}")
                    
#     except Exception as e:
#         logger.warning(f"Could not initialize database users (may require admin privileges): {e}")
#         logger.info("Skipping user creation - ensure users are created manually if needed")


async def close_db():
    global client
    if client:
        client.close()