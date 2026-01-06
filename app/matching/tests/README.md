# Vector Search Tests

This directory contains tests for the BigQuery Vector Search implementation.

## Cost-Aware Testing

Tests are organized into two categories to minimize BigQuery costs:

### Default Tests (Low Cost)
Run by default when executing `pytest`:
- `test_exact_match_is_top_result` - Single query to verify search accuracy
- `test_config_loading` - No queries, just configuration validation
- `TestEnvironmentVariables` - No queries, environment validation

**Cost**: ~1 BigQuery query

### Expensive Tests (Multiple Queries)
Marked with `@pytest.mark.expensive`, skipped by default:
- `test_embedding_with_noise` - 1 query
- `test_different_noise_levels` - 4 queries (tests with varying noise levels)
- `test_return_format` - 1 query
- `test_top_k_parameter` - 4 queries (tests k=1,3,5,10)
- `test_with_titles_backward_compatibility` - 1 query (tests JOIN method)

**Cost**: ~11 BigQuery queries

## Running Tests

### Quick Test (Default)
```bash
cd app/matching
python -m pytest tests/test_vector_search.py -v -s
```

### Run Only Expensive Tests
```bash
python -m pytest tests/test_vector_search.py -m expensive -v -s
```

### Run All Tests (Default + Expensive)
```bash
python -m pytest tests/test_vector_search.py -m "" -v -s
```

### Run Specific Test
```bash
python -m pytest tests/test_vector_search.py::TestVectorSearch::test_exact_match_is_top_result -v -s
```

## Test Configuration

The `pytest.ini` file in the parent directory configures:
- Default behavior: skip expensive tests (`-m "not expensive"`)
- Custom marker: `@pytest.mark.expensive` for costly tests

## Test Requirements

### Environment Variables
All tests require these environment variables (configured in `.env`):
- `GCP_PROJECT_ID` - Google Cloud project ID
- `DATASET_ID` - BigQuery dataset name
- `MAIN_TABLE_ID` - Main offers table name
- `TABLE_TITLE_EMBEDDINGS_ID` - Title embeddings table name
- `TABLE_DESCRIPTION_EMBEDDINGS_ID` - Description embeddings table name
- `BQ_EMBEDDING_COLUMN` - Embedding column name (default: `description_embedded`)
- `BQ_ID_COLUMN` - ID column name (default: `id`)
- `BQ_TITLE_COLUMN` - Title column name (default: `title`)
- `BQ_INGESTION_DATE_COLUMN` - Ingestion date column name (default: `ingestion_date`)

### GCP Credentials
Tests require valid GCP credentials with BigQuery access:
- Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- See [../../docs/GCP_CREDENTIALS.md](../../docs/GCP_CREDENTIALS.md) for setup

## Cost Optimization

The tests use several optimizations to minimize BigQuery costs:

1. **TABLESAMPLE** - Sample ~1000 rows instead of 700k for random selection
2. **Description embeddings** - Use default table for production behavior
3. **No JOIN by default** - Tests use `find_nearest_embeddings()` (no JOIN)
4. **Minimal queries** - Default suite runs only essential tests

## Test Strategy

### Default Test (`test_exact_match_is_top_result`)
- **Purpose**: Verify that vector search returns the exact match as top result
- **Method**: Fetch 1 random embedding, search for it, verify it's returned as #1
- **Queries**: 1 (TABLESAMPLE) + 1 (vector search) = 2 total
- **Cost**: Minimal - samples ~1k rows + searches description embeddings

### Expensive Tests
Run only when explicitly requested to avoid unnecessary costs:
- **Noise robustness**: Verify search works with slightly modified embeddings
- **Parameter validation**: Test different top_k values
- **Format validation**: Ensure response structure is correct
- **Backward compatibility**: Verify JOIN method still works

## Monitoring Costs

All tests log query statistics:
```
Query completed - Bytes processed: 2,456,789
Query duration: 0:00:01.234567
```

Monitor these logs to track actual costs incurred during testing.

## See Also

- [BIGQUERY_OPTIMIZATIONS.md](../docs/BIGQUERY_OPTIMIZATIONS.md) - Full optimization details
- [MATCHING_BACKENDS.md](../docs/MATCHING_BACKENDS.md) - Backend architecture
- [../../docs/GCP_CREDENTIALS.md](../../docs/GCP_CREDENTIALS.md) - Credential setup
