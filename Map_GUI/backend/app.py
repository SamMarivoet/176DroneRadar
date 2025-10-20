import os
import json
import time
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, abort


DATA_DIR = Path(os.environ.get('ADSB_DATA_DIR', '/data'))
# optional: allow filepath override


app = Flask(__name__, static_folder='frontend', static_url_path='')




def list_json_files():
	"""Return list of json filenames sorted by modification time (newest first)"""
	if not DATA_DIR.exists():
		return []
	files = [f for f in DATA_DIR.glob('*.json') if f.is_file()]
	files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
	return files




@app.route('/')
def index():
	return send_from_directory(app.static_folder, 'index.html')




@app.route('/api/files')
def api_files():
	files = list_json_files()
	resp = [
		{
			'filename': f.name,
			'mtime': int(f.stat().st_mtime),
			'size': f.stat().st_size
		}
		for f in files
	]
	return jsonify(resp)




@app.route('/api/aircraft/latest')
def api_latest():
	"""Return parsed latest JSON for each unique icao (one message each)"""
	files = list_json_files()
	seen = set()
	output = []
	for f in files:
		try:
			with open(f, 'r') as fh:
				data = json.load(fh)
		except Exception:
			continue
		icao = data.get('icao') or data.get('icao24')
		if not icao:
			continue
		if icao in seen:
			continue
		seen.add(icao)
		output.append(data)
	return jsonify(output)




@app.route('/api/file/<path:filename>')
def api_file(filename):
	fpath = DATA_DIR / filename
	if not fpath.exists():
		abort(404)
	try:
		return jsonify(json.load(open(fpath)))
	except Exception:
		abort(500)




@app.route('/api/reports')
def get_reports():
    reports = []
    for file in os.listdir(DATA_DIR):
        if file.endswith('.json'):
            with open(os.path.join(DATA_DIR, file)) as f:
                reports.append(json.load(f))
    return jsonify(reports)




# static assets (index.html + app.js) are served by Flask's static handling above


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080, debug=True)
