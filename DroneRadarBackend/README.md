# 176DroneRadar — backend

Run locally:

```bash
docker compose -f ./DroneRadarBackend/docker-compose.yml up --build -d
```

The backend will then be available on http://localhost:8000

## Key endpoints

- `POST /planes/bulk` — accepts a list of plane objects (JSON) and upserts them.
- `GET /planes` — query planes; supports `lat` + `lon` + `radius` (metres) or `bbox`.
- `GET /planes/{icao24}` — get single plane by ICAO24.
- `GET /health` — health check.

---

## Backend: requirements

```text
fastapi[all]==0.100.0
motor==3.1.1
pydantic==1.10.13
python-dotenv==1.0.0
uvicorn==0.22.0
```

## Viewing the database (mongo-express)

For development the compose file includes a lightweight web UI (`mongo-express`) so you can browse the MongoDB instance in your browser.

1. Start the stack (from the repository root):

```powershell
docker compose -f .\DroneRadarBackend\docker-compose.yml up --build -d
```

2. Open the web UI in your browser:

```
http://localhost:8081
```

3. Login (HTTP basic auth)

- Default mongo-express UI credentials (unless changed): `admin` / `pass`.
- The MongoDB root credentials used by the stack (DB user) are: `root` / `example`.

If you prefer the web UI to use the same credentials as the Mongo root user, add these environment variables to the `mongo-express` service in `DroneRadarBackend/docker-compose.yml` and restart the service:

- `ME_CONFIG_BASICAUTH_USERNAME=root`
- `ME_CONFIG_BASICAUTH_PASSWORD=example`

4. Connection details (for external tools)

- MongoDB URI (used by the backend): `mongodb://root:example@mongo:27017/?authSource=admin`
- To connect from host tools (Compass, mongosh) use the published host port: `mongodb://root:example@localhost:27017/?authSource=admin`

### Quick mongosh one-liners

```powershell
# show a sample document
mongosh "mongodb://root:example@localhost:27017/planesdb?authSource=admin" --eval "db.planes.findOne()"

# list indexes
mongosh "mongodb://root:example@localhost:27017/planesdb?authSource=admin" --eval "printjson(db.planes.getIndexes())"
```

Security note

`mongo-express` and the published Mongo port are enabled here only for local development convenience. Do not expose these services to public networks and avoid using these simple credentials in production.