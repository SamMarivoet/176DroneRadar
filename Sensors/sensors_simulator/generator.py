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
    Turn our sensor-style dict into something the backend /planes/bulk understands.
    This mirrors what the airplane feed does.
    """
    sensor_type = doc.get("sensor_type", "sensor")
    # try to build some stable-ish id
    drone_id = doc.get("id") or f"{sensor_type}-{random.randint(10000, 99999)}"

    lat = doc.get("lat") or doc.get("latitude")
    lon = doc.get("lon") or doc.get("longitude")
    alt = doc.get("alt") or doc.get("altitude")
    ts = doc.get("timestamp") or now_iso()

    plane_doc = {
        "icao": str(drone_id),
        "source": sensor_type.lower(),
        "last_seen": ts,
    }

    if lat is not None and lon is not None:
        plane_doc["position"] = {
            "type": "Point",
            "coordinates": [float(lon), float(lat)],
        }

    if alt is not None:
        plane_doc["altitude"] = alt

    if image_id:
        plane_doc["image_id"] = image_id

    return plane_doc


def generate_fake_sensor() -> dict:
    """
    This is the part you probably already have.
    I'll make a simple example with two kinds of sensors:
    - radar: always position, sometimes altitude
    - camera: always position, and maybe an image
    Replace with your real logic if it's more complex.
    """
    sensor_type = random.choice(["radar", "camera"])
    base = {
        "sensor_type": sensor_type,
        "timestamp": now_iso(),
        # random-ish coords near somewhere:
        "lat": 52.52 + random.uniform(-0.01, 0.01),
        "lon": 13.405 + random.uniform(-0.01, 0.01),
        "alt": random.randint(30, 120) if sensor_type == "radar" else None,
    }
    return base


def main():
    pool = list_pool_images()
    print(f"[generator] Image pool: {len(pool)} files found in {IMAGE_POOL_DIR}")
    print(f"[generator] Authenticating as: {AUTH_USERNAME}")
    print(f"[generator] Backend URL: {BACKEND_URL}")

    while True:
        sensor_doc = generate_fake_sensor()
        image_id = None

        # if it's a camera sensor, we MAY attach a random image from the pool
        if sensor_doc.get("sensor_type") == "camera" and pool and random.random() < CAMERA_IMAGE_PROB:
            chosen = random.choice(pool)
            try:
                image_id = upload_image_to_backend(chosen)
                print(f"[generator] Uploaded image {chosen.name} → image_id={image_id}")
            except Exception as e:
                print(f"[generator] Failed to upload image {chosen}: {e}")

        # now convert to plane doc and upload to /planes/bulk
        plane_doc = sensor_doc_to_plane(sensor_doc, image_id=image_id)
        try:
            resp = requests.post(
                PLANES_BULK_URL, 
                json=[plane_doc], 
                auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD),
                timeout=10
            )
            resp.raise_for_status()
            print(f"[generator] Sent plane {plane_doc['icao']} (src={plane_doc['source']}) img={image_id}")
        except Exception as e:
            print(f"[generator] Failed to send plane to backend: {e}")

        # optional: keep a local copy for debugging
        if WRITE_LOCAL_JSON:
            fname = OUTPUT_DIR / f"{plane_doc['icao']}_{int(time.time())}.json"
            with fname.open("w", encoding="utf-8") as f:
                json.dump({"sensor": sensor_doc, "plane": plane_doc}, f, indent=2)

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
