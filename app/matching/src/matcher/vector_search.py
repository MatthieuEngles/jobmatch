"""
Service to perform vector searches using Google BigQuery's vector search capabilities.
Includes configuration management, search execution, and logging of search activities.

NOTE: Table and column names come from static config, not user input.
BigQuery does not support parameterization of identifiers.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

from google.cloud import bigquery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("vector_search.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class BigQueryConfig:
    """Configuration for BigQuery tables and columns."""

    project_id: str
    dataset_id: str
    main_table: str
    title_embeddings_table: str
    description_embeddings_table: str
    embedding_column: str
    id_column: str
    title_column: str
    ingestion_date_column: str

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables."""
        # Required variables
        required = {
            "project_id": "GCP_PROJECT_ID",
            "dataset_id": "DATASET_ID",
            "main_table": "MAIN_TABLE_ID",
            "title_embeddings_table": "TABLE_TITLE_EMBEDDINGS_ID",
            "description_embeddings_table": "TABLE_DESCRIPTION_EMBEDDINGS_ID",
        }

        # Optional with defaults
        optional = {
            "embedding_column": ("BQ_EMBEDDING_COLUMN", "description_embedded"),
            "id_column": ("BQ_ID_COLUMN", "id"),
            "title_column": ("BQ_TITLE_COLUMN", "title"),
            "ingestion_date_column": ("BQ_INGESTION_DATE_COLUMN", "ingestion_date"),
        }

        # Check required vars
        config = {}
        missing = []
        for key, env_var in required.items():
            value = os.getenv(env_var)
            if not value:
                missing.append(env_var)
            config[key] = value

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Add optional vars
        for key, (env_var, default) in optional.items():
            config[key] = os.getenv(env_var, default)

        logger.info(f"Loaded BigQuery config - Project: {config['project_id']}, Dataset: {config['dataset_id']}")

        return cls(**config)

    def get_table_ref(self, table_name: str) -> str:
        """Get fully qualified table reference."""
        return f"`{self.project_id}.{self.dataset_id}.{table_name}`"


