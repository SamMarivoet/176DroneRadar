from flask import Flask, request, jsonify, render_template_string, send_from_directory
import requests
from datetime import datetime
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure folders exist
os.makedirs("reports", exist_ok=True)
os.makedirs("drone-photos", exist_ok=True)

# Configure maximum file size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Serve your HTML form (optional — or you can serve it directly with nginx)
@app.route("/")
def form():
    # You can replace this inline version by reading your actual file instead:
    # return open("drone-report-form.html").read()
    return render_template_string(open("drone-report-form.html").read())


@app.route("/submit", methods=["POST"])
def submit_report():
    """Receives form data and writes a JSON report file."""
    try:
        logger.debug("Received form submission")
        logger.debug(f"Files in request: {list(request.files.keys())}")
        
        # Extract form data
        timestamp = request.form.get("timestamp")
        drone_description = request.form.get("drone_description", "")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        notes = request.form.get("notes", "")
        photo = request.files.get("photo")

        # Validate required fields
        if not timestamp or not latitude or not longitude:
            return jsonify({"error": "Timestamp, latitude, and longitude are required."}), 400

        # Build report data (unified naming). Keep original field names and
        # include `source` so backend can identify origin. Add `image_url`.
        report = {
            "source": "dronereport",
            "timestamp": timestamp,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "drone_description": drone_description or None,
            "notes": notes or None,
            "photo_filename": None,
            "image_url": None,
        }

        # Handle photo if present: upload to backend images endpoint so images are stored in DB
        if photo and photo.filename:
            logger.debug(f"Processing photo: {photo.filename}")
            # create a deterministic filename based on timestamp for readability
            photo_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M")
            photo_filename = f"drone_photo_{photo_timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"

            API_URL = os.getenv('API_URL', 'http://backend:8000')
            images_url = f"{API_URL.rstrip('/')}/images"

            try:
                # photos come as werkzeug FileStorage; use its stream for multipart upload
                files = {'file': (photo_filename, photo.stream, photo.content_type)}
                data = {}
                # optionally include an icao if present in the form (helps indexing)
                icao_val = request.form.get('icao')
                if icao_val:
                    data['icao'] = icao_val

                resp = requests.post(images_url, files=files, data=data, timeout=15)
                if resp.status_code in (200, 201):
                    j = resp.json()
                    image_id = j.get('image_id')
                    report['photo_filename'] = photo_filename
                    report['image_id'] = image_id
                    # keep image_url as a browser-accessible path as well
                    report['image_url'] = request.host_url.rstrip('/') + '/' + os.path.join('drone-photos', photo_filename)
                else:
                    logger.warning(f"Backend image upload failed: {resp.status_code}")
                    # fallback to saving locally
                    photo_folder = "drone-photos"
                    photo_path = os.path.join(photo_folder, photo_filename)
                    photo.save(photo_path)
                    report["photo_filename"] = photo_filename
                    report["image_url"] = os.path.join('drone-photos', photo_filename)
            except Exception as e:
                logger.error(f"Error uploading photo to backend: {e}")
                # fallback: save locally
                photo_folder = "drone-photos"
                photo_path = os.path.join(photo_folder, photo_filename)
                try:
                    photo.save(photo_path)
                    report["photo_filename"] = photo_filename
                    report["image_url"] = os.path.join('drone-photos', photo_filename)
                except Exception as e2:
                    logger.error(f"Failed to save photo locally after upload error: {e2}")
                    return jsonify({"error": "Failed to save or upload photo"}), 500
                
        # Compose image_url (make it an absolute URL based on the incoming request so
        # other services can (optionally) fetch it). If no photo was saved this remains None.
        if report.get('image_url'):
            # request.host_url contains scheme+host+port from the browser request
            report['image_url'] = request.host_url.rstrip('/') + '/' + report['image_url']

        # Attempt to POST the report to the backend ingestion endpoint so form reports
        # are stored centrally. Use API_URL environment variable if present.
        API_URL = os.getenv('API_URL', 'http://backend:8000')
        ingest_url = f"{API_URL.rstrip('/')}/planes/single"

        try:
            resp = requests.post(ingest_url, json=report, timeout=10)
            if resp.status_code in (200, 201):
                return jsonify({"status": "ok", "ingested": True, "backend_response": resp.json()}), 200
            else:
                # fallback: save local copy and return error info
                filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join("reports", filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                return jsonify({"status": "ok", "ingested": False, "saved_to": filepath, "backend_status": resp.status_code}), 502
        except requests.RequestException as e:
            # network/backend failure: persist locally and return error
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join("reports", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.error(f"Failed to POST to backend ingest endpoint: {e}")
            return jsonify({"status": "ok", "ingested": False, "saved_to": filepath, "error": str(e)}), 502
        
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/save-photo", methods=["POST"])
def save_photo():
    """Handle direct photo uploads."""
    try:
        logger.debug("Received photo upload request")
        if 'photo' not in request.files:
            logger.warning("No photo file in request")
            return jsonify({"error": "No photo file"}), 400
            
        photo = request.files['photo']
        if not photo.filename:
            logger.warning("Empty photo filename")
            return jsonify({"error": "No photo selected"}), 400
            
        timestamp = request.form.get('timestamp')
        if not timestamp:
            logger.warning("No timestamp provided")
            return jsonify({"error": "No timestamp provided"}), 400
            
        # Generate timestamp-based filename
        photo_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M")
        photo_filename = f"drone_photo_{photo_timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        photo_path = os.path.join("drone-photos", photo_filename)
        
        logger.debug(f"Saving photo to: {photo_path}")
        photo.save(photo_path)
        
        if os.path.exists(photo_path):
            logger.debug(f"Photo saved successfully at {photo_path}")
            return jsonify({"status": "ok", "filename": photo_filename}), 200
        else:
            logger.error(f"Failed to save photo at {photo_path}")
            return jsonify({"error": "Failed to save photo"}), 500
            
    except Exception as e:
        logger.error(f"Error saving photo: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


@app.route('/drone-photos/<path:filename>')
def serve_photo(filename):
    """Serve saved photos (used when building absolute image_url values)."""
    return send_from_directory('drone-photos', filename)
