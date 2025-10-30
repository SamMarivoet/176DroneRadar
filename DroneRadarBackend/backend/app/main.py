from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form
from typing import List, Optional
from . import schemas, crud, database
from .config import settings
from fastapi.responses import JSONResponse
from pydantic import parse_obj_as
from fastapi.responses import StreamingResponse
from bson import ObjectId
import io


app = FastAPI(title='Planes backend')


@app.on_event('startup')
async def startup_event():
	await database.init_db()


@app.on_event('shutdown')
async def shutdown_event():
	await database.close_db()


@app.get('/health')
async def health():
	return {'status': 'ok'}


@app.post('/planes/bulk')
async def post_planes_bulk(payload: List[dict]):
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
async def delete_plane(icao: str):
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