from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, confloat, conint
from typing import Optional, Literal, List
from uuid import uuid4
import time, os, json, redis

r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))

class Location(BaseModel):
    lat: confloat(ge=-90, le=90)
    lon: confloat(ge=-180, le=180)
    precision_m: Optional[conint(ge=0)] = None

class SightingIn(BaseModel):
    event_ts: Optional[int] = None
    loc: Location
    alt_m: Optional[conint(ge=0)] = None
    type: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    contact: Optional[str] = None

class SightingOut(SightingIn):
    id: str
    reported_ts: int
    status: Literal["pending","approved","rejected"] = "pending"
    source: Literal["public-form","internal"] = "public-form"
    confidence: Optional[float] = None

app = FastAPI(title="Drone Sightings API")

app.mount("/", StaticFiles(directory="public", html=True), name="public")

@app.post("/api/sightings", response_model=SightingOut)
async def create_sighting(payload: SightingIn, request: Request):
    ip = request.client.host if request.client else "unknown"
    key = f"rate:sight:{ip}"
    cnt = r.incr(key)
    if cnt == 1:
        r.expire(key, 60)
    if cnt > int(os.getenv("RATE_LIMIT_PER_MIN", "20")):
        raise HTTPException(status_code=429, detail="Too many submissions")

    out = SightingOut(id=str(uuid4()), reported_ts=int(time.time()), **payload.model_dump())
    r.rpush("sightings", out.model_dump_json())
    r.publish("sightings_stream", out.model_dump_json())
    return out

@app.get("/api/sightings", response_model=List[SightingOut])
async def list_sightings(limit: int=200):
    n = r.llen("sightings")
    start = max(0, n - limit)
    items = r.lrange("sightings", start, n)
    return [SightingOut(**json.loads(x)) for x in items]

