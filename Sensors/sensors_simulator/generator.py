#!/usr/bin/env python3
"""
Advanced Sensors Simulator
Simulates multiple fixed cameras and radars generating JSON events.
Each camera simulates AI-based drone detection (photo + bounding box).
Each radar produces physical target measurements (speed, heading, altitude, RCS).
Now includes small random per-sensor delays for realistic async behavior.
"""

import os
import time
import json
import random
from datetime import datetime, timezone
from pathlib import Path

# --- Configuration ---
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/data/out"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "3.0"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fixed list of cameras and radars (database knows real positions)
CAMERAS = ["CAM-001", "CAM-002", "CAM-003"]
RADARS = [
    {"id": "RAD-001", "lat": 50.85, "lon": 4.35},
    {"id": "RAD-002", "lat": 50.95, "lon": 4.45},
    {"id": "RAD-003", "lat": 50.75, "lon": 4.25},
]

# --- Helpers ---
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def write_json(obj, prefix):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = OUTPUT_DIR / f"{prefix}_{ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"Wrote {filename}")

# --- Camera event generator ---
def generate_camera_event(camera_id):
    """Simulate AI detection and photo capture from a fixed camera."""
    bbox_length = round(random.uniform(0.3, 2.0), 2)
    bbox_width = round(random.uniform(0.2, 1.5), 2)

    rand_suffix = random.randint(0, 999)
    photo_id = f"PHOTO-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{rand_suffix:03d}"

    payload = {
        "type": "camera",
        "camera_id": camera_id,
        "photo_id": photo_id,
        "timestamp": now_iso(),
        "bbox_size_m": {
            "length_m": bbox_length,
            "width_m": bbox_width
        }
    }
    return payload

# --- Radar event generator ---
def generate_radar_event(radar):
    """Simulate radar measurement with physical parameters."""
    payload = {
        "type": "radar",
        "radar_id": radar["id"],
        "timestamp": now_iso(),
        "position": {"lat": radar["lat"], "lon": radar["lon"]},
        "speed_m_s": round(random.uniform(0, 30), 1),
        "heading_deg": round(random.uniform(0, 359.9), 1),
        "altitude_m": round(random.uniform(10, 200), 1),
        "rcs": round(random.uniform(-10, 10), 1)
    }
    return payload

# --- Main loop ---
def main_loop():
    print("Starting advanced sensors simulator (camera + radar)...")
    print(f"Output folder: {OUTPUT_DIR}")
    while True:
        # Randomly select which sensors report this cycle
        active_cameras = random.sample(CAMERAS, random.randint(1, len(CAMERAS)))
        active_radars = random.sample(RADARS, random.randint(1, len(RADARS)))

        # Simulate camera detections asynchronously
        for cam_id in active_cameras:
            delay = random.uniform(0.2, 1.2)
            time.sleep(delay)
            cam_event = generate_camera_event(cam_id)
            write_json(cam_event, "camera")

        # Simulate radar detections asynchronously
        for radar in active_radars:
            delay = random.uniform(0.2, 1.2)
            time.sleep(delay)
            radar_event = generate_radar_event(radar)
            write_json(radar_event, "radar")

        # Wait for the next cycle
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("Stopped by user")
