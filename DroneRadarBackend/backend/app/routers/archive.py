from fastapi import APIRouter, Depends, Query
from typing import Optional
from .. import crud, database
from ..auth import verify_operator

router = APIRouter(prefix="/archive", tags=["archive"])


@router.get('')
async def get_archived_reports(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius: Optional[int] = Query(5000),
    limit: Optional[int] = Query(100),
    username: str = Depends(verify_operator)
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
        cursor = database.db.archive.find({}, projection={'_id': False}).sort('archived_at', -1).limit(limit)
    
    return await cursor.to_list(length=limit)


@router.post('/manual')
async def trigger_manual_archive(username: str = Depends(verify_operator)):
    """Manually trigger archiving of old drone reports."""
    result = await crud.archive_old_drone_reports(age_hours=1.0)
    return result