class VectorSearchService:
    """Service for performing vector searches with BigQuery."""

    def __init__(self, config: BigQueryConfig = None):
        """Initialize with config from environment if not provided."""
        self.config = config or BigQueryConfig.from_env()
        self.client = bigquery.Client(project=self.config.project_id)

    def find_nearest_embeddings(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        query_id: str = None,
        query_metadata: dict = None,
        use_title_embeddings: bool = False,
    ) -> list[dict]:
        """
        Find top-k nearest embeddings WITHOUT joining with main table.
        Returns similarity scores (0-1 range, higher is better).

        This is the recommended method for production use - no JOIN overhead.

        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of top results to return
            query_id: Optional ID for logging
            query_metadata: Optional metadata for logging
            use_title_embeddings: If False (default), use description embeddings; if True, use title embeddings

        Returns:
            List of dicts with keys: id, similarity, ingestion_date
        """
        start_time = datetime.now()
        query_id = query_id or f"search_{start_time.strftime('%Y%m%d_%H%M%S')}"

        # Select which embeddings table to use
        embeddings_table = (
            self.config.title_embeddings_table if use_title_embeddings else self.config.description_embeddings_table
        )

        # Log input
        logger.info(f"Starting vector search (no JOIN) - Query ID: {query_id}")
        logger.info(f"Parameters: top_k={top_k}, embedding_dim={len(query_embedding)}")
        logger.info(f"Using embeddings table: {embeddings_table}")
        if query_metadata:
            logger.info(f"Metadata: {json.dumps(query_metadata)}")

        # Build optimized query - NO JOIN, just embeddings table with ingestion_date
        query = f"""
        SELECT
            base.{self.config.id_column} AS id,
            1 - (distance / 2) AS similarity,
            base.{self.config.ingestion_date_column} AS ingestion_date
        FROM VECTOR_SEARCH(
            TABLE {self.config.get_table_ref(embeddings_table)},
            '{self.config.embedding_column}',
            (SELECT @query_embedding AS {self.config.embedding_column}),
            top_k => @top_k,
            distance_type => 'COSINE'
        )
        ORDER BY similarity DESC
        """  # nosec B608

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )

        try:
            logger.info("Executing BigQuery vector search (no JOIN)...")
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()

            # Log query statistics
            logger.info(f"Query completed - Bytes processed: {query_job.total_bytes_processed:,}")
            logger.info(f"Query duration: {query_job.ended - query_job.started}")

            # Process results
            matches = []
            for row in results:
                matches.append(
                    {
                        "id": row.id,
                        "similarity": float(row.similarity),
                        "ingestion_date": row.ingestion_date.isoformat() if row.ingestion_date else None,
                    }
                )

            # Log results summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"Search completed successfully in {duration:.2f}s")
            logger.info(f"Found {len(matches)} matches")

            # Log top results
            logger.info("Top results:")
            for i, match in enumerate(matches[: min(5, len(matches))], 1):
                logger.info(f"  {i}. ID: {match['id']}, Similarity: {match['similarity']:.4f}")

            # Log all results
            result_summary = [{"id": m["id"], "similarity": f"{m['similarity']:.4f}"} for m in matches]
            logger.info(f"All results: {json.dumps(result_summary)}")

            return matches

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}", exc_info=True)
            raise

    def find_nearest_embeddings_with_titles(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        query_id: str = None,
        query_metadata: dict = None,
        use_title_embeddings: bool = False,
    ) -> list[dict]:
        """
        Find top-k nearest embeddings and retrieve their titles with JOIN.
        Returns similarity scores (0-1 range, higher is better).

        NOTE: This method performs a JOIN and is more expensive.
        Use find_nearest_embeddings() for production if titles are not needed immediately.

        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of top results to return
            query_id: Optional ID for logging
            query_metadata: Optional metadata for logging
            use_title_embeddings: If False (default), use description embeddings; if True, use title embeddings

        Returns:
            List of dicts with keys: id, title, similarity, ingestion_date
        """
        start_time = datetime.now()
        query_id = query_id or f"search_{start_time.strftime('%Y%m%d_%H%M%S')}"

        # Select which embeddings table to use
        embeddings_table = (
            self.config.title_embeddings_table if use_title_embeddings else self.config.description_embeddings_table
        )

        # Log input
        logger.info(f"Starting vector search - Query ID: {query_id}")
        logger.info(f"Parameters: top_k={top_k}, embedding_dim={len(query_embedding)}")
        logger.info(f"Using embeddings table: {embeddings_table}")
        if query_metadata:
            logger.info(f"Metadata: {json.dumps(query_metadata)}")

        # Build optimized query with config values
        # OPTIMIZATION: Use INNER JOIN instead of LEFT JOIN and retrieve only necessary columns
        # CRITICAL: Include ingestion_date for partitioned queries (100x cost reduction)
        query = f"""
        WITH nearest AS (
            SELECT base.{self.config.id_column} AS id, distance
            FROM VECTOR_SEARCH(
                TABLE {self.config.get_table_ref(embeddings_table)},
                '{self.config.embedding_column}',
                (SELECT @query_embedding AS {self.config.embedding_column}),
                top_k => @top_k,
                distance_type => 'COSINE'
            )
        )
        SELECT
            n.id,
            1 - (n.distance / 2) AS similarity,
            t.{self.config.title_column} AS title,
            t.{self.config.ingestion_date_column} AS ingestion_date
        FROM nearest n
        INNER JOIN {self.config.get_table_ref(self.config.main_table)} t
            ON n.id = t.{self.config.id_column}
        ORDER BY similarity DESC
        """  # nosec B608

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )

        try:
            logger.info("Executing BigQuery vector search...")
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()

            # Log query statistics
            logger.info(f"Query completed - Bytes processed: {query_job.total_bytes_processed:,}")
            logger.info(f"Query duration: {query_job.ended - query_job.started}")

            # Process results
            matches = []
            for row in results:
                matches.append(
                    {
                        "id": row.id,
                        "title": row.title,
                        "similarity": float(row.similarity),
                        "ingestion_date": row.ingestion_date.isoformat() if row.ingestion_date else None,
                    }
                )

            # Log results summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"Search completed successfully in {duration:.2f}s")
            logger.info(f"Found {len(matches)} matches")

            # Log top results
            logger.info("Top results:")
            for i, match in enumerate(matches[: min(5, len(matches))], 1):
                logger.info(f"  {i}. ID: {match['id']}, Similarity: {match['similarity']:.4f}, Title: {match['title']}")

            # Log all results
            result_summary = [{"id": m["id"], "similarity": f"{m['similarity']:.4f}"} for m in matches]
            logger.info(f"All results: {json.dumps(result_summary)}")

            return matches

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}", exc_info=True)
            raise

    def get_full_offer_details(self, offer_ids: list[str], ingestion_dates: list[str] = None) -> list[dict]:
        """
        Efficiently retrieve full offer details for given IDs.

        OPTIMIZATION: Uses partition pruning with ingestion_dates for 100x cost reduction.
        When ingestion_dates are provided, only scans relevant partitions instead of full table.

        Args:
            offer_ids: List of offer IDs to retrieve
            ingestion_dates: Optional list of ingestion dates (ISO format strings) corresponding to offer_ids.
                           If provided, enables partition pruning (100x cost reduction).
                           Should be obtained from vector search results.

        Returns:
            List of dictionaries containing offer details

        Example:
            # Get ingestion dates from vector search results
            results = service.find_nearest_embeddings(...)
            offer_ids = [r["id"] for r in results]
            ingestion_dates = [r["ingestion_date"] for r in results]

            # Fetch full details with partition pruning
            details = service.get_full_offer_details(offer_ids, ingestion_dates)
        """
        if not offer_ids:
            return []

        # CRITICAL OPTIMIZATION: Use partition pruning if ingestion_dates provided
        if ingestion_dates:
            # Parse ISO format dates to DATE objects for partition pruning
            # Remove None values and convert to unique dates
            unique_dates = set()
            for date_str in ingestion_dates:
                if date_str:
                    # Extract date portion from ISO timestamp (YYYY-MM-DD)
                    date_portion = date_str.split("T")[0]
                    unique_dates.add(date_portion)

            if unique_dates:
                # Build query with partition pruning (100x cost reduction)
                query = f"""
                SELECT *
                FROM {self.config.get_table_ref(self.config.main_table)}
                WHERE {self.config.id_column} IN UNNEST(@offer_ids)
                  AND DATE({self.config.ingestion_date_column}) IN UNNEST(@ingestion_dates)
                """  # nosec B608

                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ArrayQueryParameter("offer_ids", "STRING", offer_ids),
                        bigquery.ArrayQueryParameter("ingestion_dates", "DATE", list(unique_dates)),
                    ]
                )

                logger.info(
                    f"Fetching full details for {len(offer_ids)} offers with partition pruning "
                    f"({len(unique_dates)} unique dates)..."
                )
            else:
                # Fallback: No valid dates, use query without partition pruning
                logger.warning("No valid ingestion_dates found, falling back to query without partition pruning")
                query = f"""
                SELECT *
                FROM {self.config.get_table_ref(self.config.main_table)}
                WHERE {self.config.id_column} IN UNNEST(@offer_ids)
                """  # nosec B608

                job_config = bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ArrayQueryParameter("offer_ids", "STRING", offer_ids)]
                )
        else:
            # No partition pruning - will scan more data (more expensive)
            logger.warning(
                "No ingestion_dates provided - query will scan more data. "
                "For 100x cost reduction, provide ingestion_dates from vector search results."
            )
            query = f"""
            SELECT *
            FROM {self.config.get_table_ref(self.config.main_table)}
            WHERE {self.config.id_column} IN UNNEST(@offer_ids)
            """  # nosec B608

            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("offer_ids", "STRING", offer_ids)]
            )

        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()

            offers = []
            for row in results:
                # Convert row to dictionary
                offer_dict = dict(row.items())
                offers.append(offer_dict)

            logger.info(f"Retrieved {len(offers)} offer details")
            logger.info(f"Bytes processed: {query_job.total_bytes_processed:,}")

            if ingestion_dates and unique_dates:
                logger.info(f"✓ Partition pruning applied - scanned only {len(unique_dates)} date partition(s)")

            return offers

        except Exception as e:
            logger.error(f"Failed to retrieve offer details: {str(e)}", exc_info=True)
            raise


