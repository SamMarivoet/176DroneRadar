import os
import time
import json
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load .env if present (local development convenience)
load_dotenv()

# ---- Config from env / .env ----
OPENSKY_URL = os.getenv("OPENSKY_URL", "https://opensky-network.org/api/states/all")
LAMIN = float(os.getenv("LAMIN", "50.5"))
LAMAX = float(os.getenv("LAMAX", "51.5"))
LOMIN = float(os.getenv("LOMIN", "3.8"))
LOMAX = float(os.getenv("LOMAX", "5.5"))
# default poll every 5 seconds (accept env var as string or number)
POLL = float(os.getenv("POLL_SECONDS", "5"))
# Where to POST the batch (backend service in compose)
INGEST_URL = os.getenv("INGEST_URL", "http://backend:8000/planes/bulk")

# OpenSky credentials (paid / higher limits)
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")


# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "airplanefeed")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "pass")


def msg_id(icao: str, ts_aircraft: int) -> str:
    """Stable unique id per aircraft + aircraft-time for idempotency."""
    s = f"opensky|{icao}|{ts_aircraft}"
    return hashlib.sha1(s.encode()).hexdigest()[:24]


def fetch_opensky() -> dict:
    """Fetch JSON data from OpenSky Network for our bounding box."""
    params = dict(lamin=LAMIN, lamax=LAMAX, lomin=LOMIN, lomax=LOMAX)

    auth = None
    if OPENSKY_USERNAME and OPENSKY_PASSWORD:
        auth = HTTPBasicAuth(OPENSKY_USERNAME, OPENSKY_PASSWORD)

    resp = requests.get(
        OPENSKY_URL,
        params=params,
        auth=auth,
        timeout=20
    )
    resp.raise_for_status()
    return resp.json()


def post_batch(batch):
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(
            INGEST_URL, 
            json=batch, 
            headers=headers, 
            auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD),
            timeout=30
        )
        resp.raise_for_status()
        print(f"[collector] posted {len(batch)} records -> {INGEST_URL}")
        return True
    except requests.RequestException as e:
        print(f"[collector] post error: {e}", flush=True)
        return False


def main():
    print(f"[collector] OpenSky bbox (lat {LAMIN}..{LAMAX}, lon {LOMIN}..{LOMAX}); poll={POLL}s")
    print(f"[collector] Authenticating as: {AUTH_USERNAME}")
    while True:
        try:
            data = fetch_opensky()
            snap_ts = int(data.get("time") or time.time())
            states = data.get("states", []) or []

            batch = []
            for s in states:
                icao = s[0]
                if not icao:
                    continue

                lon, lat = s[5], s[6]
                if lat is None or lon is None:
                    continue

                last_contact = s[4]
                time_position = s[3]
                if isinstance(last_contact, (int, float)):
                    ts_aircraft = int(last_contact)
                elif isinstance(time_position, (int, float)):
                    ts_aircraft = int(time_position)
                else:
                    ts_aircraft = snap_ts

                rec = {
                    "msg_id": msg_id(icao, ts_aircraft),
                    "source": "opensky",
                    "icao": icao.lower(),
                    "ts_unix": ts_aircraft,
                    # labeling / extras
                    "flight": s[1].strip() if s[1] else None,
                    "country": s[2],
                    # position & motion
                    "lat": lat,
                    "lon": lon,
                    "alt": s[7],
                    "alt_geom": s[13],
                    "spd": s[9],
                    "heading": s[10],
                    "vr": s[11],
                    # misc
                    "squawk": s[14],
                    "on_ground": s[8],
                }
                batch.append(rec)

            if batch:
                ok = post_batch(batch)
                if not ok:
                    # fallback: write batch to a local file for later re-processing
                    fname = f"opensky_failed_{int(time.time())}.json"
                    with open(fname, "w", encoding="utf-8") as f:
                        json.dump(batch, f)
                    print(f"[collector] saved failed batch to {fname}")

            print(f"[collector] processed {len(batch)} records", flush=True)

        except Exception as e:
            print("[collector] error:", e, flush=True)

        time.sleep(POLL)


if __name__ == "__main__":
    main()
