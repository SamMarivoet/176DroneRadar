import os
import json
import threading
import time
import tempfile
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, abort, Response, stream_with_context, request
import requests

# where to write planefeed.json
DATA_DIR = Path(os.environ.get("ADSB_DATA_DIR", "/data"))
# how often to poll the backend for plane data (seconds)
POLL_SECONDS = int(os.environ.get("MAP_POLL_SECONDS", "5"))
# backend API base (used by poller)
BACKEND_API = os.environ.get("BACKEND_API", "http://backend:8000")

app = Flask(__name__, static_folder="frontend", static_url_path="")


def poll_backend_loop():
    """Background thread: poll backend /planes and write local planefeed.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    outfile = DATA_DIR / "planefeed.json"
    url = f"{BACKEND_API.rstrip('/')}/planes?limit=1000"
    while True:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                planes = resp.json()
                # normalize into {"planes": [...]}
                if isinstance(planes, dict) and 'planes' in planes:
                    data = planes
                else:
                    data = {"planes": planes}
                # atomic write
                with tempfile.NamedTemporaryFile('w', delete=False, dir=DATA_DIR, encoding='utf-8') as tf:
                    json.dump(data, tf, ensure_ascii=False)
                    tmpname = tf.name
                os.replace(tmpname, outfile)
            else:
                # keep previous file if backend unavailable
                app.logger.warning(f"Map GUI poll: backend returned {resp.status_code}")
        except Exception as e:
            app.logger.debug(f"Map GUI poll error: {e}")
        time.sleep(POLL_SECONDS)


# start background poller thread
threading.Thread(target=poll_backend_loop, daemon=True).start()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/reports")
def get_reports():
    """Return all drone reports (JSON files except planefeed.json)."""
    reports = []
    for file in DATA_DIR.glob("*.json"):
        if file.name == "planefeed.json":
            continue
        try:
            with open(file) as f:
                data = json.load(f)
                reports.append(data)
        except Exception:
            continue
    return jsonify(reports)


@app.route("/api/planes")
def get_planes():
    """Return current plane telemetry feed."""
    planefile = DATA_DIR / "planefeed.json"
    if not planefile.exists():
        return jsonify({"planes": []})
    try:
        with open(planefile) as f:
            data = json.load(f)
    except Exception:
        return jsonify({"planes": []})
    return jsonify(data)


@app.route('/api/auth', methods=['POST'])
def proxy_auth():
    """Proxy authentication to backend with real client IP."""
    try:
        payload = request.get_json(force=True)
    except Exception:
        payload = {}

    backend_url = f"{BACKEND_API.rstrip('/')}/admin/auth/verify"
    
    # Forward client IP
    headers = {
        'X-Forwarded-For': request.remote_addr,
        'X-Real-IP': request.remote_addr,
        'Content-Type': 'application/json'
    }
    
    try:
        resp = requests.post(backend_url, json=payload, headers=headers, timeout=8)
        try:
            data = resp.json()
            return jsonify(data), resp.status_code
        except Exception:
            return Response(resp.content, status=resp.status_code)
    except Exception as e:
        app.logger.debug(f"Auth proxy error: {e}")
        return jsonify({"detail": "auth backend unreachable"}), 502


@app.route('/api/images/<image_id>')
def get_image(image_id: str):
    """Proxy endpoint for images stored in the central backend (GridFS).

    Behavior:
    - If BACKEND_API is reachable, this will forward the request to
      BACKEND_API + /images/<image_id> and stream the response back to the client.
    - If the central backend is unavailable or returns a non-200 status, the
      endpoint falls back to returning a local placeholder image from the
      frontend `icons` folder so frontend developers can continue working.

    This keeps the API stable for frontend development. If you want to
    implement direct GridFS access in this container later, replace the
    proxy logic with Motor/GridFS reads.
    """
    # Try proxying to central backend first
    try:
        backend_url = f"{BACKEND_API.rstrip('/')}/images/{image_id}"
        resp = requests.get(backend_url, stream=True, timeout=8)
        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', 'application/octet-stream')
            def generate():
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            return Response(stream_with_context(generate()), content_type=content_type)
        else:
            app.logger.warning(f"Image proxy: backend returned {resp.status_code} for {image_id}")
    except Exception as e:
        app.logger.debug(f"Image proxy error contacting backend: {e}")

    # Fallback: serve a local placeholder image so frontend devs have something to work with
    try:
        return send_from_directory(app.static_folder + '/icons', 'plane.png')
    except Exception:
        # As a last resort, return 404 JSON
        return jsonify({'error': 'image not available', 'image_id': image_id}), 404


# Note: unified design — all data is in `planefeed.json` (planes). We intentionally
# removed the legacy /api/reports and /api/feed endpoints so the frontend and
# other consumers only use /api/planes.


# serve static frontend assets
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


@app.route('/api/statistics/<path:path>', methods=['GET', 'POST'])
def proxy_statistics(path):
    backend_url = f"{BACKEND_API.rstrip('/')}/statistics/{path}"
    try:
        if request.method == 'GET':
            resp = requests.get(backend_url, headers=request.headers, timeout=8)
        else:
            resp = requests.post(backend_url, json=request.get_json(force=True), headers=request.headers, timeout=8)

        return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        app.logger.debug(f"Statistics proxy error: {e}")
        return jsonify({"detail": "statistics backend unreachable"}), 502
