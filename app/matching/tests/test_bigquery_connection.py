"""
Test suite to verify BigQuery database connectivity and table existence.

This test suite checks:
1. GCP credentials are properly configured
2. BigQuery client can be initialized
3. Dataset exists in the project
4. All required tables exist in the dataset
"""

import os
import unittest
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound


class TestBigQueryConnection(unittest.TestCase):
    """Test suite for BigQuery database connectivity."""

    @classmethod
    def setUpClass(cls):
        """Load environment variables and initialize BigQuery client."""
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Get configuration from environment
        cls.project_id = os.getenv("GCP_PROJECT_ID")
        cls.dataset_id = os.getenv("DATASET_ID")
        cls.main_table_id = os.getenv("MAIN_TABLE_ID")
        cls.title_embeddings_table_id = os.getenv("TABLE_TITLE_EMBEDDINGS_ID")
        cls.description_embeddings_table_id = os.getenv("TABLE_DESCRIPTION_EMBEDDINGS_ID")

        # Initialize BigQuery client (uses GOOGLE_APPLICATION_CREDENTIALS env var)
        try:
            cls.client = bigquery.Client(project=cls.project_id)
            cls.client_initialized = True
        except Exception as e:
            cls.client = None
            cls.client_initialized = False
            cls.client_error = str(e)

    def test_env_variables_set(self):
        """Test that all required environment variables are set."""
        self.assertIsNotNone(self.project_id, "GCP_PROJECT_ID not set")
        self.assertIsNotNone(self.dataset_id, "DATASET_ID not set")
        self.assertIsNotNone(self.main_table_id, "MAIN_TABLE_ID not set")
        self.assertIsNotNone(self.title_embeddings_table_id, "TABLE_TITLE_EMBEDDINGS_ID not set")
        self.assertIsNotNone(self.description_embeddings_table_id, "TABLE_DESCRIPTION_EMBEDDINGS_ID not set")

        print(f"✓ GCP_PROJECT_ID: {self.project_id}")
        print(f"✓ DATASET_ID: {self.dataset_id}")
        print(f"✓ MAIN_TABLE_ID: {self.main_table_id}")
        print(f"✓ TABLE_TITLE_EMBEDDINGS_ID: {self.title_embeddings_table_id}")
        print(f"✓ TABLE_DESCRIPTION_EMBEDDINGS_ID: {self.description_embeddings_table_id}")

    def test_bigquery_client_initialized(self):
        """Test that BigQuery client was successfully initialized."""
        if not self.client_initialized:
            self.fail(f"Failed to initialize BigQuery client: {self.client_error}")

        self.assertIsNotNone(self.client, "BigQuery client is None")
        print(f"✓ BigQuery client initialized for project: {self.project_id}")

    def test_dataset_exists(self):
        """Test that the dataset exists in BigQuery."""
        if not self.client_initialized:
            self.skipTest("BigQuery client not initialized")

        dataset_ref = f"{self.project_id}.{self.dataset_id}"

        try:
            dataset = self.client.get_dataset(dataset_ref)
            self.assertIsNotNone(dataset)
            print(f"✓ Dataset exists: {dataset_ref}")
            print(f"  - Location: {dataset.location}")
            print(f"  - Created: {dataset.created}")
        except NotFound:
            self.fail(f"Dataset not found: {dataset_ref}")
        except Exception as e:
            self.fail(f"Error checking dataset: {e}")

    def test_main_table_exists(self):
        """Test that the main offers table exists."""
        if not self.client_initialized:
            self.skipTest("BigQuery client not initialized")

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.main_table_id}"

        try:
            table = self.client.get_table(table_ref)
            self.assertIsNotNone(table)
            print(f"✓ Main table exists: {table_ref}")
            print(f"  - Rows: {table.num_rows:,}")
            print(f"  - Size: {table.num_bytes / (1024**2):.2f} MB")
            print(f"  - Schema fields: {len(table.schema)}")
        except NotFound:
            self.fail(f"Table not found: {table_ref}")
        except Exception as e:
            self.fail(f"Error checking table: {e}")

    def test_title_embeddings_table_exists(self):
        """Test that the title embeddings table exists."""
        if not self.client_initialized:
            self.skipTest("BigQuery client not initialized")

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.title_embeddings_table_id}"

        try:
            table = self.client.get_table(table_ref)
            self.assertIsNotNone(table)
            print(f"✓ Title embeddings table exists: {table_ref}")
            print(f"  - Rows: {table.num_rows:,}")
            print(f"  - Size: {table.num_bytes / (1024**2):.2f} MB")
        except NotFound:
            self.fail(f"Table not found: {table_ref}")
        except Exception as e:
            self.fail(f"Error checking table: {e}")

    def test_description_embeddings_table_exists(self):
        """Test that the description embeddings table exists."""
        if not self.client_initialized:
            self.skipTest("BigQuery client not initialized")

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.description_embeddings_table_id}"

        try:
            table = self.client.get_table(table_ref)
            self.assertIsNotNone(table)
            print(f"✓ Description embeddings table exists: {table_ref}")
            print(f"  - Rows: {table.num_rows:,}")
            print(f"  - Size: {table.num_bytes / (1024**2):.2f} MB")
        except NotFound:
            self.fail(f"Table not found: {table_ref}")
        except Exception as e:
            self.fail(f"Error checking table: {e}")

    def test_query_sample_data(self):
        """Test that we can query a sample of data from the main table."""
        if not self.client_initialized:
            self.skipTest("BigQuery client not initialized")

        query = f"""
        SELECT COUNT(*) as total_rows
        FROM `{self.project_id}.{self.dataset_id}.{self.main_table_id}`
        LIMIT 1
        """

        try:
            query_job = self.client.query(query)
            results = list(query_job.result())

            self.assertEqual(len(results), 1, "Expected 1 row from COUNT query")
            total_rows = results[0].total_rows
            self.assertGreater(total_rows, 0, "Expected at least 1 row in the table")

            print("✓ Successfully queried main table")
            print(f"  - Total rows in table: {total_rows:,}")
        except Exception as e:
            self.fail(f"Error querying table: {e}")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
