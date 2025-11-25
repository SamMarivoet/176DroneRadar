from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Optional
from .. import schemas, crud, database
from ..auth import verify_airplanefeed, verify_operator
from ..dependencies import limiter
from fastapi.responses import JSONResponse
from pymongo.results import InsertOneResult, UpdateResult
import logging
import time

logger = logging.getLogger("backend.routers.planes")

router = APIRouter(prefix="/planes", tags=["planes"])


@router.post('/single')
@limiter.limit("10/hour")
async def post_single_plane(request: Request, payload: dict):
    """Post a single plane/drone sighting. Public endpoint - rate limited."""
    try:
        plane = schemas.PlaneIn(**payload)
        if not plane.icao:
            plane.icao = f"report_{int(time.time() * 1000000)}"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid payload: {e}')
    
    result = await crud.upsert_plane(plane)

    # Safely determine operation outcome; InsertOneResult does not have upserted_id/modified_count
    inserted_id = None
    modified_count = 0
    upserted_id = None

    if isinstance(result, InsertOneResult):
        inserted_id = result.inserted_id
    elif isinstance(result, UpdateResult):
        modified_count = result.modified_count
        upserted_id = result.upserted_id
    else:
        # Unexpected result type; log for diagnostics
        logger.warning(f"Unexpected result type from upsert_plane: {type(result)}")

    payload_out = {
        'status': 'ok',
        'icao': plane.icao or plane.icao24,
        'inserted': inserted_id is not None,
        'modified': modified_count > 0,
        'upserted_id': upserted_id,
        'inserted_id': inserted_id
    }
    logger.debug(f"/planes/single outcome: {payload_out}")
    return JSONResponse(payload_out)


@router.post('/bulk')
async def post_planes_bulk(
    request: Request,
    payload: List[dict],
    username: str = Depends(verify_airplanefeed)
):
    try:
        planes = [schemas.PlaneIn(**p) for p in payload]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid payload: {e}')
    await crud.upsert_planes_bulk(planes)
    return JSONResponse({'ingested': len(planes)})


@router.get('/{icao}', response_model=schemas.PlaneOut)
async def get_plane(icao: str):
    doc = await crud.get_plane(icao)
    if not doc:
        raise HTTPException(status_code=404, detail='Not found')
    return doc


@router.get('')
async def get_planes(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius: Optional[int] = Query(5000),
    bbox: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
):
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
    cursor = database.db.planes.find({}, projection={'_id': False}).sort('last_seen', -1).limit(limit)
    return await cursor.to_list(length=limit)


@router.delete('/{icao}')
async def delete_plane(
    request: Request,
    icao: str,
    username: str = Depends(verify_operator)
):
    res = await crud.delete_plane(icao)
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Not found')
    return {'deleted': 1}