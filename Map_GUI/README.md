# ADSB Web GUI (Docker)


1. Clone this repo.
2. Ensure your collector writes JSON files to `./adsb-pipeline/data` (or update docker-compose volume to point to your real folder).
3. Start:
docker-compose up -d --build
4. Open http://localhost:8080


Notes:
- The backend reads JSON files from the mounted data folder (`/data`). It exposes /api/aircraft/latest and /api/files.
- If you later have a DB/uploader, you can change DATA_DIR or modify `app.py` to query the DB instead.
- The frontend is intentionally minimal: Leaflet shows markers and a list. It polls `/api/aircraft/latest` every X seconds.


Tips:
- If JSON schema varies, `app.py` tries reasonable alternate keys (icao24, lat/latitude, lon/longitude, alt_geom, etc.). Extend parsing logic if needed.
- To increase performance with many files, switch to a small DB (SQLite, Postgres) and update the uploader to write there; then adapt `app.py` to query the DB.
