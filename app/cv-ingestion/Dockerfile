# CV Ingestion Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PDF processing, image conversion, and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package first (for Docker layer caching)
COPY shared/ ./shared/

# Copy and install Python dependencies
COPY app/cv-ingestion/requirements.txt .
RUN pip install --no-cache-dir ./shared && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/cv-ingestion/src/ ./src/

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')" || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8081"]
