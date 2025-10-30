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
    # Ensure a canonical `source` exists on the document. The ingestion pipeline
    # generally sets this (e.g. 'opensky' for ADS-B snapshots, 'dronereport' for form reports).
    # If missing, attempt a lightweight inference so consumers (UI) can rely on it.
    if not doc.get('source'):
        inferred = None
        # If we have an ICAO identifier, it's ADS-B/OpenSky telemetry
        if doc.get('icao'):
            inferred = 'opensky'
        # Form-style fields indicate a dronereport
        elif any(k in doc for k in ('drone_description', 'photo_filename', 'notes', 'timestamp', 'latitude', 'longitude')):
            inferred = 'dronereport'
        # default to unknown to avoid accidental classification
        if inferred:
            doc['source'] = inferred
    # Determine canonical icao value (use 'icao' as the canonical key)
    canonical_icao = getattr(plane, 'icao', None) or getattr(plane, 'icao24', None)
    if canonical_icao is None:
        # No icao present: treat this as a standalone report (insert new doc)
        new_doc = {**doc, 'created_at': datetime.utcnow(), 'position_history': [], 'missed_updates': 0}
        res = await database.db.planes.insert_one(new_doc)
        return res

    filter_ = {'icao': canonical_icao}

    # Try to find existing document first so we can preserve the previous position
    existing = await database.db.planes.find_one(filter_)

    if not existing:
        # New document: ensure created_at and optional empty history
        new_doc = {**doc, 'icao': canonical_icao, 'created_at': datetime.utcnow(), 'position_history': [], 'missed_updates': 0}
        res = await database.db.planes.insert_one(new_doc)
        return res

    # Existing doc: build update
    update: dict = {}
    # compute a sensible last_seen timestamp: prefer ts_unix if provided
    ts_unix = doc.get('ts_unix')
    if isinstance(ts_unix, (int, float)):
        try:
            last_seen_val = datetime.utcfromtimestamp(int(ts_unix))
        except Exception:
            last_seen_val = datetime.utcnow()
    else:
        last_seen_val = datetime.utcnow()

    # reset missed_updates to 0 when we see a fresh update
    set_fields = {**doc, 'updated_at': datetime.utcnow(), 'last_seen': last_seen_val, 'missed_updates': 0}

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
    # Treat the incoming batch as a snapshot for this poll.
    #  - Upsert any planes present (resetting their missed_updates to 0)
    #  - If a plane in the incoming batch reports `on_ground` remove it immediately
    #  - For any existing opensky-sourced plane NOT present in this snapshot,
    #    increment `missed_updates` and delete those with missed_updates >= 2
    results = []
    incoming_icaos = []

    # First pass: handle incoming planes
    for p in planes:
        canonical_icao = getattr(p, 'icao', None) or getattr(p, 'icao24', None)
        if canonical_icao:
            incoming_icaos.append(canonical_icao)

        # If plane indicates it's on the ground, remove from DB if we have an icao
        if getattr(p, 'on_ground', None):
            if canonical_icao:
                res = await database.db.planes.delete_one({'icao': canonical_icao})
                results.append(res)
            else:
                # no icao: nothing to remove
                results.append(None)
            continue

        # otherwise upsert normally
        r = await upsert_plane(p)
        results.append(r)

    # Second pass: increment missed_updates for opensky planes not seen in this snapshot
    # Normalize incoming_icaos list for query
    if incoming_icaos:
        await database.db.planes.update_many(
            {'icao': {'$nin': incoming_icaos}, 'source': 'opensky'},
            {'$inc': {'missed_updates': 1}}
        )
    else:
        # No incoming icao values: increment all opensky planes
        await database.db.planes.update_many({'source': 'opensky'}, {'$inc': {'missed_updates': 1}})

    # Remove planes which missed >= 2 consecutive snapshots
    await database.db.planes.delete_many({'source': 'opensky', 'missed_updates': {'$gte': 2}})

    return results


async def get_plane(icao: str) -> Optional[dict]:
    return await database.db.planes.find_one({'icao': icao}, projection={'_id': False})


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


async def delete_plane(icao: str):
    return await database.db.planes.delete_one({'icao': icao})