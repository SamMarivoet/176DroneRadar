176DroneRadar backend

Run locally:

```bash
docker-compose up --build
```

The backend will then be available on http://localhost:8000
Key endpoints:

POST /planes/bulk — accepts list of plane objects (JSON) and upserts them.

GET /planes — query planes, supports lat+lon+radius (metres) or bbox.

GET /planes/{icao24} — get single plane by ICAO24.

GET /health — health check.

---


## Backend: requirements.txt
```text
fastapi[all]==0.100.0
motor==3.1.1
pydantic==1.10.13
python-dotenv==1.0.0
uvicorn==0.22.0