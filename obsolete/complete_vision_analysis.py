#!/usr/bin/env python3
"""
Complete Vision API analysis for remaining images.
"""

import time
from google.cloud import vision
from google.cloud import bigquery
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
vision_client = vision.ImageAnnotatorClient()
bq_client = bigquery.Client(project="semgrep-472018")

def analyze_and_update_image(image_uri: str):
    """Analyze and immediately update a single image."""
    try:
        # Analyze with Vision API
        image = vision.Image()
        image.source.image_uri = image_uri

        # Get all Vision API features
        labels_response = vision_client.label_detection(image=image, max_results=15)
        labels = labels_response.label_annotations

        objects_response = vision_client.object_localization(image=image, max_results=10)
        objects = objects_response.localized_object_annotations

        text_response = vision_client.text_detection(image=image)
        texts = text_response.text_annotations

        props_response = vision_client.image_properties(image=image)
        colors = props_response.image_properties_annotation.dominant_colors.colors

        # Build description
        description_parts = []
        filename = image_uri.split('/')[-1]
        description_parts.append(f"Image File: {filename}")
        description_parts.append(f"Location: {image_uri}")

        if labels:
            label_list = [f"{label.description}" for label in labels]
            description_parts.append(f"Visual Content: {', '.join(label_list[:10])}")
            top_labels = [f"{label.description} ({label.score:.1%})" for label in labels[:5]]
            description_parts.append(f"Top Labels: {', '.join(top_labels)}")

        if objects:
            object_list = [f"{obj.name}" for obj in objects[:5]]
            description_parts.append(f"Detected Objects: {', '.join(object_list)}")

        if texts and len(texts) > 0:
            text_content = texts[0].description.replace('\n', ' ').strip()
            if text_content:
                preview = text_content[:200] + "..." if len(text_content) > 200 else text_content
                description_parts.append(f"Detected Text: {preview}")

        if colors and len(colors) > 0:
            color_descriptions = []
            for color in colors[:3]:
                r, g, b = int(color.color.red), int(color.color.green), int(color.color.blue)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                color_descriptions.append(hex_color)
            description_parts.append(f"Dominant Colors: {', '.join(color_descriptions)}")

        # Add categories
        categories = set()
        for label in labels[:15]:
            label_lower = label.description.lower()
            if any(word in label_lower for word in ['animal', 'bird', 'dog', 'cat']):
                categories.add("Animals")
            elif any(word in label_lower for word in ['person', 'people', 'face']):
                categories.add("People")
            elif any(word in label_lower for word in ['food', 'cuisine', 'meal']):
                categories.add("Food")
            elif any(word in label_lower for word in ['building', 'architecture']):
                categories.add("Architecture")
            elif any(word in label_lower for word in ['plant', 'tree', 'flower']):
                categories.add("Nature")

        if categories:
            description_parts.append(f"Categories: {', '.join(sorted(categories))}")

        description_parts.append("Analysis: Complete Vision API content extraction")
        description_parts.append(f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

        text_content = '\n'.join(description_parts)

        # Update BigQuery immediately
        update_query = """
        UPDATE `semgrep-472018.mmgrep.search_corpus`
        SET text_content = @text_content
        WHERE uri = @uri
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("uri", "STRING", image_uri),
                bigquery.ScalarQueryParameter("text_content", "STRING", text_content),
            ]
        )

        job = bq_client.query(update_query, job_config=job_config)
        job.result()

        logger.info(f"✓ {filename} - {len(labels)} labels, {len(objects)} objects")
        return True

    except Exception as e:
        logger.error(f"✗ {image_uri.split('/')[-1]}: {e}")
        return False

def main():
    logger.info("Completing Vision API analysis for remaining images...")

    # Get images that haven't been analyzed yet
    query = """
    SELECT uri
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality = 'image'
    AND (text_content IS NULL
         OR text_content NOT LIKE '%Vision API content extraction%')
    ORDER BY uri
    """

    results = bq_client.query(query).result()
    remaining_uris = [row.uri for row in results]

    logger.info(f"Found {len(remaining_uris)} images to analyze")

    if len(remaining_uris) == 0:
        logger.info("All images already analyzed!")
        return

    # Process remaining images
    success_count = 0
    for i, uri in enumerate(remaining_uris, 1):
        logger.info(f"[{i}/{len(remaining_uris)}] Processing {uri.split('/')[-1]}...")

        if analyze_and_update_image(uri):
            success_count += 1

        # Rate limit
        if i < len(remaining_uris):
            time.sleep(0.5)

    # Final check
    check_query = """
    SELECT COUNT(*) as total,
           SUM(CASE WHEN text_content LIKE '%Vision API content extraction%' THEN 1 ELSE 0 END) as analyzed
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality = 'image'
    """

    result = bq_client.query(check_query).result()
    for row in result:
        logger.info(f"\n{'='*60}")
        logger.info(f"Vision API Analysis Complete!")
        logger.info(f"Total images: {row.total}")
        logger.info(f"Analyzed with Vision API: {row.analyzed}")
        logger.info(f"Success rate: {row.analyzed}/{row.total} ({100*row.analyzed/row.total:.1f}%)")

    logger.info(f"\nNext: Run 'uv run bq-semgrep index --update' to regenerate embeddings")

if __name__ == "__main__":
    main()