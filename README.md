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
- The top-level compose is meant for local development and convenience; individual components also include component-level compose files for per-component testing.
- The collector is configured to poll OpenSky and POST batches to the backend ingestion endpoint by default. The legacy Redis-based uploader has been archived and removed from the top-level compose.
- If you need to run only a single component for development (for example the Map GUI or Form), use that component's Dockerfile or component-level compose files.
- If ports conflict on your machine, edit the port mappings in `docker-compose.yml` or run services individually.

Want changes?
--------------
If you prefer the frontend served separately (nginx) or want the collector to use a queue again (Redis), I can update the compose and Dockerfiles accordingly.