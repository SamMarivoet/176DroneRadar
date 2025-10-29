from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict
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


class PositionSnapshot(BaseModel):
    """A historical snapshot of a plane's position and the recorded timestamp."""
    position: Position
    last_seen: Optional[datetime] = None


class PlaneIn(BaseModel):
    # Accept both existing naming conventions from sources
    # ADS-B / AirplaneFeed (opensky-like)
    msg_id: Optional[str] = None
    source: Optional[str] = None
    icao: Optional[str] = None
    flight: Optional[str] = None
    country: Optional[str] = None
    ts_unix: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    spd: Optional[float] = None
    heading: Optional[float] = None
    vr: Optional[float] = None
    alt_geom: Optional[float] = None
    squawk: Optional[str] = None
    on_ground: Optional[bool] = None

    # Form / dronereport fields
    timestamp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    drone_description: Optional[str] = None
    notes: Optional[str] = None
    photo_filename: Optional[str] = None

    # position and final field requested
    position: Optional[Position] = None
    image_url: Optional[str] = None


    def to_db(self):
        """Create a DB-ready dict containing all present fields.

        We intentionally keep the original field names from the producers
        so the database contains the union of both schemas. Additionally,
        we create/normalize a `position` GeoJSON if lat/lon (or latitude/longitude)
        are present so geo-queries can be executed.
        """
        doc: Dict[str, Any] = {}

        # Copy ADS-B / opensky style fields if present
        for f in ('msg_id','source','icao','flight','country','ts_unix',
                  'lat','lon','alt','spd','heading','vr','alt_geom','squawk','on_ground'):
            v = getattr(self, f, None)
            if v is not None:
                doc[f] = v

        # Copy form fields
        for f in ('timestamp','latitude','longitude','drone_description','notes','photo_filename'):
            v = getattr(self, f, None)
            if v is not None:
                doc[f] = v

        # Copy common telemetry/form fields
        for f in ('alt','spd','heading','vr','alt_geom','image_url'):
            v = getattr(self, f, None)
            if v is not None:
                doc[f] = v

        # Also accept explicit GeoJSON position objects
        if self.position is not None:
            doc['position'] = {'type': self.position.type, 'coordinates': self.position.coordinates}
        else:
            # fall back to lat/lon (adsb style) or latitude/longitude (form style)
            lon = getattr(self, 'lon', None) or getattr(self, 'longitude', None)
            lat = getattr(self, 'lat', None) or getattr(self, 'latitude', None)
            if lat is not None and lon is not None:
                doc['position'] = {'type': 'Point', 'coordinates': [lon, lat]}

        return doc


class PlaneOut(BaseModel):
    # ADS-B / opensky-style fields
    msg_id: Optional[str] = None
    source: Optional[str] = None
    icao: Optional[str] = None
    flight: Optional[str] = None
    country: Optional[str] = None
    ts_unix: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    spd: Optional[float] = None
    heading: Optional[float] = None
    vr: Optional[float] = None
    alt_geom: Optional[float] = None
    squawk: Optional[str] = None
    on_ground: Optional[bool] = None

    # Form / dronereport fields
    timestamp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    drone_description: Optional[str] = None
    notes: Optional[str] = None
    photo_filename: Optional[str] = None

    # position and history
    position: Optional[Position] = None
    position_history: Optional[List[PositionSnapshot]] = None
    # final requested field
    image_url: Optional[str] = None


    class Config:
        orm_mode = True
