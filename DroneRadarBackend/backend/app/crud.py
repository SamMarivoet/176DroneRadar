from .database import db
from .schemas import PlaneIn
from typing import List, Optional
from datetime import datetime


async def upsert_plane(plane: PlaneIn):
    doc = plane.to_db()
    filter_ = {'icao24': plane.icao24}
    update = {'$set': doc, '$setOnInsert': {'created_at': datetime.utcnow()}}
    res = await db.planes.update_one(filter_, update, upsert=True)
    return res


async def upsert_planes_bulk(planes: List[PlaneIn]):
    # Perform many upserts (simple loop). For very high throughput, replace with bulk_write.
    results = []
    for p in planes:
        r = await upsert_plane(p)
        results.append(r)
    return results


async def get_plane(icao24: str) -> Optional[dict]:
    return await db.planes.find_one({'icao24': icao24}, projection={'_id': False})


async def query_planes_near(lat: float, lon: float, radius_m: int = 5000, limit: int = 100):
    cursor = db.planes.find({
        'position': {
            '$nearSphere': {
                '$geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                '$maxDistance': radius_m
            }
        }
    }, projection={'_id': False}).limit(limit)
    return await cursor.to_list(length=limit)


async def query_planes_bbox(min_lat, min_lon, max_lat, max_lon, limit=100):
    # polygon defined in GeoJSON coordinate order (lon lat)
    polygon = [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
    cursor = db.planes.find({
        'position': {
            '$geoWithin': {
            '$polygon': polygon
            }
        }
    }, projection={'_id': False}).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_plane(icao24: str):
    return await db.planes.delete_one({'icao24': icao24})