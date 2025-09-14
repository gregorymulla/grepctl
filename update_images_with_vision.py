#!/usr/bin/env python3
"""
Update image documents in BigQuery with Vision API analysis.
"""

import json
import time
from typing import Dict, List, Any
from google.cloud import vision
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
vision_client = vision.ImageAnnotatorClient()
bq_client = bigquery.Client(project="semgrep-472018")

def analyze_image(image_uri: str) -> Dict[str, Any]:
    """Analyze a single image using Vision API."""
    try:
        image = vision.Image()
        image.source.image_uri = image_uri

        # Detect labels
        labels_response = vision_client.label_detection(image=image)
        labels = labels_response.label_annotations

        # Detect objects
        objects_response = vision_client.object_localization(image=image)
        objects = objects_response.localized_object_annotations

        # Detect text
        text_response = vision_client.text_detection(image=image)
        texts = text_response.text_annotations

        # Detect dominant colors
        props_response = vision_client.image_properties(image=image)
        colors = props_response.image_properties_annotation.dominant_colors.colors

        # Build comprehensive description
        description_parts = []

        # Add file info
        filename = image_uri.split('/')[-1]
        description_parts.append(f"Image File: {filename}")
        description_parts.append(f"Location: {image_uri}")

        # Add detected labels
        if labels:
            label_list = [f"{label.description}" for label in labels[:10]]
            description_parts.append(f"Visual Content: {', '.join(label_list)}")

            # Add confidence scores for top labels
            top_labels = [f"{label.description} ({label.score:.2%})" for label in labels[:5]]
            description_parts.append(f"Top Labels: {', '.join(top_labels)}")

        # Add detected objects
        if objects:
            object_list = [f"{obj.name} ({obj.score:.2%})" for obj in objects[:5]]
            description_parts.append(f"Detected Objects: {', '.join(object_list)}")

        # Add detected text if any
        if texts:
            text_content = texts[0].description.replace('\n', ' ')[:200]
            description_parts.append(f"Detected Text: {text_content}")

        # Add dominant colors
        if colors:
            color_descriptions = []
            for color in colors[:3]:
                rgb = f"RGB({int(color.color.red)},{int(color.color.green)},{int(color.color.blue)})"
                color_descriptions.append(rgb)
            description_parts.append(f"Dominant Colors: {', '.join(color_descriptions)}")

        # Add analysis metadata
        description_parts.append("Analysis: Vision API content extraction complete")

        return {
            'uri': image_uri,
            'text_content': '\n'.join(description_parts),
            'success': True
        }

    except Exception as e:
        logger.error(f"Error analyzing {image_uri}: {e}")
        return {
            'uri': image_uri,
            'text_content': None,
            'success': False,
            'error': str(e)
        }

def get_image_uris() -> List[str]:
    """Get all image URIs from BigQuery."""
    query = """
    SELECT DISTINCT uri
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality = 'image'
    ORDER BY uri
    """

    results = bq_client.query(query).result()
    return [row.uri for row in results]

def update_image_in_bigquery(uri: str, text_content: str):
    """Update image document in BigQuery with Vision API analysis."""
    query = """
    UPDATE `semgrep-472018.mmgrep.search_corpus`
    SET text_content = @text_content
    WHERE uri = @uri
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("uri", "STRING", uri),
            bigquery.ScalarQueryParameter("text_content", "STRING", text_content),
        ]
    )

    job = bq_client.query(query, job_config=job_config)
    job.result()

    # Also update in documents table
    query_docs = """
    UPDATE `semgrep-472018.mmgrep.documents`
    SET text_content = @text_content
    WHERE uri = @uri
    """

    job_docs = bq_client.query(query_docs, job_config=job_config)
    job_docs.result()

def process_batch(image_uris: List[str], batch_num: int, total_batches: int):
    """Process a batch of images."""
    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(image_uris)} images)")

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_image, uri): uri for uri in image_uris}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if result['success']:
                logger.info(f"✓ Analyzed: {result['uri'].split('/')[-1]}")
            else:
                logger.error(f"✗ Failed: {result['uri'].split('/')[-1]}")

    return results

def main():
    """Main function to update all images with Vision API analysis."""
    logger.info("Starting Vision API analysis for images...")

    # Get all image URIs
    image_uris = get_image_uris()
    logger.info(f"Found {len(image_uris)} images to analyze")

    # Process in batches to avoid rate limits
    batch_size = 10
    batches = [image_uris[i:i + batch_size] for i in range(0, len(image_uris), batch_size)]

    all_results = []
    for i, batch in enumerate(batches, 1):
        batch_results = process_batch(batch, i, len(batches))
        all_results.extend(batch_results)

        # Update BigQuery with results
        for result in batch_results:
            if result['success']:
                try:
                    update_image_in_bigquery(result['uri'], result['text_content'])
                    logger.info(f"Updated BigQuery for: {result['uri'].split('/')[-1]}")
                except Exception as e:
                    logger.error(f"Failed to update BigQuery for {result['uri']}: {e}")

        # Rate limiting
        if i < len(batches):
            logger.info("Waiting 2 seconds before next batch...")
            time.sleep(2)

    # Summary
    successful = sum(1 for r in all_results if r['success'])
    failed = len(all_results) - successful

    logger.info(f"\n{'='*60}")
    logger.info(f"Vision API Analysis Complete!")
    logger.info(f"Successfully analyzed: {successful}/{len(all_results)} images")
    if failed > 0:
        logger.warning(f"Failed: {failed} images")

    # Now update embeddings
    logger.info("\nNow run: uv run bq-semgrep index --update")
    logger.info("This will regenerate embeddings with the new vision-extracted content")

if __name__ == "__main__":
    main()