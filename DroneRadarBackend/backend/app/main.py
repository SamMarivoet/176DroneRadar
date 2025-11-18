from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form, Request
from typing import List, Optional
from . import schemas, crud, database
from .config import settings
from .auth import verify_airplanefeed, verify_operator, verify_admin
from fastapi.responses import JSONResponse
from pydantic import parse_obj_as, BaseModel
from fastapi.responses import StreamingResponse
from bson import ObjectId
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import asyncio

logger = logging.getLogger('backend.main')

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title='Planes backend')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global reference to background task
archive_task = None

# Pydantic model for password update
class PasswordUpdate(BaseModel):
    username: str
    new_password: str



async def archive_drone_reports_periodically():
	"""Background task that archives old drone reports every 5 minutes."""
	while True:
		try:
			await asyncio.sleep(300)  # Run every 5 minutes
			result = await crud.archive_old_drone_reports(age_hours=1.0)
			if result['archived'] > 0:
				logger.info(f"Archived {result['archived']} drone reports")
		except asyncio.CancelledError:
			logger.info("Archive task cancelled")
			break
		except Exception as e:
			logger.error(f"Error in archive task: {e}", exc_info=True)
			# Continue running despite errors


@app.on_event('startup')
async def startup_event():
	global archive_task
	await database.init_db()
	# Start the background archiving task
	archive_task = asyncio.create_task(archive_drone_reports_periodically())
	logger.info("Started background archive task")


@app.on_event('shutdown')
async def shutdown_event():
	global archive_task
	# Cancel the background task
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

@app.post('/admin/settings/passwords')
async def update_passwords(
    password_update: PasswordUpdate,
    admin_username: str = Depends(verify_admin)
):
    """Update a user's password. Admin only. Changes persist in database."""
    
    
    # Validate username exists
    if password_update.username not in ["admin", "airplanefeed", "operator"]:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password in database
    success = await database.update_user_password(password_update.username, password_update.new_password)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    logger.info(f"Admin {admin_username} updated password for user: {password_update.username}")
    
    return {
        "status": "ok",
        "username": password_update.username,
        "message": f"Password updated successfully for {password_update.username}"
    }

@app.post('/planes/single')
@limiter.limit("10/hour")  # 10 requests per hour per IP
async def post_single_plane(request: Request, payload: dict):  # ADD request: Request here
    """Post a single plane/drone sighting. Public endpoint - rate limited."""
    try:
        plane = schemas.PlaneIn(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid payload: {e}')
    
    result = await crud.upsert_plane(plane)
    
    return JSONResponse({
        'status': 'ok',
        'icao': plane.icao or plane.icao24,
        'upserted': result.upserted_id is not None,
        'modified': result.modified_count > 0
    })


@app.post('/planes/bulk')
async def post_planes_bulk(
    payload: List[dict],
    username: str = Depends(verify_airplanefeed)  # Only airplanefeed can access
):
    try:
        planes = [schemas.PlaneIn(**p) for p in payload]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid payload: {e}')
    await crud.upsert_planes_bulk(planes)
    return JSONResponse({'ingested': len(planes)})


@app.get('/planes/{icao}', response_model=schemas.PlaneOut)
async def get_plane(icao: str):
	doc = await crud.get_plane(icao)
	if not doc:
		raise HTTPException(status_code=404, detail='Not found')
	return doc


@app.get('/planes')
async def get_planes(
	lat: Optional[float] = Query(None),
	lon: Optional[float] = Query(None),
	radius: Optional[int] = Query(5000),
	bbox: Optional[str] = Query(None),
	limit: Optional[int] = Query(100),
):
	# bbox format: minlat,minlon,maxlat,maxlon
	if lat is not None and lon is not None:
		results = await crud.query_planes_near(lat, lon, radius_m=radius, limit=limit)
		return results
	if bbox:
		try:
			parts = [float(x) for x in bbox.split(',')]
			min_lat, min_lon, max_lat, max_lon = parts
		except Exception:
			raise HTTPException(status_code=400, detail='bbox must be min_lat,min_lon,max_lat,max_lon')
		results = await crud.query_planes_bbox(min_lat, min_lon, max_lat, max_lon, limit=limit)
		return results
	# default: return first N recent planes
	cursor = database.db.planes.find({}, projection={'_id': False}).sort('last_seen', -1).limit(limit)
	return await cursor.to_list(length=limit)


@app.delete('/planes/{icao}')
async def delete_plane(
    icao: str,
    username: str = Depends(verify_operator)  # Only operator can delete
):
    res = await crud.delete_plane(icao)
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Not found')
    return {'deleted': 1}


@app.post('/images')
async def upload_image(file: UploadFile = File(...), icao: Optional[str] = Form(None)):
	"""Upload an image and store it in GridFS. Returns an image_id string."""
	try:
		# store in GridFS using the uploaded filename
		bucket = database.gridfs_bucket
		if bucket is None:
			raise HTTPException(status_code=500, detail='GridFS not initialized')

		# upload_from_stream accepts a filename and a file-like object
		oid = await bucket.upload_from_stream(file.filename or 'image', file.file, metadata={'contentType': file.content_type, 'icao': icao})
		return {'image_id': str(oid)}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/images/{image_id}')
async def get_image(image_id: str):
	"""Stream an image stored in GridFS by its id."""
	try:
		oid = ObjectId(image_id)
	except Exception:
		raise HTTPException(status_code=400, detail='invalid id')

	try:
		# fetch file info to get content type / filename
		files_coll = database.db['fs.files']
		info = await files_coll.find_one({'_id': oid})
		if not info:
			raise HTTPException(status_code=404, detail='not found')

		content_type = (info.get('metadata') or {}).get('contentType') or info.get('contentType') or 'application/octet-stream'

		stream = await database.gridfs_bucket.open_download_stream(oid)

		async def streamer():
			chunk_size = 8192
			while True:
				chunk = await stream.read(chunk_size)
				if not chunk:
					break
				yield chunk

		return StreamingResponse(streamer(), media_type=content_type)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/archive')
async def get_archived_reports(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius: Optional[int] = Query(5000),
    limit: Optional[int] = Query(100),
    username: str = Depends(verify_operator)  # Only operator can view archive
):
    """Retrieve archived drone reports, optionally filtered by location."""
    if lat is not None and lon is not None:
        cursor = database.db.archive.find({
            'position': {
                '$nearSphere': {
                    '$geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                    '$maxDistance': radius
                }
            }
        }, projection={'_id': False}).limit(limit)
    else:
        # Return most recently archived reports
        cursor = database.db.archive.find({}, projection={'_id': False}).sort('archived_at', -1).limit(limit)
    
    return await cursor.to_list(length=limit)


@app.post('/archive/manual')
async def trigger_manual_archive():
	"""Manually trigger archiving of old drone reports."""
	result = await crud.archive_old_drone_reports(age_hours=1.0)
	return result