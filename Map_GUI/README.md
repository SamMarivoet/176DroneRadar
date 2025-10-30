# Map GUI (Map_GUI)

This service provides a small Leaflet-based map and a lightweight backend used for local development and demos. It intentionally keeps things simple and is designed to consume the unified `planes` feed from the central backend.

## Key changes (recent)
- Unified feed: the Map GUI now reads a single unified feed of documents from the central backend. The backend normalizes incoming sources and sets a canonical `source` field on each document (`opensky` for ADS‑B telemetry, `dronereport` for form reports). The Map GUI no longer expects separate `reports` and `planes` endpoints.
- Single API: the frontend fetches `/api/planes` from the Map GUI backend. Each returned document may be a telemetry record or a report; the UI uses the `source` field to decide how to render it.
- Local poller: the Map GUI backend runs a background poller that queries the central backend (`/planes`) every `MAP_POLL_SECONDS` seconds and caches the latest snapshot locally. By default the poller writes `planefeed.json` under `ADSB_DATA_DIR` inside the container.
- Image proxy: a developer-friendly image proxy endpoint is available at `/api/images/<image_id>` which will forward requests to the central backend's image endpoint when available and fall back to a local placeholder image.

## Endpoints (Map GUI)
- `GET /` — serves the frontend (`index.html`).
- `GET /api/planes` — returns the latest snapshot the poller fetched. Response shape: `{ "planes": [ ... ] }` where each entry is the unified document stored in the central DB.
- `GET /api/images/<image_id>` — proxy for image retrieval. Developers can request images via this stable URL while building the UI. If the central backend is available the proxy streams the image; otherwise it returns a local placeholder.

Note: legacy endpoints `/api/reports` and `/api/feed` were removed when the feed was unified.

## Configuration (environment variables)
- `ADSB_DATA_DIR` (default `/data`) — path inside the container where the poller writes `planefeed.json` (ephemeral unless you mount a volume).
- `MAP_POLL_SECONDS` (default `5`) — how often (in seconds) the poller fetches the central backend.
- `BACKEND_API` (default `http://backend:8000`) — base URL of the central backend the poller queries.

You can pass these via the Docker Compose service environment for `map_gui` or set them before running the container.

## How the UI decides what to render
The Map GUI receives a mixed list of documents. Each document includes a `source` field (the ingestion pipeline ensures this). The frontend uses:
- `source === 'opensky'` → render as aircraft telemetry (plane icon, speed/altitude popup)
- `source === 'dronereport'` → render as a drone report (circle marker, description/photo popup)

If `source` is missing for older records, the frontend still has conservative fallbacks, but the ingestion logic sets `source` for new documents so relying on the canonical field is recommended.

## Development tips
- Start the full stack from repo root (top-level docker compose):
```powershell
docker-compose up -d --build
```

- Check logs for the Map GUI poller:
```powershell
docker-compose logs -f map_gui
```

- The frontend polls `/api/planes` every 5s by default. Use the image proxy URL `GET /api/images/<image_id>` in popups to show photos referenced by `image_id`.

## Ephemeral vs persistent snapshot
- Ephemeral (default): the poller stores the snapshot inside the container (no extra compose volumes required). If the container restarts the snapshot is re-populated from the DB.
- Persistent: if you want the snapshot file to survive container restarts for debugging, mount a host volume to `ADSB_DATA_DIR`. This is optional — the central DB remains the canonical store.

## Optional developer extensions
- Image proxy improvements: currently the proxy forwards to the central backend; you can replace this with a direct GridFS read from this container if desired.
- In-memory cache: if you prefer no filesystem writes at all, swap the poller to keep the snapshot in memory and serve it from a module-level variable (fast, ephemeral).

## Troubleshooting
- If no planes appear, verify the poller can contact the central backend (`BACKEND_API`) and check for errors in `map_gui` logs.
- If images are missing, try the image proxy and confirm the central backend `/images/<image_id>` endpoint is reachable.

---

If you'd like I can: (a) switch the poller to an in-memory cache, (b) add a host-volume example to the top-level compose file, or (c) replace the proxy with direct GridFS access — tell me which and I'll implement it.
