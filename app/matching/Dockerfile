FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip

# Install torch (adjust CPU/CUDA version as needed)
#RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy shared package and install with embeddings support
COPY shared /app/shared
RUN pip install -e "/app/shared[embeddings]"

# Copy matcher app and install requirements
COPY app/matching /app/matching
#RUN pip install --no-cache-dir -r /app/matching/requirements.txt
RUN pip install -r /app/matching/requirements.txt

EXPOSE $MATCHING_PORT

WORKDIR /app/matching
RUN pip install -e .

# Copy .env file
COPY app/matching/.env /app/matching/.env

CMD python -m uvicorn matcher.main:app --host 0.0.0.0 --port ${MATCHING_PORT} --reload
