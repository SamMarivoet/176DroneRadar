from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from . import database, crud
from .routers import planes, images, archive, admin, statistics
import logging
import asyncio

logger = logging.getLogger('backend.main')

# Initialize FastAPI app
app = FastAPI(title='Planes backend')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(planes.router)
app.include_router(images.router)
app.include_router(archive.router)
app.include_router(admin.router)
app.include_router(statistics.router)

# Global reference to background task
archive_task = None


async def archive_drone_reports_periodically():
    """Background task that archives old drone reports every 5 minutes."""
    while True:
        try:
            await asyncio.sleep(300)
            result = await crud.archive_old_drone_reports(age_hours=1.0)
            if result['archived'] > 0:
                logger.info(f"Archived {result['archived']} reports (dronereport, radar, camera)")
        except asyncio.CancelledError:
            logger.info("Archive task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in archive task: {e}", exc_info=True)


@app.on_event('startup')
async def startup_event():
    global archive_task
    await database.init_db()
    archive_task = asyncio.create_task(archive_drone_reports_periodically())
    logger.info("Started background archive task")


@app.on_event('shutdown')
async def shutdown_event():
    global archive_task
    if archive_task:
        archive_task.cancel()
        try:
            await archive_task
        except asyncio.CancelledError:
            pass
    await database.close_db()


@app.get('/health')
async def health():
    return {'status': 'ok'}