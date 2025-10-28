import os
import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, abort

DATA_DIR = Path(os.environ.get("ADSB_DATA_DIR", "/data"))

app = Flask(__name__, static_folder="frontend", static_url_path="")


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


# serve static frontend assets
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
