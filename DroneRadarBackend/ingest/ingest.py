"""
Simple ingestion CLI: reads .json files from a folder and POSTs them to the backend `/planes/bulk` endpoint.

Behavior:
- Reads all files matching a glob pattern (default: `*.json`) from `INPUT_DIR`.
- Each file may contain a single JSON object or an array of objects. The script POSTs either a one-item array or the array as-is.
- On success the file can optionally be deleted (use `--delete-on-success`).
- Environment variables are loaded from a `.env` file if present: `API_URL` and `INPUT_DIR`.

Usage examples:

  # run with defaults (API_URL=http://localhost:8000, INPUT_DIR=./input_json)
  python ingest.py

  # override with flags
  python ingest.py --api-url http://backend:8000 --input-dir /input_json --delete-on-success

Note: this is intentionally minimal. For production ingestion consider
- streaming directly to MongoDB or a message queue,
- adding retries/backoff, concurrency, and error handling,
- authentication headers if your API is protected.
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Generator, Tuple, Any

import requests
import time
from dotenv import load_dotenv


load_dotenv()

DEFAULT_API_URL = os.environ.get('API_URL', 'http://localhost:8000')
DEFAULT_INPUT_DIR = os.environ.get('INPUT_DIR', './input_json')


logger = logging.getLogger('ingest')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def find_json_files(folder: Path, pattern: str = '*.json') -> Generator[Path, None, None]:
    if not folder.exists():
        logger.warning('Input folder %s does not exist', folder)
        return
    for p in folder.glob(pattern):
        if p.is_file():
            yield p


def load_json_file(path: Path) -> Any:
    # Use 'utf-8-sig' to gracefully handle files that include a UTF-8 BOM
    text = path.read_text(encoding='utf-8-sig')
    return json.loads(text)


def post_payload(api_url: str, payload: Any, timeout: int = 10) -> requests.Response:
    url = api_url.rstrip('/') + '/planes/bulk'
    headers = {'Content-Type': 'application/json'}
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def wait_for_backend(api_url: str, timeout: float = 1.0, attempts: int = 30) -> bool:
    """Poll the backend /health endpoint until it responds or attempts are exhausted.

    Returns True if backend became healthy, False otherwise.
    """
    url = api_url.rstrip('/') + '/health'
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=timeout)
            if r.ok:
                logger.debug('Backend healthy at %s (attempt %d)', url, i + 1)
                return True
        except requests.RequestException:
            logger.debug('Backend not ready yet (%s) attempt %d/%d', url, i + 1, attempts)
        time.sleep(1)
    return False


def process_files(api_url: str, input_dir: str, pattern: str = '*.json', delete_on_success: bool = False) -> None:
    folder = Path(input_dir)
    files = list(find_json_files(folder, pattern=pattern))
    if not files:
        logger.info('No files found in %s matching %s', folder, pattern)
        return

    success_count = 0
    fail_count = 0

    for f in files:
        logger.info('Processing %s', f)
        try:
            data = load_json_file(f)
        except Exception as e:
            logger.error('Failed to parse %s: %s', f, e)
            fail_count += 1
            continue

        # Ensure payload is an array of plane objects
        if isinstance(data, dict):
            payload = [data]
        elif isinstance(data, list):
            payload = data
        else:
            logger.error('Unsupported JSON top-level type in %s: %s', f, type(data))
            fail_count += 1
            continue

        try:
            r = post_payload(api_url, payload)
        except requests.RequestException as e:
            logger.error('Request to %s failed for %s: %s', api_url, f.name, e)
            fail_count += 1
            continue

        if r.ok:
            logger.info('Uploaded %s -> %s (%s)', f.name, r.url, r.status_code)
            success_count += 1
            if delete_on_success:
                try:
                    f.unlink()
                    logger.info('Deleted %s after success', f)
                except Exception as e:
                    logger.warning('Failed to delete %s: %s', f, e)
        else:
            logger.error('Server returned %s for %s: %s', r.status_code, f.name, r.text)
            fail_count += 1

    logger.info('Done. success=%d fail=%d total=%d', success_count, fail_count, len(files))


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Ingest JSON plane files to backend')
    p.add_argument('--api-url', default=DEFAULT_API_URL, help='Base URL of the backend API (default from env/API_URL)')
    p.add_argument('--input-dir', default=DEFAULT_INPUT_DIR, help='Folder containing .json files')
    p.add_argument('--pattern', default='*.json', help='Glob pattern for files in input-dir')
    p.add_argument('--delete-on-success', action='store_true', help='Delete JSON file after successful POST')
    p.add_argument('--verbose', action='store_true', help='Enable debug logging')
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_argparser()
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    process_files(args.api_url, args.input_dir, pattern=args.pattern, delete_on_success=args.delete_on_success)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
