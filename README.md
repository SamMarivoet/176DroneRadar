This repository contains a small multi-component demo app for collecting, storing and visualizing ADS-B / drone reports.

High level layout
-----------------
- `DroneRadarBackend/` - FastAPI backend, MongoDB integration and ingest helpers. The backend exposes ingestion endpoints (POST `/planes/bulk`) and query endpoints (GET `/planes/{icao}`).
- `AirplaneFeed/` - OpenSky collector and legacy uploader pipeline. The collector now posts directly to the backend. The legacy `uploader/` component has been archived.
- `Map_GUI/` - Simple web UI (frontend + a small Flask backend) for visualizing the data.
- `Form/` - Small Flask app to submit manual drone reports (dronereport form).

Top-level orchestration
-----------------------
Use the top-level `docker-compose.yml` to bring up the full stack for local development. That compose starts the backend, the collector, the Map GUI, the Form, MongoDB and development conveniences (mongo-express and a mongo-client helper).

Quick start (development)
-------------------------
1. Build and start everything:

```powershell
docker compose up --build -d
```

2. Check services:

```powershell
docker compose ps
```

3. Open the services in your browser:
	- Backend API: http://localhost:8000
	- Map GUI: http://localhost:8080
	- Form: http://localhost:5000
	- Mongo Express (dev UI): http://localhost:8081

Notes and developer tips
------------------------
- Idk if component level docker-compose will still work, has not been tested and I'm not planning on doing it xx
- The top-level compose is meant for local development and convenience; individual components also include component-level compose files for per-component testing.
- The collector is configured to poll OpenSky and POST batches to the backend ingestion endpoint by default. The legacy Redis-based uploader has been archived and removed from the top-level compose.
- If you need to run only a single component for development (for example the Map GUI or Form), use that component's Dockerfile or component-level compose files.
- If ports conflict on your machine, edit the port mappings in `docker-compose.yml` or run services individually.

Stale plane cleanup policy
--------------------------
The backend now maintains a small housekeeping field on plane documents named `missed_updates` (integer). This field is used to automatically remove stale aircraft from the database in the default collector-driven workflow:

- New or updated plane documents get `missed_updates = 0` and a `last_seen` timestamp.
- When the backend receives a batch snapshot from the collector it:
	- upserts incoming planes (resetting `missed_updates`),
	- deletes any incoming plane that reports `on_ground: true` (if it has an `icao`), and
	- increments `missed_updates` by 1 for existing OpenSky-sourced planes that were not present in the current snapshot.
- Any OpenSky-sourced plane whose `missed_updates` reaches 2 (i.e., missed two consecutive snapshots) is deleted.

Notes and alternatives
----------------------
- The field is created automatically when the system runs (no explicit migration needed). A missing `missed_updates` field will be incremented by MongoDB and become 1 on the next update.
- This consecutive-miss policy is simple and works well for a single collector. If you run multiple independent collectors that post partial snapshots, consider switching to a time-based TTL policy (delete if `last_seen` is older than N seconds) or run a periodic cleanup job — I can implement that change if you prefer.