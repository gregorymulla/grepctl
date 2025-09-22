"""
Health check and service validation for grepctl.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.api_core.exceptions import PermissionDenied, GoogleAPIError
import subprocess
import json

from .config import Config
from .bigquery.connection import BigQueryClient


logger = logging.getLogger(__name__)


class HealthChecker:
    """Check system health and service availability."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize health checker."""
        self.client = client
        self.config = config
        self.raw_client = client.client
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'project_id': self.config.project_id,
            'dataset': self.config.dataset_name,
            'checks': {},
            'summary': {
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }

        # Run all checks
        checks = [
            ('apis', self.check_apis()),
            ('dataset', self.check_dataset()),
            ('tables', self.check_tables()),
            ('connection', self.check_connection()),
            ('models', self.check_models()),
            ('permissions', self.check_permissions()),
            ('data', self.check_data_status()),
        ]

        for check_name, check_result in checks:
            results['checks'][check_name] = check_result
            if check_result['status'] == 'passed':
                results['summary']['passed'] += 1
            elif check_result['status'] == 'failed':
                results['summary']['failed'] += 1
            if check_result.get('warnings'):
                results['summary']['warnings'] += len(check_result['warnings'])

        results['overall_status'] = 'healthy' if results['summary']['failed'] == 0 else 'unhealthy'

        return results

    def check_apis(self) -> Dict[str, Any]:
        """Check if required APIs are enabled."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'warnings': [],
            'instructions': []
        }

        required_apis = {
            'bigquery.googleapis.com': 'BigQuery API',
            'aiplatform.googleapis.com': 'Vertex AI API',
            'storage.googleapis.com': 'Cloud Storage API',
        }

        optional_apis = {
            'generativelanguage.googleapis.com': 'Generative Language API (for Gemini models)',
            'speech.googleapis.com': 'Speech-to-Text API (for audio transcription)',
            'videointelligence.googleapis.com': 'Video Intelligence API (for video analysis)',
            'vision.googleapis.com': 'Vision API (for image OCR)',
            'documentai.googleapis.com': 'Document AI (for PDF extraction)',
        }

        try:
            # Check enabled APIs
            cmd = ['gcloud', 'services', 'list', '--enabled',
                   '--format=json', f'--project={self.config.project_id}']
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            enabled_apis = json.loads(output)
            enabled_names = {api['config']['name'] for api in enabled_apis}

            # Check required APIs
            for api_name, api_title in required_apis.items():
                if api_name in enabled_names:
                    result['details'][api_title] = '✅ Enabled'
                else:
                    result['status'] = 'failed'
                    result['errors'].append(f"{api_title} is not enabled")
                    result['instructions'].append(
                        f"Enable {api_title}:\n"
                        f"  gcloud services enable {api_name} --project={self.config.project_id}"
                    )

            # Check optional APIs
            for api_name, api_title in optional_apis.items():
                if api_name in enabled_names:
                    result['details'][api_title] = '✅ Enabled'
                else:
                    result['warnings'].append(f"{api_title} is not enabled (optional)")
                    result['details'][api_title] = '⚠️ Not enabled (optional)'

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Failed to check APIs: {str(e)}")
            result['instructions'].append(
                "Ensure gcloud CLI is installed and authenticated:\n"
                "  gcloud auth application-default login"
            )

        return result

    def check_dataset(self) -> Dict[str, Any]:
        """Check if BigQuery dataset exists."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'instructions': []
        }

        try:
            dataset = self.raw_client.get_dataset(
                f"{self.config.project_id}.{self.config.dataset_name}"
            )
            result['details']['dataset'] = f"✅ Dataset '{self.config.dataset_name}' exists"
            result['details']['location'] = f"📍 Location: {dataset.location}"
            result['details']['created'] = f"📅 Created: {dataset.created.strftime('%Y-%m-%d %H:%M:%S')}"
        except NotFound:
            result['status'] = 'failed'
            result['errors'].append(f"Dataset '{self.config.dataset_name}' does not exist")
            result['instructions'].append(
                f"Create the dataset:\n"
                f"  grepctl setup\n"
                f"  # Or manually:\n"
                f"  bq mk --dataset --location={self.config.location} "
                f"{self.config.project_id}:{self.config.dataset_name}"
            )
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Failed to check dataset: {str(e)}")

        return result

    def check_tables(self) -> Dict[str, Any]:
        """Check if required tables exist."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'warnings': [],
            'instructions': []
        }

        required_tables = [
            'documents',
            'search_corpus',
        ]

        optional_tables = [
            'document_chunks',
            'obj_pdf',
            'obj_images',
            'obj_audio',
            'obj_video',
            'obj_text',
            'obj_markdown',
            'obj_json',
            'obj_csv',
            'obj_documents',
        ]

        try:
            # List all tables
            tables = list(self.raw_client.list_tables(
                f"{self.config.project_id}.{self.config.dataset_name}"
            ))
            table_names = {table.table_id for table in tables}

            # Check required tables
            for table_name in required_tables:
                if table_name in table_names:
                    # Get row count
                    query = f"SELECT COUNT(*) as count FROM `{self.config.project_id}.{self.config.dataset_name}.{table_name}`"
                    try:
                        count_result = self.raw_client.query(query).result()
                        count = list(count_result)[0].count
                        result['details'][table_name] = f"✅ Table exists ({count:,} rows)"
                    except:
                        result['details'][table_name] = f"✅ Table exists"
                else:
                    result['status'] = 'failed'
                    result['errors'].append(f"Required table '{table_name}' does not exist")

            # Check optional tables (external tables)
            for table_name in optional_tables:
                if table_name in table_names:
                    result['details'][table_name] = f"✅ External table configured"
                else:
                    result['warnings'].append(f"External table '{table_name}' not configured")

            if result['status'] == 'failed':
                result['instructions'].append(
                    "Run setup to create required tables:\n"
                    "  grepctl setup"
                )

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Failed to check tables: {str(e)}")

        return result

    def check_connection(self) -> Dict[str, Any]:
        """Check Vertex AI connection."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'instructions': []
        }

        try:
            # Check for Vertex AI connection
            cmd = ['bq', 'ls', '--connection', '--location=us', '--max_results=20',
                   '--project_id=' + self.config.project_id, '--format=json']
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            connections = json.loads(output) if output else []

            vertex_connection = None
            for conn in connections:
                # Check the 'name' field for vertex-ai connection
                conn_name = conn.get('name', '') if isinstance(conn, dict) else ''
                if 'vertex-ai' in conn_name.lower():
                    vertex_connection = conn
                    break

            if vertex_connection:
                full_name = vertex_connection.get('name', 'vertex-ai-connection')
                conn_name = full_name.split('/')[-1] if '/' in full_name else full_name
                service_account = vertex_connection.get('cloudResource', {}).get('serviceAccountId', 'Unknown')

                result['details']['connection'] = f"✅ Vertex AI connection exists"
                result['details']['connection_name'] = f"📝 Name: {conn_name}"
                result['details']['service_account'] = f"🔑 Service Account: {service_account}"

                # Check service account permissions
                if service_account != 'Unknown':
                    result['details']['permissions_hint'] = (
                        "Ensure service account has roles:\n"
                        "    - roles/aiplatform.user\n"
                        "    - roles/bigquery.dataEditor"
                    )
            else:
                result['status'] = 'failed'
                result['errors'].append("No Vertex AI connection found")
                result['instructions'].append(
                    "Create a Vertex AI connection:\n"
                    "  1. Go to BigQuery console\n"
                    "  2. Click on 'Add Data' → 'Connections'\n"
                    "  3. Create a new connection of type 'Vertex AI'\n"
                    "  Or use bq CLI:\n"
                    "  bq mk --connection --location=us --project_id={} \\\n"
                    "    --connection_type=CLOUD_RESOURCE vertex-ai-connection".format(self.config.project_id)
                )

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Failed to check connection: {str(e)}")

        return result

    def check_models(self) -> Dict[str, Any]:
        """Check ML models availability."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'warnings': [],
            'instructions': []
        }

        try:
            # Check embedding model
            embedding_model_name = f"{self.config.project_id}.{self.config.dataset_name}.text_embedding_model"
            try:
                # Test embedding model
                test_query = f"""
                SELECT ARRAY_LENGTH(ml_generate_embedding_result) as dim
                FROM ML.GENERATE_EMBEDDING(
                    MODEL `{embedding_model_name}`,
                    (SELECT 'test' as content)
                )
                """
                result_set = self.raw_client.query(test_query).result()
                dim = list(result_set)[0].dim
                result['details']['embedding_model'] = f"✅ Embedding model working (dim={dim})"
            except NotFound:
                result['warnings'].append("Embedding model not found")
                result['details']['embedding_model'] = "⚠️ Not configured"
                result['instructions'].append(
                    f"Create embedding model:\n"
                    f"  bq query --use_legacy_sql=false \"\n"
                    f"  CREATE OR REPLACE MODEL `{embedding_model_name}`\n"
                    f"  REMOTE WITH CONNECTION `us.vertex-ai-connection`\n"
                    f"  OPTIONS (ENDPOINT = 'text-embedding-004')\""
                )
            except Exception as e:
                result['warnings'].append(f"Embedding model error: {str(e)[:50]}")
                result['details']['embedding_model'] = "❌ Error"

            # Check text generation model availability (optional)
            # Note: Gemini models through BigQuery ML are not currently supported
            # as remote models due to BigQuery limitations
            result['details']['text_model'] = "ℹ️ ML.GENERATE_TEXT not available (BigQuery limitation)"
            result['warnings'].append("BigQuery ML.GENERATE_TEXT with Gemini not supported")
            result['instructions'].append(
                "ML.GENERATE_TEXT Status:\n"
                "  • Gemini models cannot be created as BigQuery remote models\n"
                "  • This is a known BigQuery ML limitation\n"
                "\n"
                "Alternative Solutions:\n"
                "  1. Use the working embedding model for semantic search\n"
                "  2. Use Vertex AI SDK in Python for text generation\n"
                "  3. Create Cloud Functions to bridge Vertex AI and BigQuery\n"
                "\n"
                "Note: The embedding functionality is fully operational for grepctl."
            )

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Failed to check models: {str(e)}")

        return result

    def check_permissions(self) -> Dict[str, Any]:
        """Check user permissions."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'instructions': []
        }

        try:
            # Get current user
            cmd = ['gcloud', 'config', 'get-value', 'account']
            user = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            result['details']['user'] = f"👤 Current user: {user}"

            # Test BigQuery permissions
            try:
                test_query = "SELECT 1 as test"
                self.raw_client.query(test_query).result()
                result['details']['bigquery'] = "✅ BigQuery access verified"
            except PermissionDenied:
                result['status'] = 'failed'
                result['errors'].append("Insufficient BigQuery permissions")
                result['instructions'].append(
                    f"Grant BigQuery permissions:\n"
                    f"  gcloud projects add-iam-policy-binding {self.config.project_id} \\\n"
                    f"    --member='user:{user}' \\\n"
                    f"    --role='roles/bigquery.user'"
                )

            # Check project access
            try:
                cmd = ['gcloud', 'projects', 'describe', self.config.project_id, '--format=json']
                project_info = json.loads(subprocess.check_output(cmd, stderr=subprocess.DEVNULL))
                result['details']['project'] = f"✅ Project access verified"
            except:
                result['warnings'].append("Could not verify project access")

        except Exception as e:
            result['warnings'].append(f"Permission check incomplete: {str(e)}")

        return result

    def check_data_status(self) -> Dict[str, Any]:
        """Check data ingestion and indexing status."""
        result = {
            'status': 'passed',
            'details': {},
            'errors': [],
            'warnings': [],
            'instructions': []
        }

        try:
            # Check document count
            doc_query = f"""
            SELECT
                COUNT(*) as total_docs,
                COUNT(DISTINCT modality) as modalities,
                COUNT(DISTINCT source) as sources
            FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            """
            doc_result = self.raw_client.query(doc_query).result()
            doc_stats = list(doc_result)[0]

            result['details']['documents'] = f"📄 Documents: {doc_stats.total_docs:,} total"
            result['details']['modalities'] = f"📊 Modalities: {doc_stats.modalities}"
            result['details']['sources'] = f"📁 Sources: {doc_stats.sources}"

            # Check embeddings
            embed_query = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN embedding IS NOT NULL AND ARRAY_LENGTH(embedding) > 0 THEN 1 ELSE 0 END) as with_embeddings
            FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            """
            embed_result = self.raw_client.query(embed_query).result()
            embed_stats = list(embed_result)[0]

            if embed_stats.total > 0:
                embed_pct = (embed_stats.with_embeddings / embed_stats.total) * 100
                result['details']['embeddings'] = f"🔍 Embeddings: {embed_stats.with_embeddings:,}/{embed_stats.total:,} ({embed_pct:.1f}%)"

                if embed_pct < 100:
                    result['warnings'].append(f"Only {embed_pct:.1f}% of documents have embeddings")
                    result['instructions'].append(
                        "Generate missing embeddings:\n"
                        "  grepctl index --update"
                    )
            else:
                result['warnings'].append("No documents in search corpus")
                result['instructions'].append(
                    "Ingest documents first:\n"
                    "  grepctl ingest --bucket <your-bucket>"
                )

        except Exception as e:
            result['warnings'].append(f"Could not check data status: {str(e)}")

        return result