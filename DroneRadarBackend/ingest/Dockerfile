FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# copy the ingest script
COPY ingest.py ./ingest.py
# default entry (can be overridden by docker-compose command)
CMD ["python", "ingest.py"]