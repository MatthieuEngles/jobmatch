"""
Test script to verify that GCP credentials are properly loaded.

This test suite checks:
1. GOOGLE_APPLICATION_CREDENTIALS environment variable is set
2. The credentials file exists and is readable
3. The credentials file contains valid JSON
4. The credentials file has the required service account fields
"""

import json
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv


class TestCredentialsConfiguration(unittest.TestCase):
    """Test suite for GCP credentials configuration."""

    @classmethod
    def setUpClass(cls):
        """Load environment variables before running tests."""
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        cls.env_path = env_path

    def test_env_file_exists(self):
        """Test that .env file exists in the matching module."""
        self.assertTrue(self.env_path.exists(), f".env file not found at {self.env_path}")
        print(f"✓ .env file found at {self.env_path}")

    def test_google_application_credentials_set(self):
        """Test that GOOGLE_APPLICATION_CREDENTIALS is set."""
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.assertIsNotNone(creds_path, "GOOGLE_APPLICATION_CREDENTIALS not set in environment")
        print(f"✓ GOOGLE_APPLICATION_CREDENTIALS is set: {creds_path}")

    def test_credentials_path_configured(self):
        """Test that the credentials path is properly configured."""
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.assertIsNotNone(creds_path, "GOOGLE_APPLICATION_CREDENTIALS not set")

        path = Path(creds_path)
        print(f"✓ Credentials path configured: {creds_path}")

        # If running in Docker or if file exists locally, verify it
        if path.exists():
            self.assertTrue(path.is_file(), f"{creds_path} is not a file")
            print("✓ Credentials file exists and is readable")
        else:
            print(f"⚠ Credentials file not found at {creds_path} (expected in Docker environment)")

    def test_credentials_file_valid_json(self):
        """Test that the credentials file contains valid JSON (if file exists)."""
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            self.skipTest("GOOGLE_APPLICATION_CREDENTIALS not set")

        path = Path(creds_path)
        if not path.exists():
            self.skipTest("Credentials file not present in test environment")

        try:
            with open(path) as f:
                creds = json.load(f)
            print("✓ Credentials file is valid JSON")
            self._validate_credentials_fields(creds)
        except json.JSONDecodeError as e:
            self.fail(f"Credentials file is not valid JSON: {e}")

    def _validate_credentials_fields(self, creds):
        """Validate that credentials have required service account fields."""
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]

        for field in required_fields:
            self.assertIn(field, creds, f"Required field '{field}' not found in credentials")

        self.assertEqual(creds["type"], "service_account", f"Expected type 'service_account', got '{creds['type']}'")

        print("✓ Credentials have all required service account fields")
        print(f"  - Project ID: {creds.get('project_id')}")
        print(f"  - Client Email: {creds.get('client_email')}")

    def test_port_env_variable(self):
        """Test that PORT environment variable is set."""
        port = os.getenv("PORT")
        self.assertIsNotNone(port, "PORT environment variable not set")
        print(f"✓ PORT: {port}")

    def test_db_path_env_variable(self):
        """Test that JOB_OFFERS_DB_PATH environment variable is set."""
        db_path = os.getenv("JOB_OFFERS_DB_PATH")
        self.assertIsNotNone(db_path, "JOB_OFFERS_DB_PATH environment variable not set")
        print(f"✓ JOB_OFFERS_DB_PATH: {db_path}")

    def test_gcp_project_id_env_variable(self):
        """Test that GCP_PROJECT_ID environment variable is set."""
        project_id = os.getenv("GCP_PROJECT_ID")
        self.assertIsNotNone(project_id, "GCP_PROJECT_ID environment variable not set")
        print(f"✓ GCP_PROJECT_ID: {project_id}")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
