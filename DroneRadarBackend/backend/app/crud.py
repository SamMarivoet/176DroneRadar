from . import schemas
from .schemas import PlaneIn
from typing import List, Optional, Dict, Any
from datetime import datetime  # Import for MongoDB-compatible datetime
from fastapi import HTTPException
from pymongo import UpdateOne   

async def upsert_plane(plane: PlaneIn, db) -> Dict[str, Any]:
    doc = plane.to_db()
    filter_ = {"icao24": plane.icao24}
    update = {"$set": doc, "$setOnInsert": {"created_at": bson_datetime.datetime.now()}}
    try:
        res = await db.planes.update_one(filter_, update, upsert=True)
        return {"matched_count": res.matched_count, "modified_count": res.modified_count, "upserted_id": getattr(res, "upserted_id", None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def upsert_planes_bulk(planes: List[PlaneIn], db) -> Dict[str, Any]:
    ops = []
    for p in planes:
        doc = p.to_db()
        ops.append(
            UpdateOne(
                {"icao24": doc["icao24"]},
                {
                    "$set": doc,
                    "$setOnInsert": {"created_at": datetime.now()}
                },
                upsert=True
            )
        )

    if not ops:
        return {"acknowledged": True, "matched_count": 0, "modified_count": 0, "upserted_count": 0}

    try:
        result = await db.planes.bulk_write(ops)
        return {
            "acknowledged": result.bulk_api_result.get("ok", 1) == 1,
            "matched_count": result.bulk_api_result.get("nMatched", 0),
            "modified_count": result.bulk_api_result.get("nModified", 0),
            "upserted_count": result.bulk_api_result.get("nUpserted", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk write error: {str(e)}")

async def get_plane(icao24: str, db) -> Optional[Dict[str, Any]]:
    try:
        doc = await db.planes.find_one({"icao24": icao24}, projection={"_id": False})
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

async def query_planes_near(lat: float, lon: float, radius_m: int = 5000, limit: int = 100, db=None) -> List[Dict[str, Any]]:
    try:
        cursor = db.planes.find({
            "position": {
                "$nearSphere": {
                    "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "$maxDistance": radius_m
                }
            }
        }, projection={"_id": False}).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geospatial query error: {str(e)}")

async def query_planes_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float, limit: int = 100, db=None) -> List[Dict[str, Any]]:
    try:
        polygon = [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
        cursor = db.planes.find({
            "position": {"$geoWithin": {"$polygon": polygon}}
        }, projection={"_id": False}).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bounding box query error: {str(e)}")

async def delete_plane(icao24: str, db) -> Dict[str, Any]:
    try:
        res = await db.planes.delete_one({"icao24": icao24})
        return {"deleted_count": res.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")