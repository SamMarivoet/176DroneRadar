from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Optional
from .. import schemas, crud, database
from ..auth import verify_airplanefeed, verify_operator
from ..dependencies import limiter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/planes", tags=["planes"])


@router.post('/single')
@limiter.limit("10/hour")
async def post_single_plane(request: Request, payload: dict):
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