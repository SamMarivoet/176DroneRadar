import os, json, time, random, requests, redis

URL   = os.getenv("INGEST_URL")
TOKEN = os.getenv("INGEST_TOKEN","")
BATCH = int(os.getenv("BATCH_SIZE","200"))
r = redis.from_url(os.getenv("REDIS_URL","redis://redis:6379"))

def backoff(i): return min(60, 2**i) * (0.5 + random.random())

while True:
    batch = []
    for _ in range(BATCH):
        raw = r.lpop("positions")
        if not raw: break
        batch.append(json.loads(raw))
    if not batch:
        time.sleep(0.5); continue

    headers = {"Content-Type":"application/json"}
    if TOKEN: headers["Authorization"] = f"Bearer {TOKEN}"

    try:
        resp = requests.post(URL, json=batch, headers=headers, timeout=10)
        if resp.status_code in (200,201):
            print(f"[uploader] sent {len(batch)} ok", flush=True)
        elif resp.status_code == 429:
            for m in reversed(batch): r.lpush("positions", json.dumps(m))
            wait = int(resp.headers.get("Retry-After","5"))
            print(f"[uploader] 429, waiting {wait}s", flush=True)
            time.sleep(wait)
        elif 500 <= resp.status_code < 600:
            for m in reversed(batch): r.lpush("positions", json.dumps(m))
            wait = backoff(1)
            print(f"[uploader] server {resp.status_code}, retrying in {wait:.1f}s", flush=True)
            time.sleep(wait)
        else:
            print(f"[uploader] dropped batch status={resp.status_code}", flush=True)
    except requests.RequestException as e:
        for m in reversed(batch): r.lpush("positions", json.dumps(m))
        wait = backoff(1)
        print(f"[uploader] network error: {e}, backoff {wait:.1f}s", flush=True)
        time.sleep(wait)
