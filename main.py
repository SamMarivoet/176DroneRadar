from flask import Flask, request, jsonify, render_template_string, send_from_directory
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

        # Build report data
        report = {
            "timestamp": timestamp,
            "latitude": latitude,
            "longitude": longitude,
            "drone_description": drone_description or None,
            "notes": notes or None,
            "photo_filename": None
        }

        # Save photo if present
        if photo and photo.filename:
            logger.debug(f"Processing photo: {photo.filename}")
            photo_folder = "drone-photos"
            
            # Generate timestamp-based filename
            photo_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M")
            photo_filename = f"drone_photo_{photo_timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_path = os.path.join(photo_folder, photo_filename)
            
            logger.debug(f"Saving photo to: {photo_path}")
            photo.save(photo_path)
            
            # Verify the file was saved
            if os.path.exists(photo_path):
                logger.debug(f"Photo saved successfully at {photo_path}")
                report["photo_filename"] = photo_filename
            else:
                logger.error(f"Failed to save photo at {photo_path}")
                return jsonify({"error": "Failed to save photo"}), 500
                
        # Save report JSON
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join("reports", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        return jsonify({"status": "ok", "saved_to": filepath})
        
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
