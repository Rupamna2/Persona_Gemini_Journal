FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend source code
COPY backend/ /app/backend/

# Expose default Cloud Run port
EXPOSE 8080

# Launch FastAPI backend with uvicorn
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
