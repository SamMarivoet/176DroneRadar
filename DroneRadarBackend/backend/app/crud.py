from . import database
from .schemas import PlaneIn
from typing import List, Optional
from datetime import datetime


async def upsert_plane(plane: PlaneIn):
    """Insert or update a plane.

    If the plane exists, append the previous position/last_seen to
    `position_history` (if a previous position exists) and set the
    new `position` / telemetry fields. If the plane does not exist,
    create it with `created_at`.
    """
    doc = plane.to_db()
    filter_ = {'icao24': plane.icao24}

    # Try to find existing document first so we can preserve the previous position
    existing = await database.db.planes.find_one(filter_)

    if not existing:
        # New document: ensure created_at and optional empty history
        new_doc = {**doc, 'icao24': plane.icao24, 'created_at': datetime.utcnow(), 'position_history': []}
        res = await database.db.planes.insert_one(new_doc)
        return res

    # Existing doc: build update
    update: dict = {}
    set_fields = {**doc, 'updated_at': datetime.utcnow()}

    # Prepare $push for previous position if present
    push_fields = {}
    prev_pos = existing.get('position')
    prev_last_seen = existing.get('last_seen')
    if prev_pos is not None:
        # store a small snapshot of the previous point so we can reconstruct path
        snapshot = {'position': prev_pos, 'last_seen': prev_last_seen or datetime.utcnow()}
        push_fields['position_history'] = snapshot

    if set_fields:
        update['$set'] = set_fields
    if push_fields:
        # Use $push to append the snapshot to position_history
        update['$push'] = {k: v for k, v in push_fields.items()}

    # Perform the update
    res = await database.db.planes.update_one(filter_, update)
    return res


async def upsert_planes_bulk(planes: List[PlaneIn]):
    # For simplicity and correctness (to preserve history) use sequential upserts.
    # If throughput becomes a concern, convert to a bulk_write solution that
    # uses find/update semantics or server-side update pipelines.
    results = []
    for p in planes:
        r = await upsert_plane(p)
        results.append(r)
    return results


async def get_plane(icao24: str) -> Optional[dict]:
    return await database.db.planes.find_one({'icao24': icao24}, projection={'_id': False})


async def query_planes_near(lat: float, lon: float, radius_m: int = 5000, limit: int = 100):
    cursor = database.db.planes.find({
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
    cursor = database.db.planes.find({
        'position': {
            '$geoWithin': {
            '$polygon': polygon
            }
        }
    }, projection={'_id': False}).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_plane(icao24: str):
    return await database.db.planes.delete_one({'icao24': icao24})