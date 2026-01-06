# Matching Service Backend Architecture

The matching service supports two interchangeable backends for job offer matching, configurable via environment variable.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              POST /api/match                        │
│         (title_embedding, cv_embedding, top_k)      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  MATCHING_METHOD env  │
         │   "sqlite" | "bigquery"│
         └───────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────┐          ┌──────────────────┐
│   SQLite     │          │    BigQuery      │
│   Backend    │          │  Vector Search   │
│              │          │                  │
│ Local DB     │          │ Cloud-based      │
│ ~10k entries │          │ 700k+ entries    │
└──────────────┘          └──────────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
         ┌──────────────────────────┐
         │      MatchResponse        │
         │  {matches: [{offer_id,   │
         │             score}]}      │
         └──────────────────────────┘
```

## Configuration

### Environment Variable

Set the `MATCHING_METHOD` in `app/matching/.env`:

```bash
# Options: "sqlite" (local database) or "bigquery" (cloud vector search)
MATCHING_METHOD=sqlite
```

**Options:**
- `sqlite` - Use local SQLite database (default, recommended for development)
- `bigquery` - Use Google Cloud BigQuery Vector Search (production, scalable)

### Switching Backends

Simply change the environment variable and restart the service:

```bash
# Switch to BigQuery
echo "MATCHING_METHOD=bigquery" >> app/matching/.env
docker compose up -d matching

# Switch back to SQLite
echo "MATCHING_METHOD=sqlite" >> app/matching/.env
docker compose up -d matching
```

No code changes or API contract modifications required!

## Backend Comparison

| Feature | SQLite | BigQuery Vector Search |
|---------|--------|------------------------|
| **Dataset Size** | ~10k entries | 700k+ entries |
| **Speed** | Fast for small datasets | Optimized for large scale |
| **Cost** | Free (local) | Pay per query (bytes processed) |
| **Scalability** | Limited by disk/memory | Cloud-scalable |
| **Setup** | Simple, no cloud credentials | Requires GCP setup |
| **Availability** | Local only | Cloud, highly available |
| **Best For** | Development, testing, small deployments | Production, large datasets |

## SQLite Backend

### How It Works

1. Loads embeddings from local SQLite database
2. Performs vector similarity search using numpy
3. Returns top-k matches with similarity scores

### Configuration

```bash
# app/matching/.env
MATCHING_METHOD=sqlite
JOB_OFFERS_DB_PATH=/app/matching/data/job_offers_gold.db
```

### Database Location

See [DATABASE_LOCATIONS.md](../../docs/DATABASE_LOCATIONS.md) for details.

### Pros
- ✅ No external dependencies
- ✅ No cloud costs
- ✅ Fast for small to medium datasets
- ✅ Easy to debug and inspect data
- ✅ Works offline

### Cons
- ❌ Limited to ~10k entries (performance degrades)
- ❌ Not suitable for production scale
- ❌ Single-node only (no horizontal scaling)

## BigQuery Vector Search Backend

### How It Works

1. Uses Google Cloud BigQuery's `VECTOR_SEARCH` function
2. Queries cloud-hosted embeddings tables
3. Performs optimized vector similarity at scale
4. Returns top-k matches with titles

### Configuration

```bash
# app/matching/.env
MATCHING_METHOD=bigquery

