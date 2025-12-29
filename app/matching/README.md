# Matching Module

A FastAPI service to match CV embeddings against job offer embeddings stored in a SQLite database.

## Features

- REST API using FastAPI
- Swagger UI and ReDoc for interactive API documentation
- Accepts CV title and description embeddings (lists of floats)
- Returns top matches with similarity scores
- Dockerized for easy deployment
- Supports unit testing with pytest

## Folder Structure

```bash
matching/
├── src/
│   ├── matcher/
│   │   ├── __init__.py
│   │   ├── core.py           # Main matching logic
│   │   ├── logging_config.py # logging config in api
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py     # FastAPI routes
│   │   │   └── schemas.py    # Pydantic request/response schemas
│   │   └── main.py           # FastAPI app bootstrap
├── tests/                    # Pytest test cases
├── requirements.txt          # Python dependencies
└── Dockerfile                # Docker configuration
```

## Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd matching
```

### 2. Create a Python virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### Running the API Locally

From the matching directory:
```bash
uvicorn matcher.main:app --reload
```

- The API will run at http://127.0.0.1:8000
- Interactive docs available at http://127.0.0.1:8000/docs

### API Usage Example
#### Endpoint
```
POST /matching/match
```

#### Request Body
- title_embedded: List of 384 floats
- description_embedded: List of 384 floats
- job_offers_sqlite: Path to SQLite database containing job offer embeddings

```json
{
  "title_embedded": [
    0.0123, -0.4412, 0.8734, 0.1123, -0.9981,
    "... 379 more values ...",
    0.2241
  ],
  "description_embedded": [
    -0.1023, 0.7741, -0.3341, 0.9012, -0.1123,
    "... 379 more values ...",
    -0.8834
  ],
  "job_offers_sqlite": "/data/job_offers.db"
}
```

⚠️ Both embeddings must contain exactly 384 floating-point values, as produced by Sentence Transformers (e.g. all-MiniLM-L6-v2).

#### Response Body
```json
{
  "result": [
    {
      "id": "offer_123",
      "similarity": 0.87
    },
    {
      "id": "offer_456",
      "similarity": 0.74
    }
  ]
}
```

- similarity is a cosine similarity score
- Results are ordered by decreasing similarity

## Docker Usage
### 1. Build the image

From the root directory (mandatory because of ```shared/``` dependance)
```bash
docker build -t matching -f app/matching/Dockerfile .
```

### 2. Run the container
```bash
docker run -p 8000:8000 matching
```

- The API will be available at http://localhost:8000
- Logs are printed to stdout (Docker-friendly)

### Testing

Run unit tests with pytest:
```bash
pytest -v -s
```

- -s ensures logging is displayed
- Tests are located in the tests/ directory

### Logging
- Uses Python's built-in logging module
- Logs are printed to stdout, suitable for Docker
- Request/response and key events are logged

### Notes
- Ensure your SQLite database path is accessible to the API (relative or absolute)
- Input embeddings must be lists of floats (List[float])
