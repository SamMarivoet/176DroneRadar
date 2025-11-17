# 176DroneRadar — backend

Run locally:

```bash
docker compose -f ./DroneRadarBackend/docker-compose.yml up --build -d
```

The backend will then be available on http://localhost:8000

## Key endpoints

- `POST /planes/bulk` — accepts a list of plane objects (JSON) and upserts them.
- `GET /planes` — query planes; supports `lat` + `lon` + `radius` (metres) or `bbox`.
- `GET /planes/{icao}` — get single plane by ICAO.
# 176DroneRadar — backend

This folder contains the FastAPI-based backend service that accepts telemetry and form reports, stores them in MongoDB, and serves query endpoints used by the Map GUI and other clients.

Quick start (full stack)
------------------------
From the repository root you can bring up the full development stack (recommended):

```powershell
docker compose up --build -d
```

The backend will then be available on http://localhost:8000

Run the backend component only
----------------------------
If you only want to run the backend service during development:

```powershell
# build and start the backend service using the component compose
docker compose -f .\DroneRadarBackend\docker-compose.yml up --build -d
```

Or build/run the image directly from the backend folder:

```powershell
docker build -t droneradar-backend:local ./DroneRadarBackend/backend
docker run -p 8000:8000 --env-file .env -e MONGO_URI="mongodb://root:example@mongo:27017/?authSource=admin" droneradar-backend:local
```

Run locally in a Python virtualenv (fast iteration):

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r DroneRadarBackend\backend\requirements.txt
uvicorn DroneRadarBackend.backend.app.main:app --reload --port 8000
```


Key endpoints
-------------
- `POST /planes/bulk` — accepts a list of plane objects (JSON) and upserts them.
- `GET /planes` — query planes; supports `lat` + `lon` + `radius` (metres) or `bbox`.
- `GET /planes/{icao}` — get single plane by ICAO.
- `GET /health` — health check.
- `GET /archive` — query archived drone reports (see below).
- `POST /archive/manual` — manually trigger archiving of old drone reports.

Requirements
------------
The backend's runtime dependencies are listed in `DroneRadarBackend/backend/requirements.txt`.

Current pinned deps (see file for exact versions):
```
fastapi
uvicorn
pymongo
motor
pydantic
python-dotenv
```

Viewing the database (mongo-express)
----------------------------------
The component compose includes a lightweight web UI (`mongo-express`) for browsing the MongoDB instance.

Start the component compose from `DroneRadarBackend`:

```powershell
docker compose -f .\DroneRadarBackend\docker-compose.yml up --build -d
```

Open the web UI in your browser at `http://localhost:8081` (port may vary if you changed mappings).

Authentication and credentials
------------------------------
- The backend and compose files use a MongoDB root user `root` with password `example` by default for local development.
- By default mongo-express in the component compose is configured to connect using the above URI. If you want mongo-express to require basic auth, set the environment variables on the `mongo-express` service:

```
ME_CONFIG_BASICAUTH_USERNAME=root
ME_CONFIG_BASICAUTH_PASSWORD=example
```

Connection details (for external tools)

- MongoDB URI (used by the backend): `mongodb://root:example@mongo:27017/?authSource=admin`
- To connect from host tools (Compass, mongosh) use the published host port: `mongodb://root:example@localhost:27017/?authSource=admin`

Quick mongosh one-liners
------------------------
```powershell
# show a sample document
mongosh "mongodb://root:example@localhost:27017/planesdb?authSource=admin" --eval "db.planes.findOne()"

# list indexes
mongosh "mongodb://root:example@localhost:27017/planesdb?authSource=admin" --eval "printjson(db.planes.getIndexes())"
```

Testing notes
-------------
There are no automated tests included in this repository's backend component. For manual/smoke testing use the sample payloads in `DroneRadarBackend/sample_json/` and POST them to `POST /planes/bulk`, then verify results using the API (`GET /planes/{icao}`) or via `mongo-express`.


