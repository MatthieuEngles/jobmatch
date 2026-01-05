# Job Offers Database Locations

## Required Database Files

### 1. Matching Service - Gold Database
**Location:** `app/matching/data/job_offers_gold.db`

Contains pre-computed embeddings for semantic matching.

```
app/matching/
└── data/
    └── job_offers_gold.db
```

### 2. GUI Service - Silver Database
**Location:** `app/gui/temp_BQ/Silver/offers.db`

Contains raw job offer details (titles, descriptions, company info).

```
app/gui/
└── temp_BQ/
    └── Silver/
        └── offers.db
```

## Quick Setup

```bash
# Create directories
mkdir -p app/matching/data
mkdir -p app/gui/temp_BQ/Silver

# Place your database files
cp /path/to/job_offers_gold.db app/matching/data/
cp /path/to/offers.db app/gui/temp_BQ/Silver/

# Restart services
docker compose up -d matching gui
```

## Notes

- **Gold DB**: Used by matching service for similarity search (embeddings only)
- **Silver DB**: Used by GUI to display offer details (full data)
- GUI database is mounted as volume - changes persist outside container
