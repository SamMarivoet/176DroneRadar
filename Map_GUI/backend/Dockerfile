FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency list and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app
COPY backend/app.py .

# Copy frontend for static serving
COPY frontend ./frontend

# Expose Flask/Gunicorn port
EXPOSE 8080

# Start app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app", "--workers=2", "--threads=4"]
