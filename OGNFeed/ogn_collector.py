import os
import time
import json
import hashlib
import requests
import datetime
import threading
from ogn.client import AprsClient
from ogn.parser import parse, AprsParseError

# ---- Config from .env ----
LAMIN = float(os.getenv("LAMIN", "49.5"))
LAMAX = float(os.getenv("LAMAX", "51.5"))
LOMIN = float(os.getenv("LOMIN", "2.5"))
LOMAX = float(os.getenv("LOMAX", "6.5"))
POLL = float(os.getenv("POLL_SECONDS", str(5)))  # 5 seconds
INGEST_URL = os.getenv("INGEST_URL", "http://localhost:8000/planes/bulk")
TOKEN = os.getenv("INGEST_TOKEN", "")
APRS_USER = os.getenv("APRS_USER", "N0CALL-BE")

# In-memory store: {address: latest beacon data}
gliders_in_belgium = {}

# Aircraft type mapping (from OGN protocol)
AIRCRAFT_TYPES = {
    0: "Reserved",
    1: "Glider",
    2: "Tow plane",
    3: "Helicopter",
    4: "Motorplane",
    5: "UAV/Drone",
    # 6-15: Reserved/future use – default to "Unknown"
}

def is_in_belgium(lat, lon):
    return (LAMIN <= lat <= LAMAX and LOMIN <= lon <= LOMAX)

def msg_id(address: str, ts_aircraft: int) -> str:
    s = f"ogn|{address}|{ts_aircraft}"
    return hashlib.sha1(s.encode()).hexdigest()[:24]

def get_aircraft_type(aircraft_type: int) -> str:
    """Map OGN aircraft_type code to descriptive string."""
    return AIRCRAFT_TYPES.get(aircraft_type, "Unknown")

def process_beacon(raw_message):
    try:
        # Parse with current UTC time as reference
        beacon = parse(raw_message, reference_timestamp=datetime.datetime.utcnow())
        
        if beacon.get('aprs_type') != 'position':
            return
        
        address = beacon.get('address')
        if not address:
            return

        lat = beacon['latitude']
        lon = beacon['longitude']
        alt_m = beacon.get('altitude')  # <-- This is in METERS (OGN standard)
        if alt_m is None:
            return

        timestamp = beacon['timestamp']

        if not is_in_belgium(lat, lon):
            gliders_in_belgium.pop(address, None)
            return

        # Store latest data
        gliders_in_belgium[address] = {
            'name': beacon.get('name'),
            'latitude': lat,
            'longitude': lon,
            'altitude_m': alt_m,
            'timestamp': timestamp,
            'track': beacon.get('track'),
            'ground_speed_knots': beacon.get('ground_speed'),
            'climb_rate_fpm': beacon.get('climb_rate'),
            'on_ground': beacon.get('on_ground', False),
            'aircraft_type': get_aircraft_type(beacon.get('aircraft_type', 0)),  # <-- NEW: Map to string
        }

    except (AprsParseError, KeyError, ValueError, TypeError):
        pass  # Skip bad packets silently

def post_batch(batch):
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        resp = requests.post(INGEST_URL, json=batch, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"[collector] POSTED {len(batch)} OGN records -> {INGEST_URL}")
        return True
    except requests.RequestException as e:
        print(f"[collector] POST ERROR: {e}", flush=True)
        return False

def periodic_post():
    while True:
        batch = []
        snap_ts = int(time.time())

        for address, data in gliders_in_belgium.items():
            ts_unix = int(data['timestamp'].timestamp())

            # Convert units to match OpenSky schema
            spd_ms = data['ground_speed_knots'] * 0.514444 if data['ground_speed_knots'] is not None else None
            vr_ms = data['climb_rate_fpm'] * 0.00508 if data['climb_rate_fpm'] is not None else None

            rec = {
                "msg_id": msg_id(address, ts_unix),
                "source": "ogn",
                "icao": address.lower(),
                "ts_unix": ts_unix,
                # labeling
                "flight": data['name'].strip() if data['name'] else None,
                "country": "OGN: " + data['aircraft_type'],  # <-- NEW: Use aircraft type as "country" field
                # position & motion
                "lat": data['latitude'],
                "lon": data['longitude'],
                "alt": round(data['altitude_m'], 1),           # barometric altitude not in OGN
                "alt_geom": round(data['altitude_m'], 1),  # meters, rounded
                "spd": round(spd_ms, 2) if spd_ms is not None else None,
                "heading": data['track'],
                "vr": round(vr_ms, 2) if vr_ms is not None else None,
                # misc
                "squawk": None,
                "on_ground": data['on_ground'],
            }
            batch.append(rec)

        if batch:
            if not post_batch(batch):
                fname = f"ogn_failed_{int(time.time())}.json"
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(batch, f, indent=2)
                print(f"[collector] SAVED failed batch -> {fname}")

        print(f"[collector] Processed {len(batch)} OGN gliders in Belgium", flush=True)
        time.sleep(POLL)

# === Start APRS Client ===
client = AprsClient(aprs_user=APRS_USER)
client.connect()

# === Start periodic POST thread ===
poster = threading.Thread(target=periodic_post, daemon=True)
poster.start()

print(f"[collector] OGN Belgium tracker STARTED")
print(f"   BBox: lat {LAMIN}–{LAMAX}, lon {LOMIN}–{LOMAX}")
print(f"   Push every {POLL}s to {INGEST_URL}")
print("   Waiting for beacons... (Ctrl+C to stop)\n")

try:
    client.run(callback=process_beacon, autoreconnect=True)
except KeyboardInterrupt:
    print("\n[collector] Shutting down...")
    client.disconnect()