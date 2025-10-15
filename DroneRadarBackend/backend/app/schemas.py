from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class Position(BaseModel):
    # GeoJSON Point: [longitude, latitude]
    type: str = Field('Point', const=True)
    coordinates: list[float] = Field(..., min_items=2, max_items=2)


    @validator('coordinates')
    def coords_range(cls, v):
        lon, lat = v
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('coordinates must be [lon, lat] in valid ranges')
        return v


class PlaneIn(BaseModel):
    icao24: str
    callsign: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    track: Optional[float] = None
    speed: Optional[float] = None
    last_seen: Optional[datetime] = None


    def to_db(self):
        doc = dict(
            icao24=self.icao24,
            callsign=self.callsign,
            altitude=self.altitude,
            track=self.track,
            speed=self.speed,
        )
        if self.latitude is not None and self.longitude is not None:
            doc['position'] = {'type': 'Point', 'coordinates': [self.longitude, self.latitude]}
        if self.last_seen:
            doc['last_seen'] = self.last_seen
        return {k: v for k, v in doc.items() if v is not None}


class PlaneOut(BaseModel):
    icao24: str
    callsign: Optional[str] = None
    altitude: Optional[float] = None
    track: Optional[float] = None
    speed: Optional[float] = None
    last_seen: Optional[datetime] = None
    position: Optional[Position] = None


    class Config:
        orm_mode = True