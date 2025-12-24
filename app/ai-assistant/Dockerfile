FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY app/ai-assistant/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/ai-assistant/src/ ./src/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8084

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8084"]
