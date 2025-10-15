import os
import time
import json
import hashlib
import requests
import redis

# ---- Config from .env ----
OPENSKY_URL = os.getenv("OPENSKY_URL", "https://opensky-network.org/api/states/all")
LAMIN = float(os.getenv("LAMIN", "50.5"))
LAMAX = float(os.getenv("LAMAX", "51.5"))
LOMIN = float(os.getenv("LOMIN", "3.8"))
LOMAX = float(os.getenv("LOMAX", "5.5"))
POLL = float(os.getenv("POLL_SECONDS", "5"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

r = redis.from_url(REDIS_URL)

def msg_id(icao: str, ts_aircraft: int) -> str:
    """Stable unique id per aircraft + aircraft-time for idempotency."""
    s = f"opensky|{icao}|{ts_aircraft}"
    return hashlib.sha1(s.encode()).hexdigest()[:24]

def fetch_opensky() -> dict:
    """Fetch JSON data from OpenSky Network for our bounding box."""
    params = dict(lamin=LAMIN, lamax=LAMAX, lomin=LOMIN, lomax=LOMAX)
    resp = requests.get(OPENSKY_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def main():
    print(f"[collector] OpenSky bbox "
          f"(lat {LAMIN}..{LAMAX}, lon {LOMIN}..{LOMAX}); poll={POLL}s")
    while True:
        try:
            data = fetch_opensky()
            # snapshot time from server (fallback to local time if missing)
            snap_ts = int(data.get("time") or time.time())
            states = data.get("states", []) or []

            pushed = 0
            for s in states:
                # indices per OpenSky API:
                # 0=icao24, 1=callsign, 2=origin_country, 3=time_position,
                # 4=last_contact, 5=lon, 6=lat, 7=baro_altitude,
                # 8=on_ground, 9=velocity, 10=true_track, 11=vertical_rate,
                # 13=geo_altitude, 14=squawk
                icao = s[0]
                if not icao:
                    continue

                lon, lat = s[5], s[6]
                if lat is None or lon is None:
                    continue

                # choose the aircraft's own time first
                last_contact  = s[4]
                time_position = s[3]
                if isinstance(last_contact, (int, float)):
                    ts_aircraft = int(last_contact)
                elif isinstance(time_position, (int, float)):
                    ts_aircraft = int(time_position)
                else:
                    ts_aircraft = snap_ts

                rec = {
                    # identity & timestamps
                    "msg_id": msg_id(icao, ts_aircraft),
                    "source": "opensky",
                    "icao": icao.lower(),
                    "ts_aircraft": ts_aircraft,           # <-- use this for history
                    "ingest_ts_unix": int(time.time()),   # when we processed it

                    # labeling / extras
                    "flight": s[1].strip() if s[1] else None,
                    "country": s[2],

                    # position & motion
                    "lat": lat,
                    "lon": lon,
                    "alt": s[7],           # baro altitude (meters; may be None)
                    "alt_geom": s[13],     # geometric altitude (meters; may be None)
                    "spd": s[9],           # velocity (m/s)
                    "heading": s[10],      # degrees (true track)
                    "vr": s[11],           # vertical rate (m/s)

                    # misc flags/codes
                    "squawk": s[14],
                    "on_ground": s[8],
                }

                r.rpush("positions", json.dumps(rec))
                pushed += 1

            print(f"[collector] queued {pushed} records "
                  f"(queue_len={r.llen('positions')})", flush=True)

        except Exception as e:
            print("[collector] error:", e, flush=True)

        time.sleep(POLL)

if __name__ == "__main__":
    main()
