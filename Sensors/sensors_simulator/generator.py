# Sensors/sensors_simulator/generator.py
import os
import time
import json
import random
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone

# ====== CONFIG ======
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/data/out"))  # optional local dump
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
PLANES_BULK_URL = f"{BACKEND_URL}/planes/bulk"
IMAGES_URL = f"{BACKEND_URL}/images"

IMAGE_POOL_DIR = Path(os.getenv("IMAGE_POOL_DIR", "/data/image_pool"))
CAMERA_IMAGE_PROB = float(os.getenv("CAMERA_IMAGE_PROB", "0.4"))  # 40% chance
WRITE_LOCAL_JSON = os.getenv("WRITE_LOCAL_JSON", "true").lower() == "true"

# kept for backwards compatibility (not used directly anymore)
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "2.0"))

# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "airplanefeed")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "pass")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def list_pool_images():
    if not IMAGE_POOL_DIR.exists():
        return []
    exts = {".jpg", ".jpeg", ".png"}
    return [p for p in IMAGE_POOL_DIR.iterdir() if p.suffix.lower() in exts]


def upload_image_to_backend(path: Path) -> str | None:
    """POST image to backend /images and return image_id."""
    with path.open("rb") as f:
        files = {"file": (path.name, f, "application/octet-stream")}
        resp = requests.post(IMAGES_URL, files=files, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("image_id") or data.get("id")


def sensor_doc_to_plane(doc: dict, image_id: str | None = None) -> dict:
    """
    Convert a sensor-style dict into a backend-compatible plane document.
    Harmonized with airplane/glider schema: uses lat, lon, alt, spd, heading, ts_unix, country.
    """
    sensor_type = doc.get("sensor_type", "sensor")
    drone_id = doc.get("id") or f"{sensor_type}-{random.randint(10000, 99999)}"

    lat = doc.get("lat") or doc.get("latitude")
    lon = doc.get("lon") or doc.get("longitude")
    alt = doc.get("alt") or doc.get("altitude")
    spd = doc.get("spd") or doc.get("speed")
    heading = doc.get("heading")
    ts = doc.get("timestamp") or now_iso()

    plane_doc = {
        "icao": str(drone_id),
        "source": sensor_type.lower(),
        "ts_unix": int(time.time()),
        "country": "site_name",  # for frontend consistency
    }

    if lat is not None:
        plane_doc["lat"] = float(lat)
    if lon is not None:
        plane_doc["lon"] = float(lon)
    if alt is not None:
        plane_doc["alt"] = alt
    if spd is not None:
        plane_doc["spd"] = spd
    if heading is not None:
        plane_doc["heading"] = heading
    if image_id:
        plane_doc["image_id"] = image_id
    if "site_name" in doc:
        plane_doc["country"] = doc["site_name"]

    return plane_doc



# ====== BELGIAN SITES FOR SIMULATION ======
# (name, lat, lon)
SITES = [
    ("Brussels Airport (Zaventem)",               50.9014, 4.4844),
    ("Brussels South Charleroi Airport",          50.4592, 4.4538),
    ("Antwerp International Airport",             51.1894, 4.4603),
    ("Ostend–Bruges International Airport",       51.1997, 2.8742),
    ("Liège Airport",                             50.6375, 5.4433),
    ("Port of Antwerp",                           51.2700, 4.3367),
    ("Port of Zeebrugge",                         51.3371, 3.2173),
    ("Doel Nuclear Power Station",                51.3254, 4.2597),
    ("Tihange Nuclear Power Station",             50.5334, 5.2714),
    ("Coo-Trois-Ponts Hydroelectric Power Station", 50.3570, 5.8450),
    ("Vilvoorde Power Station",                   50.9414, 4.4246),
    ("Wilmarsdonk Total Power Station",           51.2717, 4.3262),
    ("NATO Headquarters (Brussels, Evere)",       50.8794, 4.4217),
    ("SHAPE – Supreme Headquarters Allied Powers Europe", 50.4367, 3.9936),
    ("Chièvres Air Base",                         50.5810, 3.8280),
    ("Kleine Brogel Air Base",                    51.1667, 5.4500),
    ("Brunssum NATO JFC Support Site",            50.9460, 5.9690),
    ("Florennes Air Base",                        50.2439, 4.6461),
    ("Beauvechain Air Base",                      50.7583, 4.7686),
    ("Melsbroek Air Base",                        50.9120, 4.5110),
    ("Koksijde Air Base",                         51.0900, 2.6522),
]


def generate_fake_sensor() -> dict:
    """
    Generate a fake sensor hit somewhere around a Belgian critical site.

    - Randomly pick one of the SITES above.
    - Add a tiny jitter around that site (so points don't overlap perfectly).
    - Randomly choose sensor type: radar or camera.
    """
    sensor_type = random.choice(["radar", "camera"])

    site_name, base_lat, base_lon = random.choice(SITES)

    # Small jitter ~ up to ~1km-ish (0.01 degrees is ~1.1 km at these latitudes)
    lat_jitter = random.uniform(-0.01, 0.01)
    lon_jitter = random.uniform(-0.01, 0.01)

    lat = base_lat + lat_jitter
    lon = base_lon + lon_jitter





    base = {
        "sensor_type": sensor_type,
        "timestamp": now_iso(),
        "lat": lat,
        "lon": lon,
        "alt": random.randint(30, 120) if sensor_type == "radar" else None,
        "spd": random.randint(10, 100) if sensor_type == "radar" else None,
        "site_name": site_name,
    }
    return base


def main():
    pool = list_pool_images()
    print(f"[generator] Image pool: {len(pool)} files found in {IMAGE_POOL_DIR}")
    print(f"[generator] Authenticating as: {AUTH_USERNAME}")
    print(f"[generator] Backend URL: {BACKEND_URL}")
    print(f"[generator] Using {len(SITES)} Belgian sites for sensor positions")

    while True:
        sensor_doc = generate_fake_sensor()
        image_id = None

        # if it's a camera sensor, we MAY attach a random image from the pool
        if (
            sensor_doc.get("sensor_type") == "camera"
            and pool
            and random.random() < CAMERA_IMAGE_PROB
        ):
            chosen = random.choice(pool)
            try:
                image_id = upload_image_to_backend(chosen)
                print(
                    f"[generator] Uploaded image {chosen.name} → image_id={image_id}"
                )
            except Exception as e:
                print(f"[generator] Failed to upload image {chosen}: {e}")

        # now convert to plane doc and upload to /planes/bulk
        plane_doc = sensor_doc_to_plane(sensor_doc, image_id=image_id)
        try:
            resp = requests.post(
                PLANES_BULK_URL,
                json=[plane_doc],
                auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD),
                timeout=10,
            )
            resp.raise_for_status()
            print(
                f"[generator] Sent plane {plane_doc['icao']} "
                f"(src={plane_doc['source']}, site={sensor_doc.get('site_name')}) "
                f"img={image_id}"
            )
        except Exception as e:
            print(f"[generator] Failed to send plane to backend: {e}")

        # optional: keep a local copy for debugging
        if WRITE_LOCAL_JSON:
            fname = OUTPUT_DIR / f"{plane_doc['icao']}_{int(time.time())}.json"
            with fname.open("w", encoding="utf-8") as f:
                json.dump(
                    {"sensor": sensor_doc, "plane": plane_doc},
                    f,
                    indent=2,
                )

        # Wait a random time between 40 and 90 seconds
        sleep_for = random.uniform(40.0, 90.0)
        print(
            f"[generator] Sleeping for {sleep_for:.1f} seconds before next sensor doc"
        )
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
