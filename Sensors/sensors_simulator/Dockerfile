# Sensors Simulator Dockerfile
FROM python:3.11-slim

# 1) work inside /app
WORKDIR /app

# 2) copy requirements first so Docker can cache installs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) now copy the rest of the simulator code (generator, image_pool, etc.)
COPY . .

# 4) make sure the data dirs exist inside the container
RUN mkdir -p /data/out /data/image_pool

# 5) declare volumes so you can mount host dirs if you want
VOLUME ["/data/out", "/data/image_pool"]

# 6) default envs (you can still override in docker-compose)
ENV OUTPUT_DIR=/data/out
ENV IMAGE_POOL_DIR=/data/image_pool
ENV SLEEP_SECONDS=2.0
ENV NUM_DRONES=5
ENV CAMERA_PROB=0.6

# extra envs for our new upload logic
ENV BACKEND_URL=http://backend:8000
ENV WRITE_LOCAL_JSON=true
ENV CAMERA_IMAGE_PROB=0.4

# 7) run the generator
CMD ["python", "generator.py"]

