FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ogn_collector.py .

CMD ["python", "ogn_collector.py"]