Stale plane cleanup policy
-------------------------
The backend maintains a small housekeeping field on plane documents named `missed_updates`. This field tracks consecutive polls where an OpenSky-sourced plane was missing from the collector's snapshot.

- New or updated plane documents get `missed_updates = 0` and a `last_seen` timestamp (derived from `ts_unix` when present).
- When the backend receives a batch snapshot it:
    - upserts incoming planes (resetting `missed_updates`),
    - deletes incoming planes that report `on_ground: true` (if they include an `icao`), and
    - increments `missed_updates` by 1 for existing OpenSky-sourced planes that were not present in the snapshot.
- Any OpenSky-sourced plane whose `missed_updates` reaches `2` is removed from the database.

Automatic archiving of drone reports
------------------------------------
Drone reports (form submissions, i.e. documents with `source: 'dronereport'` or typical drone report fields) are automatically moved from the active `planes` collection to a separate `archive` collection after 1 hour.

- The backend runs a background task every 5 minutes to archive drone reports older than 1 hour.
- Archiving is based on the `last_seen` field if present, or `created_at` for legacy reports.
- The archiving logic is robust to older reports that may not have a `source` field or `last_seen`.
- Archived reports are removed from the active `planes` collection and inserted into the `archive` collection with metadata (`archived_at`, `original_last_seen`).

Manual archiving
----------------
You can manually trigger the archiving process by POSTing to `/archive/manual`.

Querying archived reports
------------------------
- `GET /archive` returns archived drone reports, optionally filtered by location (`lat`, `lon`, `radius`).
- By default, returns the most recently archived reports.

Notes:
- Only drone reports are archived; OpenSky/ADS-B planes are not affected.
- The archiving process is automatic and requires no manual intervention for normal operation.

If you have legacy drone reports that are not being archived, ensure they have either a `created_at` or `last_seen` field and at least one of the typical drone report fields (`drone_description`, `notes`, etc.).

Security note
-------------
`mongo-express` and the published Mongo port are enabled here only for local development convenience. Do not expose these services to public networks and avoid using these simple credentials in production.

***

If you'd like I can add a short `DroneRadarBackend/.env.example` documenting environment variables used by the component compose; the repository already contains a basic `.env.example` in `DroneRadarBackend/`.

Image storage (GridFS)
----------------------
The backend now includes a small image store backed by MongoDB GridFS and exposes two endpoints to interact with images:

- `POST /images` — multipart file upload (field name `file`). The endpoint stores the uploaded binary in GridFS and returns a JSON object with an `image_id` (string). Optionally include an `icao` form field to associate metadata.
- `GET /images/{image_id}` — streams the stored image back with the original content-type.

How images are used
--------------------
- Producers (the Form app) upload photos to `POST /images` and receive an `image_id` in response. The Form then includes that `image_id` in the report JSON posted to `POST /planes/bulk`. The plane documents thus reference images by id (the `image_id` field).
- Images are stored in the same MongoDB instance (GridFS stores binary chunks in `fs.chunks` and file metadata in `fs.files`) and therefore persist to the same `mongo-data` Docker volume used by the database.

Examples
--------
Upload an image with curl (multipart):

```bash
curl -F "file=@./photo.jpg" http://localhost:8000/images
```

Download an image by id (streamed):

```bash
curl http://localhost:8000/images/<image_id> -o photo.jpg
```

Notes & caveats
---------------
- Storing images in GridFS keeps binary blobs out of the `planes` collection and avoids bloating plane documents. The planes maintenance functions operate only on the `planes` collection, so they will not be slowed by images unless the DB instance overall experiences heavy I/O due to large numbers of image writes/reads.
- Images are not automatically deleted when a plane document is removed. If you want images removed when their referencing plane is deleted, I can implement cascade deletion or a periodic cleanup job to remove orphaned images.
- The `/images/{image_id}` endpoint is unauthenticated in this development setup. For production you should add access controls or serve images from a secure object store.