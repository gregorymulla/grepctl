import logging
from grepctl.config import Config
from grepctl.bigquery.connection import BigQueryClient
from grepctl.ingestion.base import IngestionPipeline

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = Config()
config.gcs_bucket = "gcm-data-lake"
client = BigQueryClient(config)

pipeline = IngestionPipeline(client, config)

# Test with minimal options
stats = pipeline.run(
    modalities=['images'],
    batch_size=10,
    generate_embeddings=False
)

print(f"Stats: {stats}")
