# Form (dronereport)

Small Flask app that serves a simple drone-report form and submits reports to the backend.

What changed
------------
- The Form now uploads attached photos to the backend image store and includes an `image_id` in the JSON report it sends to the backend ingestion endpoint (`POST /planes/bulk`).
- If the backend image upload fails the Form falls back to saving the photo locally under `Form/drone-photos/` and still posts the report (without `image_id`).
- The form also exposes saved photos at `/drone-photos/<filename>` for browser preview and local testing.

Behavior details
----------------
- When a user submits the form with a photo the Form will:
  1. Attempt to upload the photo to the backend at `POST {API_URL:-http://backend:8000}/images` (multipart/form-data).
  2. If the upload succeeds the backend returns an `image_id` which the Form includes in the report JSON it posts to `POST {API_URL:-http://backend:8000}/planes/bulk`.
  3. If the upload fails the Form saves the image locally (under `Form/drone-photos/`) and the report is posted without `image_id` but with a local `image_url` for browser preview.

Configuration
-------------
- `API_URL` (env) — base URL of the backend service the Form should talk to. Defaults to `http://backend:8000` in Compose.

Endpoints
---------
- `GET /` — the HTML form UI.
- `POST /submit` — submits a report and optional photo; forwards the report to the backend.
- `POST /save-photo` — legacy direct photo upload endpoint (kept for compatibility).
- `GET /drone-photos/<filename>` — serves saved photos from the local `drone-photos/` folder (useful for browser preview when running the Form container).

Running locally
----------------
- Development (compose): run the top-level compose or the Form component compose. The Form compose sets `API_URL` to point to the backend service on the same network by default.
- Standalone (venv): create a virtualenv, install `Form/requirements.txt`, and run `python Form/main.py`.

Notes and suggestions
---------------------
- Images uploaded by the Form are now stored centrally in the backend's image store (GridFS) when the backend is available. This keeps binary blobs out of the planes collection and centralises storage.
- The Form keeps local copies only as a fallback. If you prefer not to keep local files, we can remove the fallback save.
- For production setups consider storing images in object storage (S3/MinIO) and issuing signed URLs rather than serving images directly from the backend.
