"""
Image processing and description generation for semantic search.
"""

import logging
from typing import Dict, List, Optional
from ..config import Config
from ..bigquery.connection import BigQueryClient

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Process images and generate searchable descriptions."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize image processor."""
        self.client = client
        self.config = config

    def create_image_descriptions_table(self) -> None:
        """Create a table to store image descriptions."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.image_descriptions` (
            image_id STRING,
            uri STRING,
            description STRING,
            tags ARRAY<STRING>,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        try:
            job = self.client.execute_query(query)
            job.result()
            logger.info("Image descriptions table created/verified")
        except Exception as e:
            logger.error(f"Failed to create image descriptions table: {e}")

    def add_sample_descriptions(self) -> None:
        """Add sample descriptions for demo images."""
        # Sample descriptions for demonstration
        # In production, these would come from Vision API or manual annotation
        descriptions = [
            ("image_001.jpg", "A beautiful red bird perched on a tree branch with green leaves in the background. The bird has vibrant red plumage and appears to be a cardinal.", ["bird", "cardinal", "red", "nature", "wildlife", "tree"]),
            ("image_002.jpg", "A golden retriever dog playing in a park, running through green grass with a tennis ball in its mouth.", ["dog", "golden retriever", "pet", "park", "playing", "tennis ball"]),
            ("image_003.jpg", "A serene mountain landscape at sunset with snow-capped peaks and a lake reflecting the orange sky.", ["mountain", "landscape", "sunset", "lake", "nature", "scenic"]),
            ("image_004.jpg", "A blue jay bird sitting on a fence post, showing its distinctive blue and white feathers.", ["bird", "blue jay", "blue", "wildlife", "fence"]),
            ("image_005.jpg", "A close-up of a hummingbird hovering near red flowers, wings in motion creating a blur effect.", ["bird", "hummingbird", "flowers", "nature", "wildlife", "red flowers"]),
            ("image_006.jpg", "A cat sleeping on a windowsill in warm sunlight, curled up in a ball.", ["cat", "pet", "sleeping", "window", "sunlight", "cozy"]),
            ("image_007.jpg", "An eagle soaring through cloudy skies with wings spread wide.", ["bird", "eagle", "flying", "sky", "clouds", "wildlife", "majestic"]),
            ("image_008.jpg", "A colorful parrot with green, red, and blue feathers sitting on a tropical branch.", ["bird", "parrot", "colorful", "tropical", "wildlife", "exotic"]),
            ("image_009.jpg", "A city skyline at night with illuminated buildings reflecting in the water.", ["city", "skyline", "night", "lights", "urban", "reflection"]),
            ("image_010.jpg", "A robin bird with orange breast standing on grass looking for worms.", ["bird", "robin", "orange", "grass", "wildlife", "nature"]),
        ]

        # Generate more sample descriptions for remaining images
        for i in range(11, 101):
            if i % 10 in [1, 4, 5, 7, 8, 0]:  # 60% chance of bird-related content
                bird_types = ["sparrow", "finch", "owl", "hawk", "dove", "crow", "swan", "duck", "pelican", "flamingo"]
                bird_type = bird_types[(i // 10) % len(bird_types)]
                descriptions.append(
                    (f"image_{i:03d}.jpg",
                     f"A {bird_type} bird in its natural habitat, showcasing distinctive features and behaviors typical of the species.",
                     ["bird", bird_type, "wildlife", "nature", "animal"])
                )
            else:
                # Non-bird content
                subjects = [
                    ("A beautiful sunset over the ocean with waves crashing on the shore.", ["sunset", "ocean", "beach", "waves", "nature"]),
                    ("A forest path winding through tall pine trees with dappled sunlight.", ["forest", "path", "trees", "nature", "hiking"]),
                    ("A field of wildflowers in bloom with various colors under blue sky.", ["flowers", "field", "nature", "colorful", "spring"]),
                    ("Modern architecture building with glass facade reflecting clouds.", ["architecture", "building", "modern", "glass", "urban"]),
                ]
                subject = subjects[(i // 10) % len(subjects)]
                descriptions.append((f"image_{i:03d}.jpg", subject[0], subject[1]))

        # Insert descriptions into BigQuery
        self._insert_descriptions(descriptions)

    def _insert_descriptions(self, descriptions: List[tuple]) -> None:
        """Insert image descriptions into BigQuery."""
        values = []
        for filename, desc, tags in descriptions:
            uri = f"gs://gcm-data-lake/multimodal-dataset/images/{filename}"
            tags_str = "[" + ", ".join([f'"{tag}"' for tag in tags]) + "]"
            values.append(f"('{filename}', '{uri}', '{desc}', {tags_str})")

        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.image_descriptions`
        (image_id, uri, description, tags)
        VALUES {', '.join(values)}
        """

        try:
            job = self.client.execute_query(query)
            job.result()
            logger.info(f"Inserted {len(descriptions)} image descriptions")
        except Exception as e:
            logger.error(f"Failed to insert descriptions: {e}")

    def ingest_images_with_descriptions(self) -> int:
        """Ingest images with their descriptions into the documents table."""
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            COALESCE(d.uri, i.uri) AS uri,
            'image' AS modality,
            'image' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            COALESCE(
                CONCAT(
                    'Image: ', REGEXP_EXTRACT(i.uri, r'/([^/]+)$'), '\\n\\n',
                    'Description: ', d.description, '\\n\\n',
                    'Tags: ', ARRAY_TO_STRING(d.tags, ', '), '\\n',
                    'Format: ', UPPER(REGEXP_EXTRACT(i.uri, r'\\.([^.]+)$')), '\\n',
                    'Size: ', CAST(i.size AS STRING), ' bytes'
                ),
                CONCAT(
                    'Image File: ', REGEXP_EXTRACT(i.uri, r'/([^/]+)$'), '\\n',
                    'Format: ', UPPER(REGEXP_EXTRACT(i.uri, r'\\.([^.]+)$')), '\\n',
                    'Size: ', CAST(i.size AS STRING), ' bytes\\n',
                    'Type: Stock photo or general image'
                )
            ) AS text_content,
            i.content_type AS mime_type,
            TO_JSON(STRUCT(
                i.size,
                i.updated AS last_modified,
                i.generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_images` i
        LEFT JOIN `{self.config.project_id}.{self.config.dataset_name}.image_descriptions` d
        ON i.uri = d.uri
        WHERE i.uri NOT IN (
            SELECT DISTINCT uri FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            WHERE modality = 'image'
        )
        """

        try:
            job = self.client.execute_query(query)
            job.result(timeout=300)
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Ingested {num_rows} images with descriptions")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to ingest images: {e}")
            return 0

    def update_search_corpus(self) -> int:
        """Update search corpus with image documents."""
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
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
            embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        WHERE modality = 'image'
        AND doc_id NOT IN (
            SELECT doc_id FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            WHERE modality = 'image'
        )
        """

        try:
            job = self.client.execute_query(query)
            job.result(timeout=300)
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Added {num_rows} images to search corpus")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to update search corpus: {e}")
            return 0