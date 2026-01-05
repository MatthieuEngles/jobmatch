# Google Cloud Credentials Setup for Docker

Quick guide on using GCP service account credentials in containerized services.

## Method 1: Mount Credentials File (Recommended for Development)

### Setup

1. **Place credentials outside the repo** (security best practice):
   ```bash
   mkdir -p ~/.gcp
   cp jobmatch-credentials-service-account.json ~/.gcp/
   ```

2. **Add to docker-compose.yml**:
   ```yaml
   services:
     your-service:
       volumes:
         - ~/.gcp/jobmatch-credentials-service-account.json:/app/credentials.json:ro
       environment:
         - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
   ```

3. **Add to .gitignore**:
   ```
   *credentials*.json
   *.json
   !package.json
   ```

### Example for GUI Service

```yaml
gui:
  volumes:
    - ./app/gui/temp_BQ:/app/temp_BQ
    - ~/.gcp/jobmatch-credentials-service-account.json:/app/gcp-credentials.json:ro
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
    - GCP_PROJECT_ID=your-project-id
```

## Method 2: Environment Variable (Base64 Encoded)

For CI/CD or when file mounting isn't available:

1. **Encode credentials**:
   ```bash
   base64 -w 0 jobmatch-credentials-service-account.json > credentials.b64
   ```

2. **Add to .env** (don't commit this file):
   ```bash
   GCP_CREDENTIALS_BASE64=<paste base64 string>
   ```

3. **Decode in entrypoint.sh**:
   ```bash
   if [ -n "$GCP_CREDENTIALS_BASE64" ]; then
     echo "$GCP_CREDENTIALS_BASE64" | base64 -d > /tmp/gcp-credentials.json
     export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json
   fi
   ```

## Method 3: Copy to Image (Not Recommended)

**Only for private registries or internal use:**

```dockerfile
COPY gcp-credentials.json /app/credentials.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

⚠️ **Warning**: Credentials are baked into the image. Don't push to public registries!

## Using in Python Code

Once `GOOGLE_APPLICATION_CREDENTIALS` is set, the Google Cloud client libraries automatically use it:

```python
from google.cloud import bigquery

# No explicit credentials needed - uses GOOGLE_APPLICATION_CREDENTIALS
client = bigquery.Client()
query = "SELECT * FROM dataset.table LIMIT 10"
results = client.query(query)
```

## Security Best Practices

✅ **Do:**
- Mount credentials as read-only (`:ro`)
- Store credentials outside the repo
- Add `*credentials*.json` to `.gitignore`
- Use separate service accounts per environment

❌ **Don't:**
- Commit credentials to git
- Hardcode credentials in code
- Use the same service account for dev/prod
- Give excessive permissions to service accounts

## Verify Setup

```bash
# Inside container
docker compose exec gui bash -c 'echo $GOOGLE_APPLICATION_CREDENTIALS'
docker compose exec gui cat /app/gcp-credentials.json | head -5
```

## Environment Variables Summary

| Variable | Purpose | Example |
|----------|---------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to JSON credentials file | `/app/credentials.json` |
| `GCP_PROJECT_ID` | Your GCP project ID | `job-match-v0` |
| `BIGQUERY_GOLD_DATASET` | BigQuery dataset name | `gold` |
