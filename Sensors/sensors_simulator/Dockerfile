# Sensors Simulator Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY generator.py .

RUN mkdir -p /data/out /data/images
VOLUME ["/data/out", "/data/images"]

ENV OUTPUT_DIR=/data/out
ENV IMAGE_POOL_DIR=/data/images
ENV SLEEP_SECONDS=2.0
ENV NUM_DRONES=5
ENV CAMERA_PROB=0.6

CMD ["python", "./generator.py"]


