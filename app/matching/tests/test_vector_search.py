import logging
import os
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from dotenv import load_dotenv
from google.cloud import bigquery
from matcher.vector_search import BigQueryConfig, VectorSearchService

# Configure test logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TestVectorSearch(unittest.TestCase):
    """Test suite for vector search functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used by all tests."""
        logger.info("Setting up test environment...")

        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Load config from environment
        cls.config = BigQueryConfig.from_env()
        cls.service = VectorSearchService(cls.config)
        cls.client = bigquery.Client(project=cls.config.project_id)

        # Fetch a sample embedding from the dataset for testing
        cls.sample_id, cls.sample_embedding = cls._fetch_sample_embedding()

        logger.info(f"Test setup complete. Sample ID: {cls.sample_id}")
        logger.info(f"Sample embedding dimension: {len(cls.sample_embedding)}")

    @classmethod
    def _fetch_sample_embedding(cls):
        """
        Efficiently fetch a random embedding from the dataset for 700k+ entries.

        OPTIMIZED Strategy:
        1. Use TABLESAMPLE to avoid full table scan - samples ~1000 rows
        2. Apply RAND() only on the sample, not the entire table
        3. Fetch embedding in a single query to minimize round trips
        4. Use description embeddings table (default for production)

        This is MUCH faster than ORDER BY RAND() LIMIT 1 on 700k rows.
        """
        # OPTIMIZATION: TABLESAMPLE SYSTEM samples approximately 1000 rows (0.15% of 700k)
        # Then RAND() + LIMIT only sorts those ~1000 rows, not all 700k
        # Use description embeddings table (default)
        query_get_sample = f"""
        SELECT
            {cls.config.id_column} AS id,
            {cls.config.embedding_column} AS embedding
        FROM {cls.config.get_table_ref(cls.config.description_embeddings_table)} TABLESAMPLE SYSTEM (0.15 PERCENT)
        WHERE {cls.config.embedding_column} IS NOT NULL
        ORDER BY RAND()
        LIMIT 1
        """

        logger.info("Fetching random sample using TABLESAMPLE (optimized for large tables)...")
        start_time = datetime.now()
        query_job = cls.client.query(query_get_sample)
        result = query_job.result()

        sample_id = None
        sample_embedding = None
        for row in result:
            sample_id = row.id
            sample_embedding = list(row.embedding)
            break

        if not sample_id:
            raise ValueError("No embeddings found in the dataset")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Sample fetched in {duration:.2f}s - ID: {sample_id}")
        logger.info(f"Bytes processed: {query_job.total_bytes_processed:,}")

        return sample_id, sample_embedding

    def test_exact_match_is_top_result(self):
        """Test that searching with an exact embedding returns itself as top result (no JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: Exact Match - Top Result (No JOIN)")
        logger.info("=" * 80)

        results = self.service.find_nearest_embeddings(
            query_embedding=self.sample_embedding,
            top_k=5,
            query_id=f"test_exact_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            query_metadata={"test": "exact_match"},
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Assertions
        self.assertGreater(len(results), 0, "Should return at least one result")

        top_result = results[0]
        logger.info(f"\nTop result ID: {top_result['id']}")
        logger.info(f"Expected ID: {self.sample_id}")
        logger.info(f"Similarity: {top_result['similarity']:.6f}")

        self.assertEqual(
            top_result["id"],
            self.sample_id,
            f"Top result ID should match sample ID. Got {top_result['id']}, expected {self.sample_id}",
        )

        # Similarity should be very close to 1.0 (allowing for floating point precision)
        self.assertGreater(
            top_result["similarity"],
            0.9999,
            f"Exact match should have similarity > 0.9999, got {top_result['similarity']}",
        )

        # Should NOT have 'title' field (no JOIN)
        self.assertNotIn("title", top_result, "Result should NOT have 'title' field (no JOIN)")

        logger.info("✓ Test passed: Exact embedding returned as top result (no JOIN)")

    @pytest.mark.expensive
    def test_embedding_with_noise(self):
        """Test that embedding with small noise still returns original in top 5 (no JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: Embedding with Negligible Noise (No JOIN)")
        logger.info("=" * 80)

        # Add small Gaussian noise to the embedding
        np.random.seed(42)  # For reproducibility
        noise_scale = 0.001  # Very small noise
        noise = np.random.normal(0, noise_scale, len(self.sample_embedding))
        noisy_embedding = (np.array(self.sample_embedding) + noise).tolist()

        # Calculate the L2 norm of the noise for logging
        noise_magnitude = np.linalg.norm(noise)
        logger.info(f"Noise magnitude (L2 norm): {noise_magnitude:.6f}")
        logger.info(f"Noise scale: {noise_scale}")

        results = self.service.find_nearest_embeddings(
            query_embedding=noisy_embedding,
            top_k=5,
            query_id=f"test_noise_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            query_metadata={"test": "with_noise", "noise_scale": noise_scale},
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Assertions
        self.assertGreaterEqual(len(results), 1, "Should return at least one result")

        # Check if original ID is in top 5
        result_ids = [r["id"] for r in results]
        logger.info(f"\nOriginal ID: {self.sample_id}")
        logger.info(f"Top 5 IDs: {result_ids}")

        self.assertIn(
            self.sample_id, result_ids, f"Original ID {self.sample_id} should be in top 5 results: {result_ids}"
        )

        # Find the position and similarity of the original
        original_position = result_ids.index(self.sample_id) + 1
        original_similarity = results[result_ids.index(self.sample_id)]["similarity"]

        logger.info(f"Original embedding found at position: {original_position}")
        logger.info(f"Similarity with noise: {original_similarity:.6f}")

        # With small noise, similarity should still be very high
        self.assertGreater(
            original_similarity,
            0.99,
            f"Noisy embedding should have similarity > 0.99 with original, got {original_similarity}",
        )

        # Ideally, it should still be the top result
        if original_position == 1:
            logger.info("✓ Test passed: Noisy embedding still returned original as top result (no JOIN)")
        else:
            logger.warning(
                f"⚠ Original was at position {original_position}, not #1. "
                "This might indicate other very similar embeddings exist in the dataset."
            )
            logger.info("✓ Test passed: Noisy embedding returned original in top 5 (no JOIN)")

    @pytest.mark.expensive
    def test_different_noise_levels(self):
        """Test with varying noise levels to understand behavior (no JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: Multiple Noise Levels (No JOIN)")
        logger.info("=" * 80)

        noise_levels = [0.0001, 0.001, 0.01, 0.05]
        results_summary = []

        for noise_scale in noise_levels:
            np.random.seed(42)
            noise = np.random.normal(0, noise_scale, len(self.sample_embedding))
            noisy_embedding = (np.array(self.sample_embedding) + noise).tolist()

            results = self.service.find_nearest_embeddings(
                query_embedding=noisy_embedding,
                top_k=5,
                query_id=f"test_noise_{noise_scale}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                query_metadata={"test": "noise_levels", "noise_scale": noise_scale},
                use_title_embeddings=False,  # Use description embeddings (default)
            )

            result_ids = [r["id"] for r in results]
            if self.sample_id in result_ids:
                position = result_ids.index(self.sample_id) + 1
                similarity = results[position - 1]["similarity"]
            else:
                position = None
                similarity = None

            results_summary.append({"noise_scale": noise_scale, "position": position, "similarity": similarity})

            logger.info(
                f"Noise scale {noise_scale:.4f}: "
                f"Position={position}, Similarity={similarity:.6f if similarity else 'N/A'}"
            )

        # Assert that for small noise levels, we always find the original
        for summary in results_summary[:2]:  # First two noise levels are smallest
            self.assertIsNotNone(
                summary["position"], f"Original should be found with noise scale {summary['noise_scale']}"
            )
            self.assertLessEqual(
                summary["position"], 5, f"Original should be in top 5 with noise scale {summary['noise_scale']}"
            )

        logger.info("✓ Test passed: Noise level analysis complete (no JOIN)")

    def test_config_loading(self):
        """Test that configuration is properly loaded from environment."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Configuration Loading")
        logger.info("=" * 80)

        # Check required fields are set
        self.assertIsNotNone(self.config.project_id)
        self.assertIsNotNone(self.config.dataset_id)
        self.assertIsNotNone(self.config.main_table)
        self.assertIsNotNone(self.config.title_embeddings_table)
        self.assertIsNotNone(self.config.description_embeddings_table)

        logger.info(f"Project ID: {self.config.project_id}")
        logger.info(f"Dataset ID: {self.config.dataset_id}")
        logger.info(f"Main Table: {self.config.main_table}")
        logger.info(f"Title Embeddings Table: {self.config.title_embeddings_table}")
        logger.info(f"Description Embeddings Table: {self.config.description_embeddings_table}")
        logger.info(f"Embedding Column: {self.config.embedding_column}")
        logger.info(f"ID Column: {self.config.id_column}")
        logger.info(f"Title Column: {self.config.title_column}")
        logger.info(f"Ingestion Date Column: {self.config.ingestion_date_column}")

        logger.info("✓ Test passed: Configuration loaded successfully")

    @pytest.mark.expensive
    def test_return_format(self):
        """Test that results have the expected format (no JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: Result Format Validation (No JOIN)")
        logger.info("=" * 80)

        results = self.service.find_nearest_embeddings(
            query_embedding=self.sample_embedding,
            top_k=3,
            query_id=f"test_format_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Check we got results
        self.assertGreater(len(results), 0, "Should return at least one result")
        self.assertLessEqual(len(results), 3, "Should return at most 3 results (top_k=3)")

        # Check format of each result
        for i, result in enumerate(results):
            logger.info(f"Result {i + 1}: {result}")

            # Check required keys
            self.assertIn("id", result, "Result should have 'id' key")
            self.assertIn("similarity", result, "Result should have 'similarity' key")
            self.assertIn("ingestion_date", result, "Result should have 'ingestion_date' key")

            # Should NOT have 'title' key (no JOIN)
            self.assertNotIn("title", result, "Result should NOT have 'title' key (no JOIN)")

            # Check types
            self.assertIsInstance(result["similarity"], float, "Similarity should be float")
            # ingestion_date can be string (ISO format) or None
            if result["ingestion_date"] is not None:
                self.assertIsInstance(result["ingestion_date"], str, "Ingestion date should be string (ISO format)")

            # Check similarity range
            self.assertGreaterEqual(result["similarity"], 0.0, "Similarity should be >= 0")
            self.assertLessEqual(result["similarity"], 1.0, "Similarity should be <= 1")

        # Check results are sorted by similarity (descending)
        similarities = [r["similarity"] for r in results]
        self.assertEqual(
            similarities,
            sorted(similarities, reverse=True),
            "Results should be sorted by similarity in descending order",
        )

        logger.info("✓ Test passed: Results have correct format and ordering (no JOIN)")

    @pytest.mark.expensive
    def test_top_k_parameter(self):
        """Test that top_k parameter is respected (no JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 6: Top-K Parameter (No JOIN)")
        logger.info("=" * 80)

        for k in [1, 3, 5, 10]:
            results = self.service.find_nearest_embeddings(
                query_embedding=self.sample_embedding,
                top_k=k,
                query_id=f"test_topk_{k}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                use_title_embeddings=False,  # Use description embeddings (default)
            )

            logger.info(f"top_k={k}: returned {len(results)} results")

            self.assertLessEqual(len(results), k, f"Should return at most {k} results")

        logger.info("✓ Test passed: top_k parameter respected (no JOIN)")

    @pytest.mark.expensive
    def test_with_titles_backward_compatibility(self):
        """Test that find_nearest_embeddings_with_titles still works (with JOIN)."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 7: Backward Compatibility - With Titles (WITH JOIN)")
        logger.info("=" * 80)

        results = self.service.find_nearest_embeddings_with_titles(
            query_embedding=self.sample_embedding,
            top_k=5,
            query_id=f"test_with_titles_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            query_metadata={"test": "backward_compatibility"},
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        # Assertions
        self.assertGreater(len(results), 0, "Should return at least one result")

        # Check format includes 'title' field
        for i, result in enumerate(results):
            if i == 0:
                logger.info(f"Result {i + 1}: {result}")

            # Should have all keys including 'title'
            self.assertIn("id", result, "Result should have 'id' key")
            self.assertIn("title", result, "Result should have 'title' key (WITH JOIN)")
            self.assertIn("similarity", result, "Result should have 'similarity' key")
            self.assertIn("ingestion_date", result, "Result should have 'ingestion_date' key")

            # Check types
            self.assertIsInstance(result["title"], str, "Title should be string")
            self.assertIsInstance(result["similarity"], float, "Similarity should be float")

        logger.info("✓ Test passed: find_nearest_embeddings_with_titles still works (backward compatibility)")


class TestEnvironmentVariables(unittest.TestCase):
    """Test that required environment variables are set."""

    @classmethod
    def setUpClass(cls):
        """Load environment variables before running tests."""
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

    def test_required_env_vars(self):
        """Test that all required environment variables are present."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Environment Variables")
        logger.info("=" * 80)

        required_vars = [
            "GCP_PROJECT_ID",
            "DATASET_ID",
            "MAIN_TABLE_ID",
            "TABLE_TITLE_EMBEDDINGS_ID",
            "TABLE_DESCRIPTION_EMBEDDINGS_ID",
        ]

        missing = []
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            else:
                logger.info(f"✓ {var}: {value}")

        self.assertEqual(len(missing), 0, f"Missing required environment variables: {', '.join(missing)}")

        logger.info("✓ All required environment variables are set")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
