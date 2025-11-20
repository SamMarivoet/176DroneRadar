from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
import time
import bleach


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
    image_id: Optional[str] = None

    # Validate latitude/longitude ranges
    @validator('lat', 'latitude')
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return v

    @validator('lon', 'longitude')
    def validate_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('longitude must be between -180 and 180')
        return v

    # Validate altitude (reasonable ranges)
    @validator('alt', 'alt_geom')
    def validate_altitude(cls, v):
        if v is not None:
            if v < -500:  # Below Dead Sea level
                raise ValueError('altitude too low (minimum: -500m)')
            if v > 20000:  # Above typical drone/aircraft ceiling
                raise ValueError('altitude too high (maximum: 20000m)')
        return v

    # Validate speed (reasonable ranges)
    @validator('spd')
    def validate_speed(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError('speed cannot be negative')
            if v > 1000:  # ~3600 km/h (faster than most aircraft)
                raise ValueError('speed too high (maximum: 1000 m/s)')
        return v

    # Validate heading
    @validator('heading')
    def validate_heading(cls, v):
        if v is not None and not (0 <= v <= 360):
            raise ValueError('heading must be between 0 and 360 degrees')
        return v

    # Validate vertical rate
    @validator('vr')
    def validate_vertical_rate(cls, v):
        if v is not None:
            if abs(v) > 100:  # ~6000 m/min (extreme climb/descent)
                raise ValueError('vertical rate too extreme (maximum: ±100 m/s)')
        return v

    # Validate timestamp
    @validator('ts_unix')
    def validate_timestamp(cls, v):
        if v is not None:
            now = int(time.time())
            # Reject timestamps from future or > 24 hours old
            if v > now + 60:  # 1 minute tolerance for clock skew
                raise ValueError('timestamp cannot be in the future')
            if v < now - 86400:  # 24 hours
                raise ValueError('timestamp too old (maximum age: 24 hours)')
        return v

    # Validate ICAO hex code format
    @validator('icao')
    def validate_icao(cls, v):
        if v is not None:
            # ICAO should be 6 hex characters or alphanumeric for drones
            if len(v) > 24:  # Reasonable max length
                raise ValueError('icao identifier too long')
            if len(v) < 3:
                raise ValueError('icao identifier too short')
        return v

    # Validate squawk code
    @validator('squawk')
    def validate_squawk(cls, v):
        if v is not None:
            # Squawk codes are 4 octal digits (0-7)
            if not (len(v) == 4 and all(c in '0123456789' for c in v)):
                raise ValueError('squawk must be 4 digits')
        return v

    # # Validate source
    # @validator('source')
    # def validate_source(cls, v):
    #     if v is not None:
    #         valid_sources = ['opensky', 'ogn', 'dronereport', 'radar', 'camera', 'adsb', 'mlat']
    #         if v.lower() not in valid_sources:
    #             raise ValueError(f'source must be one of: {", ".join(valid_sources)}')
    #     return v.lower() if v else v

    # Validate text fields for length and content
    @validator('drone_description', 'notes', 'flight', 'country')
    def validate_text_fields(cls, v):
        if v is not None:
            if len(v) > 1000:  # Prevent excessive text
                raise ValueError('text field too long (maximum: 1000 characters)')
            
            # Allow only safe tags and attributes (or none)
            v = bleach.clean(
                v,
                tags=[],  # No HTML tags allowed
                attributes={},  # No attributes allowed
                strip=True  # Strip disallowed tags instead of escaping
            )
            
            # Additional: normalize whitespace
            v = ' '.join(v.split())
        
        return v

    # Validate image_id format (MongoDB ObjectId)
    @validator('image_id')
    def validate_image_id(cls, v):
        if v is not None:
            # MongoDB ObjectId is 24 hex characters
            if len(v) != 24 or not all(c in '0123456789abcdefABCDEF' for c in v):
                raise ValueError('invalid image_id format (must be 24 hex characters)')
        return v

    # Validate no NoSQL injection patterns in sensitive fields
    @validator('icao', 'flight', 'country')
    def validate_no_nosql_injection(cls, v):
        if v is not None:
            # Reject MongoDB operators
            if isinstance(v, dict) or '$' in str(v):
                raise ValueError('invalid characters in field')
        return v

    # Root validator to ensure at least position OR coordinates exist
    @root_validator
    def validate_has_position(cls, values):
        position = values.get('position')
        lat = values.get('lat') or values.get('latitude')
        lon = values.get('lon') or values.get('longitude')
        
        # At least one position method must be provided
        if position is None and (lat is None or lon is None):
            raise ValueError('must provide either position or lat/lon coordinates')
        
        return values


    def to_db(self):
        """Create a DB-ready dict containing all present fields."""
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
        for f in ('alt','spd','heading','vr','alt_geom','image_url','image_id'):
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
    image_id: Optional[str] = None

    class Config:
        orm_mode = True
