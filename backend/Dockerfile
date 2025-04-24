FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including poppler for PDF processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run with Uvicorn in development mode
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]