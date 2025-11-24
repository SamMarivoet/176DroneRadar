import os
import time
import json
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load .env if present (local development convenience)
load_dotenv()

# ---- Config from env / .env ----
OPENSKY_URL = os.getenv("OPENSKY_URL", "https://opensky-network.org/api/states/all")
OPENSKY_TOKEN_URL = os.getenv("OPENSKY_TOKEN_URL", "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token")

LAMIN = float(os.getenv("LAMIN", "50.5"))
LAMAX = float(os.getenv("LAMAX", "51.5"))
LOMIN = float(os.getenv("LOMIN", "3.8"))
LOMAX = float(os.getenv("LOMAX", "5.5"))
# default poll every 5 seconds (accept env var as string or number)
POLL = float(os.getenv("POLL_SECONDS", "5"))
# Where to POST the batch (backend service in compose)
INGEST_URL = os.getenv("INGEST_URL", "http://backend:8000/planes/bulk")

# OpenSky OAuth2 credentials (new API clients - preferred)
OPENSKY_CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID")
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET")

# OpenSky legacy credentials (for backward compatibility)
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")

# Authentication credentials for backend
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "airplanefeed")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "pass")

# Token management
_access_token = None
_token_expires_at = None


def get_opensky_token() -> str:
    """
    Obtain an OAuth2 access token from OpenSky Network.
    Tokens are cached and reused until they expire (30 minutes).
    """
    global _access_token, _token_expires_at
    
    # Return cached token if still valid (with 1 minute buffer)
    if _access_token and _token_expires_at:
        if datetime.now() < _token_expires_at - timedelta(minutes=1):
            return _access_token
    
    # Request new token
    print("[collector] Requesting new OpenSky OAuth2 token...")
    
    try:
        resp = requests.post(
            OPENSKY_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": OPENSKY_CLIENT_ID,
                "client_secret": OPENSKY_CLIENT_SECRET
            },
            timeout=10
        )
        resp.raise_for_status()
        
        token_data = resp.json()
        _access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 1800)  # Default 30 minutes
        
        _token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        print(f"[collector] Token obtained, expires in {expires_in} seconds")
        return _access_token
        
    except requests.RequestException as e:
        print(f"[collector] Failed to obtain OAuth2 token: {e}", flush=True)
        raise


def msg_id(icao: str, ts_aircraft: int) -> str:
    """Stable unique id per aircraft + aircraft-time for idempotency."""
    s = f"opensky|{icao}|{ts_aircraft}"
    return hashlib.sha1(s.encode()).hexdigest()[:24]


def fetch_opensky() -> dict:
    """Fetch JSON data from OpenSky Network for our bounding box."""
    params = dict(lamin=LAMIN, lamax=LAMAX, lomin=LOMIN, lomax=LOMAX)
    
    headers = {}
    auth = None
    
    # Prefer OAuth2 if credentials are available
    if OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET:
        try:
            token = get_opensky_token()
            headers["Authorization"] = f"Bearer {token}"
            print("[collector] Using OAuth2 authentication")
        except Exception as e:
            print(f"[collector] OAuth2 failed, falling back to basic auth if available: {e}", flush=True)
            # Fall back to basic auth if OAuth2 fails
            if OPENSKY_USERNAME and OPENSKY_PASSWORD:
                auth = HTTPBasicAuth(OPENSKY_USERNAME, OPENSKY_PASSWORD)
                print("[collector] Using legacy basic authentication")
    elif OPENSKY_USERNAME and OPENSKY_PASSWORD:
        # Use legacy basic auth
        auth = HTTPBasicAuth(OPENSKY_USERNAME, OPENSKY_PASSWORD)
        print("[collector] Using legacy basic authentication")
    else:
        print("[collector] No authentication configured (using anonymous/rate-limited API)")
    
    try:
        resp = requests.get(
            OPENSKY_URL,
            params=params,
            headers=headers,
            auth=auth,
            timeout=20
        )
        
        # Handle token expiration
        if resp.status_code == 401 and headers.get("Authorization"):
            print("[collector] Token expired or invalid, requesting new token...")
            global _access_token, _token_expires_at
            _access_token = None
            _token_expires_at = None
            
            # Retry with new token
            token = get_opensky_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.get(
                OPENSKY_URL,
                params=params,
                headers=headers,
                timeout=20
            )
        
        resp.raise_for_status()
        return resp.json()
        
    except requests.RequestException as e:
        print(f"[collector] OpenSky API error: {e}", flush=True)
        raise


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
    print(f"[collector] Backend authentication as: {AUTH_USERNAME}")
    
    # Log authentication method
    if OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET:
        print(f"[collector] OpenSky OAuth2 configured (client_id: {OPENSKY_CLIENT_ID[:8]}...)")
    elif OPENSKY_USERNAME and OPENSKY_PASSWORD:
        print(f"[collector] OpenSky legacy auth configured (username: {OPENSKY_USERNAME})")
    else:
        print("[collector] No OpenSky credentials - using anonymous API (rate limited)")
    
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
