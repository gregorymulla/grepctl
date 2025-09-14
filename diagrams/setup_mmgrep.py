#!/usr/bin/env python3
"""
Automated setup script for BigQuery Semantic Grep (mmgrep).
This script handles the complete setup including dataset creation,
external tables, data ingestion, and configuration.
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.bq_semgrep.config import Config, create_default_config
    from src.bq_semgrep.bigquery.connection import BigQueryClient
    from src.bq_semgrep.bigquery.schema import SchemaManager
    USE_PACKAGE = True
except ImportError:
    USE_PACKAGE = False
    print("Warning: bq_semgrep package not found. Using shell commands instead.")


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def print_success(message: str):
    """Print success message in green."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def run_command(command: str, capture_output: bool = False) -> Optional[str]:
    """Run a shell command and return output if requested."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if e.stderr:
            print_error(f"Error: {e.stderr}")
        return None


class MMGrepSetup:
    """Main setup class for BigQuery Semantic Grep."""

    def __init__(self, project_id: str, dataset_name: str = "mmgrep",
                 location: str = "US", gcs_bucket: str = "gcm-data-lake",
                 gcs_prefix: str = "multimodal-dataset"):
        self.project_id = project_id
        self.dataset_name = dataset_name
        self.location = location
        self.gcs_bucket = gcs_bucket
        self.gcs_prefix = gcs_prefix
        self.connection_name = "bigquery-gcs"

    def check_prerequisites(self) -> bool:
        """Check if all required tools are installed."""
        print_info("Checking prerequisites...")

        required_tools = ["gcloud", "bq", "gsutil"]
        missing_tools = []

        for tool in required_tools:
            result = run_command(f"which {tool}", capture_output=True)
            if not result:
                missing_tools.append(tool)

        if missing_tools:
            print_error(f"Missing required tools: {', '.join(missing_tools)}")
            print_info("Please install Google Cloud SDK: https://cloud.google.com/sdk/install")
            return False

        print_success("All prerequisites are installed")
        return True

    def setup_authentication(self) -> bool:
        """Setup Google Cloud authentication."""
        print_info("Setting up Google Cloud authentication...")

        # Set project
        run_command(f"gcloud config set project {self.project_id}")

        # Set quota project
        run_command(f"gcloud auth application-default set-quota-project {self.project_id}")

        # Verify authentication
        user = run_command(
            "gcloud auth list --filter=status:ACTIVE --format='value(account)'",
            capture_output=True
        )

        if not user:
            print_error("No active Google Cloud account found")
            print_info("Please run: gcloud auth login")
            return False

        print_success(f"Authenticated as: {user.strip()}")
        print_success(f"Project set to: {self.project_id}")
        return True

    def create_dataset(self) -> bool:
        """Create BigQuery dataset."""
        print_info(f"Creating BigQuery dataset: {self.dataset_name}...")

        # Check if dataset exists
        datasets = run_command(
            f"bq ls -d --project_id={self.project_id}",
            capture_output=True
        )

        if datasets and self.dataset_name in datasets:
            print_warning(f"Dataset {self.dataset_name} already exists")
            return True

        # Create dataset
        result = run_command(
            f"bq mk --dataset --location={self.location} "
            f"--project_id={self.project_id} {self.dataset_name}"
        )

        if result is not None:
            print_success(f"Dataset {self.dataset_name} created")
            return True
        return False

    def create_core_tables(self) -> bool:
        """Create core BigQuery tables."""
        print_info("Creating core tables...")

        tables = ["documents", "document_chunks", "search_corpus"]

        for table in tables:
            query = f"""
            CREATE OR REPLACE TABLE `{self.project_id}.{self.dataset_name}.{table}` (
                doc_id STRING NOT NULL,
                uri STRING NOT NULL,
                modality STRING NOT NULL,
                source STRING NOT NULL,
                created_at TIMESTAMP NOT NULL,
                author STRING,
                channel STRING,
                text_content STRING,
                mime_type STRING,
                meta JSON,
                chunk_index INT64,
                chunk_start INT64,
                chunk_end INT64,
                embedding ARRAY<FLOAT64>
            )
            PARTITION BY DATE(created_at)
            CLUSTER BY modality, source
            """

            run_command(f'bq query --use_legacy_sql=false --project_id={self.project_id} "{query}"')

        print_success("Core tables created")
        return True

    def create_gcs_connection(self) -> bool:
        """Create BigQuery connection for GCS."""
        print_info("Creating BigQuery connection for GCS...")

        # Check if connection exists
        existing = run_command(
            f"bq show --connection --location={self.location} "
            f"--project_id={self.project_id} {self.connection_name}",
            capture_output=True
        )

        if existing:
            print_warning(f"Connection {self.connection_name} already exists")
        else:
            # Create connection
            run_command(
                f"bq mk --connection --location={self.location} "
                f"--project_id={self.project_id} --connection_type=CLOUD_RESOURCE "
                f"{self.connection_name}"
            )
            print_success(f"Connection {self.connection_name} created")

        # Get service account
        connection_info = run_command(
            f"bq show --connection --location={self.location} "
            f"--project_id={self.project_id} {self.connection_name}",
            capture_output=True
        )

        if connection_info:
            # Extract service account
            for line in connection_info.split('\n'):
                if 'serviceAccountId' in line:
                    service_account = line.split('"')[3]
                    print_info(f"Granting GCS access to: {service_account}")
                    run_command(
                        f"gsutil iam ch serviceAccount:{service_account}:objectViewer "
                        f"gs://{self.gcs_bucket}"
                    )
                    print_success("GCS access granted")
                    break

        return True

    def create_external_tables(self) -> bool:
        """Create external tables for GCS data."""
        print_info("Creating external tables...")

        modalities = ["text", "pdf", "images", "audio", "video", "json", "csv", "markdown", "documents"]

        for modality in modalities:
            print_info(f"Creating external table for {modality}...")

            query = f"""
            CREATE OR REPLACE EXTERNAL TABLE `{self.project_id}.{self.dataset_name}.obj_{modality}`
            WITH CONNECTION `{self.project_id}.{self.location}.{self.connection_name}`
            OPTIONS (
                object_metadata = 'SIMPLE',
                uris = ['gs://{self.gcs_bucket}/{self.gcs_prefix}/{modality}/*']
            )
            """

            run_command(f'bq query --use_legacy_sql=false --project_id={self.project_id} "{query}"')

        print_success("All external tables created")
        return True

    def ingest_simple_data(self) -> bool:
        """Ingest text and markdown files."""
        print_info("Ingesting text and markdown files...")

        # Ingest text files
        text_query = f"""
        INSERT INTO `{self.project_id}.{self.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'file' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            NULL AS author,
            NULL AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            NULL AS chunk_index,
            NULL AS chunk_start,
            NULL AS chunk_end,
            NULL AS embedding
        FROM `{self.project_id}.{self.dataset_name}.obj_text`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{self.project_id}.{self.dataset_name}.documents`
            WHERE modality = 'text'
        )
        """

        run_command(f'bq query --use_legacy_sql=false --project_id={self.project_id} "{text_query}"')

        # Ingest markdown files
        markdown_query = f"""
        INSERT INTO `{self.project_id}.{self.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'markdown' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            NULL AS author,
            NULL AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            NULL AS chunk_index,
            NULL AS chunk_start,
            NULL AS chunk_end,
            NULL AS embedding
        FROM `{self.project_id}.{self.dataset_name}.obj_markdown`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{self.project_id}.{self.dataset_name}.documents`
            WHERE source = 'markdown'
        )
        """

        run_command(f'bq query --use_legacy_sql=false --project_id={self.project_id} "{markdown_query}"')

        print_success("Simple data ingested")
        return True

    def create_search_corpus(self) -> bool:
        """Create search corpus from documents."""
        print_info("Creating search corpus...")

        query = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.dataset_name}.search_corpus`
        PARTITION BY DATE(created_at)
        CLUSTER BY modality, source AS
        SELECT
            doc_id,
            uri,
            modality,
            source,
            created_at,
            author,
            channel,
            text_content,
            mime_type,
            meta,
            chunk_index,
            chunk_start,
            chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{self.project_id}.{self.dataset_name}.documents`
        WHERE text_content IS NOT NULL
        """

        run_command(f'bq query --use_legacy_sql=false --project_id={self.project_id} "{query}"')

        print_success("Search corpus created")
        return True

    def create_config_file(self) -> bool:
        """Create configuration file for bq-semgrep."""
        print_info("Creating configuration file...")

        config_dir = Path.home() / ".bq-semgrep"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_content = f"""# BigQuery Semantic Grep Configuration
project_id: "{self.project_id}"
dataset_name: "{self.dataset_name}"
location: "{self.location}"

# GCS settings
gcs_bucket: "{self.gcs_bucket}"
gcs_prefix: "{self.gcs_prefix}"
gcs_connection: "projects/{self.project_id}/locations/{self.location}/connections/{self.connection_name}"

# Model configurations - will be auto-generated
text_model: ""
embedding_model: ""

# Chunking parameters
chunk_size: 1000
chunk_overlap: 200
max_chunk_size: 1200

# Search parameters
default_top_k: 20
search_multiplier: 5
max_search_count: 200
rerank_threshold: 50

# Vector index parameters
index_type: "IVF"
distance_type: "COSINE"
ivf_min_train_size: 10000

# Processing parameters
batch_size: 100
max_workers: 4
timeout_seconds: 300

# Logging
log_level: "INFO"
"""

        config_file = config_dir / "config.yaml"
        config_file.write_text(config_content)

        print_success(f"Configuration file created at: {config_file}")
        return True

    def verify_setup(self) -> bool:
        """Verify the setup was successful."""
        print_info("Verifying setup...")

        # Check dataset
        datasets = run_command(
            f"bq ls -d --project_id={self.project_id}",
            capture_output=True
        )
        if datasets and self.dataset_name in datasets:
            print_success(f"✓ Dataset exists: {self.dataset_name}")
        else:
            print_error(f"✗ Dataset not found: {self.dataset_name}")
            return False

        # Check tables
        tables = run_command(
            f"bq ls {self.project_id}:{self.dataset_name}",
            capture_output=True
        )
        if tables:
            table_count = tables.count("TABLE")
            external_count = tables.count("EXTERNAL")
            print_success(f"✓ Tables created: {table_count} regular, {external_count} external")

        # Check document count
        doc_count = run_command(
            f'bq query --use_legacy_sql=false --format=csv --project_id={self.project_id} '
            f'"SELECT COUNT(*) FROM `{self.project_id}.{self.dataset_name}.documents`"',
            capture_output=True
        )
        if doc_count:
            count = doc_count.strip().split('\n')[-1]
            print_success(f"✓ Documents ingested: {count}")

        # Check search corpus
        corpus_count = run_command(
            f'bq query --use_legacy_sql=false --format=csv --project_id={self.project_id} '
            f'"SELECT COUNT(*) FROM `{self.project_id}.{self.dataset_name}.search_corpus`"',
            capture_output=True
        )
        if corpus_count:
            count = corpus_count.strip().split('\n')[-1]
            print_success(f"✓ Search corpus size: {count}")

        return True

    def run_setup(self) -> bool:
        """Run the complete setup process."""
        print(f"{Colors.BLUE}{'=' * 70}")
        print("BigQuery Semantic Grep (mmgrep) - Automated Setup")
        print(f"{'=' * 70}{Colors.NC}\n")

        steps = [
            ("Checking prerequisites", self.check_prerequisites),
            ("Setting up authentication", self.setup_authentication),
            ("Creating dataset", self.create_dataset),
            ("Creating core tables", self.create_core_tables),
            ("Creating GCS connection", self.create_gcs_connection),
            ("Creating external tables", self.create_external_tables),
            ("Ingesting simple data", self.ingest_simple_data),
            ("Creating search corpus", self.create_search_corpus),
            ("Creating configuration file", self.create_config_file),
            ("Verifying setup", self.verify_setup),
        ]

        for step_name, step_func in steps:
            print(f"\n{Colors.BLUE}Step:{Colors.NC} {step_name}")
            if not step_func():
                print_error(f"Setup failed at: {step_name}")
                return False
            time.sleep(1)  # Small delay between steps

        self.display_next_steps()
        return True

    def display_next_steps(self):
        """Display next steps after successful setup."""
        print(f"\n{Colors.GREEN}{'=' * 70}")
        print("Setup Complete! BigQuery Semantic Grep (mmgrep) is ready to use.")
        print(f"{'=' * 70}{Colors.NC}\n")

        print("Summary:")
        print(f"  • Project: {self.project_id}")
        print(f"  • Dataset: {self.dataset_name}")
        print(f"  • Location: {self.location}")
        print(f"  • GCS Bucket: gs://{self.gcs_bucket}/{self.gcs_prefix}")

        print("\nNext Steps:\n")
        print("1. Generate embeddings for semantic search:")
        print(f"   {Colors.BLUE}uv run bq-semgrep index --update{Colors.NC}\n")

        print("2. Build vector index:")
        print(f"   {Colors.BLUE}uv run bq-semgrep index --rebuild{Colors.NC}\n")

        print("3. Test semantic search:")
        print(f'   {Colors.BLUE}uv run bq-semgrep search "your search query"{Colors.NC}\n')

        print("4. Check system status:")
        print(f"   {Colors.BLUE}uv run bq-semgrep status{Colors.NC}\n")

        print("5. For more data ingestion (PDFs, images, etc.):")
        print(f"   {Colors.BLUE}uv run bq-semgrep ingest --bucket {self.gcs_bucket} -m pdf -m images{Colors.NC}\n")

        print("For SQL access, use:")
        print(f"   {Colors.BLUE}SELECT * FROM `{self.project_id}.{self.dataset_name}.search_corpus` LIMIT 10{Colors.NC}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated setup for BigQuery Semantic Grep (mmgrep)"
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", "semgrep-472018"),
        help="Google Cloud project ID"
    )
    parser.add_argument(
        "--dataset",
        default="mmgrep",
        help="BigQuery dataset name"
    )
    parser.add_argument(
        "--bucket",
        default="gcm-data-lake",
        help="GCS bucket name"
    )
    parser.add_argument(
        "--location",
        default="US",
        help="BigQuery location"
    )
    parser.add_argument(
        "--prefix",
        default="multimodal-dataset",
        help="GCS prefix for data"
    )

    args = parser.parse_args()

    setup = MMGrepSetup(
        project_id=args.project,
        dataset_name=args.dataset,
        location=args.location,
        gcs_bucket=args.bucket,
        gcs_prefix=args.prefix
    )

    try:
        success = setup.run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_warning("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()