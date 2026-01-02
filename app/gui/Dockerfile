FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package and install
COPY shared /app/shared
RUN pip install -e /app/shared

# Install Python dependencies
COPY app/gui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY app/gui/ .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