# GCP Configuration
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# BigQuery Tables
DATASET_ID=jobmatch_gold
MAIN_TABLE_ID=offers
TABLE_TITLE_EMBEDDINGS_ID=offers_intitule_embeddings
TABLE_DESCRIPTION_EMBEDDINGS_ID=offers_description_embeddings
```

See [GCP_CREDENTIALS.md](../../docs/GCP_CREDENTIALS.md) for credential setup.

### Optimizations

The BigQuery backend is optimized for 700k+ entries:
- **No JOIN by default** - Production queries don't join with main table (faster, cheaper)
- **Description embeddings** - Uses CV/description embeddings for better matching quality
- Uses `TABLESAMPLE` for efficient random sampling
- Parameterized queries with `UNNEST()` for detail retrieval
- Returns `ingestion_date` for partition pruning (100x cost reduction)
- See [BIGQUERY_OPTIMIZATIONS.md](BIGQUERY_OPTIMIZATIONS.md) for full details

### Two Methods Available

The BigQuery backend provides two methods:

1. **`find_nearest_embeddings()`** - Production default (RECOMMENDED)
   - No JOIN with main table
   - Faster and cheaper
   - Returns: `id`, `similarity`, `ingestion_date`
   - Use when you only need offer IDs for initial matching

2. **`find_nearest_embeddings_with_titles()`** - Optional (MORE EXPENSIVE)
   - JOINs with main table to retrieve titles
   - Slower and more costly
   - Returns: `id`, `title`, `similarity`, `ingestion_date`
   - Use only when titles are immediately needed for display

### Pros
- ✅ Handles 700k+ entries efficiently
- ✅ Cloud-scalable (no infrastructure management)
- ✅ Highly available and distributed
- ✅ Built-in vector search optimization
- ✅ Can query latest data without deploying new DB

### Cons
- ❌ Requires GCP account and credentials
- ❌ Costs money (query-based pricing)
- ❌ Network latency (cloud round trip)
- ❌ More complex setup

## API Endpoint

### Request

```http
POST /api/match HTTP/1.1
Content-Type: application/json

{
  "title_embedding": [0.1, 0.2, ...],  // 384-dim vector
  "cv_embedding": [0.3, 0.4, ...],     // 384-dim vector
  "top_k": 20                           // Number of results
}
```

### Response

**Same format for both backends:**

```json
{
  "matches": [
    {
      "offer_id": "12345",
      "score": 0.8765,
      "ingestion_date": "2024-01-15T10:30:00"
    },
    {
      "offer_id": "67890",
      "score": 0.8432,
      "ingestion_date": "2024-01-15T10:30:00"
    }
  ]
}
```

**Note**:
- `ingestion_date` is `null` for SQLite backend
- `ingestion_date` is ISO 8601 timestamp for BigQuery backend
- **CRITICAL**: Use `ingestion_date` for partitioned queries (100x cost reduction)

### Error Handling

**Invalid matching method:**
```json
HTTP 500 Internal Server Error
{
  "detail": "Invalid MATCHING_METHOD: xyz. Must be 'sqlite' or 'bigquery'"
}
```

**BigQuery search failure:**
```json
HTTP 500 Internal Server Error
{
  "detail": "BigQuery vector search failed: [error details]"
}
```

## Implementation Details

### Route Handling

The `/api/match` endpoint routes to different implementations:

```python
@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest) -> MatchResponse:
    matching_method = os.getenv("MATCHING_METHOD", "sqlite").lower()

    if matching_method == "sqlite":
        return _match_sqlite(request)
    elif matching_method == "bigquery":
        return _match_bigquery(request)
    else:
        raise HTTPException(status_code=500, detail="Invalid method")
```

### SQLite Implementation

```python
def _match_sqlite(request: MatchRequest) -> MatchResponse:
    result = match_cv(
        np.array(request.title_embedding, dtype=np.float32),
        np.array(request.cv_embedding, dtype=np.float32),
        job_offers_db,
    )
    return {"matches": [{"offer_id": r.id, "score": r.similarity}
                        for r in result[:request.top_k]]}
```

### BigQuery Implementation

```python
def _match_bigquery(request: MatchRequest) -> MatchResponse:
    service = VectorSearchService()

    # Use description embeddings (default) with NO JOIN (optimized for production)
    results = service.find_nearest_embeddings(
        query_embedding=request.cv_embedding,  # CV/description embedding
        top_k=request.top_k,
        use_title_embeddings=False  # Description embeddings (default)
    )
    return {
        "matches": [
            {
                "offer_id": r["id"],
                "score": r["similarity"],
                "ingestion_date": r.get("ingestion_date")  # For partition pruning
            }
            for r in results
        ]
    }
```

## Testing

### Test SQLite Backend

```bash
cd app/matching
export MATCHING_METHOD=sqlite
python -m pytest tests/test_api.py::test_match_endpoint_sqlite -v
```

### Test BigQuery Backend

**Note:** Requires valid GCP credentials and tables.

#### Test Vector Search Service (Direct)
```bash
cd app/matching
export MATCHING_METHOD=bigquery
# Ensure .env has valid GCP configuration
python -m pytest tests/test_vector_search.py -v
```

#### Test API Endpoint with BigQuery
```bash
cd app/matching
# Run specific BigQuery API tests
python -m pytest tests/test_api.py::test_match_endpoint_bigquery -v -s
python -m pytest tests/test_api.py::test_match_endpoint_bigquery_response_format -v -s

