FROM python:3.11-slim

WORKDIR /app

# Copy backend-specific files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app.py .

# Copy frontend (for serving static files)
COPY frontend ./frontend

EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app", "--workers", "2", "--threads", "4"]