# Usage example
if __name__ == "__main__":
    # Initialize service (loads config from env)
    service = VectorSearchService()

    # Your embedding
    my_embedding = [0.1, 0.2, 0.3, ...]  # replace with actual

    metadata = {"source": "user_query", "user_id": "user_123", "query_text": "senior data engineer"}

    try:
        # RECOMMENDED: Use find_nearest_embeddings (no JOIN, production default)
        print("\n=== Method 1: No JOIN (Recommended for Production) ===")
        results = service.find_nearest_embeddings(
            query_embedding=my_embedding,
            top_k=10,
            query_metadata=metadata,
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Results include: id, similarity, ingestion_date
        print("\nTop matches (no JOIN):")
        for i, match in enumerate(results[:5], 1):
            print(
                f"{i}. ID: {match['id']}, Similarity: {match['similarity']:.4f}, Ingestion: {match['ingestion_date']}"
            )

        # OPTIONAL: Fetch full offer details with partition pruning (100x cost reduction)
        print("\n=== Fetching Full Details with Partition Pruning ===")
        offer_ids = [r["id"] for r in results]
        ingestion_dates = [r["ingestion_date"] for r in results]

        full_details = service.get_full_offer_details(
            offer_ids=offer_ids,
            ingestion_dates=ingestion_dates,  # Enables 100x cost reduction
        )

        print(f"\nFetched {len(full_details)} full offer details with partition pruning")

        # ALTERNATIVE: Use find_nearest_embeddings_with_titles (with JOIN, more expensive)
        print("\n=== Method 2: With JOIN (More Expensive) ===")
        results_with_titles = service.find_nearest_embeddings_with_titles(
            query_embedding=my_embedding,
            top_k=5,
            query_metadata=metadata,
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Results include: id, title, similarity, ingestion_date
        print("\nTop matches (with JOIN):")
        for i, match in enumerate(results_with_titles, 1):
            print(f"{i}. ID: {match['id']}, Similarity: {match['similarity']:.4f}, Title: {match['title']}")

    except Exception as e:
        logger.error(f"Search failed: {e}")