# Or run all BigQuery API tests
python -m pytest tests/test_api.py -k bigquery -v -s
```

**Available BigQuery API tests:**
- `test_match_endpoint_bigquery` - Basic BigQuery backend functionality
- `test_match_endpoint_bigquery_response_format` - Validates response format and ingestion_date

**Note:** These tests automatically skip if GCP credentials are not configured

### Test Invalid Method Handling

```bash
python -m pytest tests/test_api.py::test_match_endpoint_invalid_method -v
```

## Production Recommendations

### For Small to Medium Deployments (<50k offers)
- **Use SQLite backend**
- Simple, fast, cost-effective
- No cloud dependencies

### For Large Scale (100k+ offers)
- **Use BigQuery Vector Search**
- Designed for scale
- Monitor costs with query logging
- Use appropriate `top_k` values (10-50 typically)

### Hybrid Approach
- **Development/Testing:** SQLite
- **Production:** BigQuery
- Same codebase, just change environment variable

## Monitoring

All backends log to stdout:

```
INFO - Received match request using sqlite method
INFO - Using SQLite backend: /app/matching/data/job_offers_gold.db
INFO - Returning 20 SQLite match results (top 20)
```

```
INFO - Received match request using bigquery method
INFO - Using BigQuery Vector Search backend
INFO - Starting vector search - Query ID: search_20260105_143022
INFO - Query completed - Bytes processed: 2,456,789
INFO - Returning 20 BigQuery match results
```

Monitor these logs to:
- Track which backend is active
- Measure performance (query time)
- Identify errors
- Audit BigQuery costs (bytes processed)

## Migration Guide

### From SQLite to BigQuery

1. **Prepare BigQuery tables**:
   - Upload embeddings to BigQuery
   - Create vector search indexes
   - Verify table structure

2. **Update `.env`**:
   ```bash
   MATCHING_METHOD=bigquery
   GCP_PROJECT_ID=your-project
   DATASET_ID=jobmatch_gold
   # ... other GCP config
   ```

3. **Test connection**:
   ```bash
   cd app/matching
   python tests/test_bigquery_connection.py
   ```

4. **Test vector search**:
   ```bash
   python tests/test_vector_search.py
   ```

5. **Deploy**:
   ```bash
   docker compose up --build -d matching
   ```

### From BigQuery to SQLite

1. **Ensure local database exists**:
   ```bash
   ls app/matching/data/job_offers_gold.db
   ```

2. **Update `.env`**:
   ```bash
   MATCHING_METHOD=sqlite
   JOB_OFFERS_DB_PATH=/app/matching/data/job_offers_gold.db
   ```

3. **Restart service**:
   ```bash
   docker compose up -d matching
   ```

## Troubleshooting

### "Invalid MATCHING_METHOD" error
- Check `.env` file has `MATCHING_METHOD=sqlite` or `MATCHING_METHOD=bigquery`
- Ensure no typos (case-insensitive)

### BigQuery: "Missing required environment variables"
- Verify all GCP variables are set in `.env`
- Check `GCP_PROJECT_ID`, `DATASET_ID`, table IDs

### BigQuery: Authentication errors
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Ensure service account has BigQuery permissions
- See [GCP_CREDENTIALS.md](../../docs/GCP_CREDENTIALS.md)

### SQLite: Database not found
- Check `JOB_OFFERS_DB_PATH` in `.env`
- Verify file exists at specified path
- See [DATABASE_LOCATIONS.md](../../docs/DATABASE_LOCATIONS.md)

## See Also

- [DATABASE_LOCATIONS.md](../../docs/DATABASE_LOCATIONS.md) - SQLite database setup
- [GCP_CREDENTIALS.md](../../docs/GCP_CREDENTIALS.md) - Google Cloud authentication
- [BIGQUERY_OPTIMIZATIONS.md](BIGQUERY_OPTIMIZATIONS.md) - Performance optimizations
