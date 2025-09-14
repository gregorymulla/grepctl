#!/usr/bin/env python3
"""
Update ALL image documents in BigQuery with Vision API analysis.
"""

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
        labels_response = vision_client.label_detection(image=image, max_results=15)
        labels = labels_response.label_annotations

        # Detect objects
        objects_response = vision_client.object_localization(image=image, max_results=10)
        objects = objects_response.localized_object_annotations

        # Detect text
        text_response = vision_client.text_detection(image=image)
        texts = text_response.text_annotations

        # Detect dominant colors
        props_response = vision_client.image_properties(image=image)
        colors = props_response.image_properties_annotation.dominant_colors.colors

        # Detect landmarks
        landmarks_response = vision_client.landmark_detection(image=image)
        landmarks = landmarks_response.landmark_annotations

        # Detect faces (just count for privacy)
        faces_response = vision_client.face_detection(image=image)
        faces = faces_response.face_annotations

        # Build comprehensive description
        description_parts = []

        # Add file info
        filename = image_uri.split('/')[-1]
        description_parts.append(f"Image File: {filename}")
        description_parts.append(f"Location: {image_uri}")

        # Add detected labels with confidence
        if labels:
            label_list = [f"{label.description}" for label in labels]
            description_parts.append(f"Visual Content: {', '.join(label_list[:10])}")

            # Add confidence scores for top labels
            top_labels = [f"{label.description} ({label.score:.1%})" for label in labels[:5]]
            description_parts.append(f"Top Labels: {', '.join(top_labels)}")

        # Add detected objects with location info
        if objects:
            object_list = [f"{obj.name}" for obj in objects[:5]]
            description_parts.append(f"Detected Objects: {', '.join(object_list)}")

            # Add object details
            object_details = []
            for obj in objects[:3]:
                conf = f"{obj.score:.1%}"
                object_details.append(f"{obj.name} ({conf})")
            if object_details:
                description_parts.append(f"Object Details: {', '.join(object_details)}")

        # Add detected text if any
        if texts and len(texts) > 0:
            text_content = texts[0].description.replace('\n', ' ').strip()
            if text_content:
                preview = text_content[:200] + "..." if len(text_content) > 200 else text_content
                description_parts.append(f"Detected Text: {preview}")

        # Add dominant colors
        if colors and len(colors) > 0:
            color_descriptions = []
            for color in colors[:5]:
                r, g, b = int(color.color.red), int(color.color.green), int(color.color.blue)
                # Convert to hex for readability
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                coverage = f"{color.pixel_fraction:.1%}" if hasattr(color, 'pixel_fraction') else "N/A"
                color_descriptions.append(f"{hex_color} ({coverage})")
            description_parts.append(f"Dominant Colors: {', '.join(color_descriptions[:3])}")

        # Add landmarks if detected
        if landmarks:
            landmark_names = [landmark.description for landmark in landmarks[:3]]
            description_parts.append(f"Landmarks: {', '.join(landmark_names)}")

        # Add face count if detected (privacy-conscious)
        if faces:
            description_parts.append(f"People Detected: {len(faces)} face(s)")

        # Add scene understanding
        scene_labels = []
        for label in labels[:20]:
            label_lower = label.description.lower()
            # Categorize into scenes/environments
            if any(word in label_lower for word in ['outdoor', 'indoor', 'nature', 'city', 'urban',
                                                     'forest', 'beach', 'mountain', 'office', 'home']):
                scene_labels.append(label.description)

        if scene_labels:
            description_parts.append(f"Scene Type: {', '.join(scene_labels[:3])}")

        # Add semantic categories
        categories = set()
        for label in labels[:15]:
            label_lower = label.description.lower()
            if any(word in label_lower for word in ['animal', 'bird', 'dog', 'cat', 'wildlife']):
                categories.add("Animals")
            elif any(word in label_lower for word in ['person', 'people', 'human', 'face', 'man', 'woman']):
                categories.add("People")
            elif any(word in label_lower for word in ['food', 'cuisine', 'meal', 'drink']):
                categories.add("Food & Drink")
            elif any(word in label_lower for word in ['car', 'vehicle', 'transport', 'airplane', 'train']):
                categories.add("Transportation")
            elif any(word in label_lower for word in ['building', 'architecture', 'house', 'structure']):
                categories.add("Architecture")
            elif any(word in label_lower for word in ['plant', 'tree', 'flower', 'vegetation']):
                categories.add("Nature & Plants")
            elif any(word in label_lower for word in ['technology', 'computer', 'device', 'electronic']):
                categories.add("Technology")
            elif any(word in label_lower for word in ['sport', 'game', 'fitness', 'recreation']):
                categories.add("Sports & Recreation")

        if categories:
            description_parts.append(f"Categories: {', '.join(sorted(categories))}")

        # Add analysis metadata
        description_parts.append("Analysis: Complete Vision API content extraction with labels, objects, colors, text, and scene understanding")
        description_parts.append(f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

        return {
            'uri': image_uri,
            'text_content': '\n'.join(description_parts),
            'success': True,
            'label_count': len(labels),
            'object_count': len(objects),
            'has_text': len(texts) > 0,
            'has_faces': len(faces) > 0
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

def update_batch_in_bigquery(results: List[Dict[str, Any]]):
    """Update multiple images in BigQuery in a single query."""
    successful_results = [r for r in results if r['success'] and r['text_content']]

    if not successful_results:
        return

    # Build VALUES for batch update
    values = []
    for result in successful_results:
        # Escape single quotes in text content
        text_content = result['text_content'].replace("'", "''")
        values.append(f"('{result['uri']}', '''{text_content}''')")

    # Update search_corpus table
    update_query = f"""
    WITH updates AS (
        SELECT * FROM UNNEST([
            STRUCT{','.join(values)}
        ])
    )
    UPDATE `semgrep-472018.mmgrep.search_corpus` sc
    SET sc.text_content = updates.text_content
    FROM updates
    WHERE sc.uri = updates.uri
    """

    try:
        job = bq_client.query(update_query)
        job.result()
        logger.info(f"Batch updated {len(successful_results)} images in search_corpus")
    except Exception as e:
        logger.error(f"Batch update failed, falling back to individual updates: {e}")
        # Fall back to individual updates
        for result in successful_results:
            update_individual(result['uri'], result['text_content'])

def update_individual(uri: str, text_content: str):
    """Update a single image in BigQuery."""
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

    try:
        job = bq_client.query(query, job_config=job_config)
        job.result()
    except Exception as e:
        logger.error(f"Failed to update {uri}: {e}")

def process_batch(image_uris: List[str], batch_num: int, total_batches: int) -> List[Dict[str, Any]]:
    """Process a batch of images with parallel Vision API calls."""
    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(image_uris)} images)")

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_image, uri): uri for uri in image_uris}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if result['success']:
                stats = []
                if result.get('label_count', 0) > 0:
                    stats.append(f"{result['label_count']} labels")
                if result.get('object_count', 0) > 0:
                    stats.append(f"{result['object_count']} objects")
                if result.get('has_text'):
                    stats.append("text")
                if result.get('has_faces'):
                    stats.append("faces")

                stats_str = f" [{', '.join(stats)}]" if stats else ""
                logger.info(f"✓ Analyzed: {result['uri'].split('/')[-1]}{stats_str}")
            else:
                logger.error(f"✗ Failed: {result['uri'].split('/')[-1]} - {result.get('error', 'Unknown error')}")

    return results

def main():
    """Main function to update all images with Vision API analysis."""
    logger.info("="*70)
    logger.info("Starting comprehensive Vision API analysis for ALL images...")
    logger.info("="*70)

    # Get all image URIs
    image_uris = get_image_uris()
    logger.info(f"Found {len(image_uris)} total images to analyze")

    # Check if any already have Vision content
    check_query = """
    SELECT COUNT(*) as analyzed_count
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality = 'image'
    AND text_content LIKE '%Vision API content extraction%'
    """

    result = bq_client.query(check_query).result()
    analyzed_count = list(result)[0].analyzed_count
    logger.info(f"Already analyzed with Vision API: {analyzed_count} images")

    if analyzed_count > 0:
        logger.info(f"Will analyze remaining {len(image_uris) - analyzed_count} images")

    # Process in batches to manage rate limits and memory
    batch_size = 10
    batches = [image_uris[i:i + batch_size] for i in range(0, len(image_uris), batch_size)]

    all_results = []
    successful_count = 0
    failed_count = 0

    start_time = time.time()

    for i, batch in enumerate(batches, 1):
        batch_results = process_batch(batch, i, len(batches))
        all_results.extend(batch_results)

        # Update BigQuery with batch results
        update_batch_in_bigquery(batch_results)

        # Track statistics
        batch_successful = sum(1 for r in batch_results if r['success'])
        batch_failed = len(batch_results) - batch_successful
        successful_count += batch_successful
        failed_count += batch_failed

        # Progress update
        total_processed = len(all_results)
        progress_pct = (total_processed / len(image_uris)) * 100
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        eta = (len(image_uris) - total_processed) / rate if rate > 0 else 0

        logger.info(f"Progress: {total_processed}/{len(image_uris)} ({progress_pct:.1f}%) | "
                   f"Rate: {rate:.1f} imgs/sec | ETA: {eta:.0f}s")

        # Rate limiting between batches
        if i < len(batches):
            time.sleep(1)  # 1 second between batches to avoid rate limits

    # Final statistics
    elapsed_total = time.time() - start_time

    logger.info("="*70)
    logger.info("Vision API Analysis Complete!")
    logger.info("="*70)
    logger.info(f"Total images processed: {len(all_results)}")
    logger.info(f"Successfully analyzed: {successful_count}")
    if failed_count > 0:
        logger.warning(f"Failed: {failed_count}")
    logger.info(f"Total time: {elapsed_total:.1f} seconds")
    logger.info(f"Average rate: {len(all_results)/elapsed_total:.1f} images/second")

    # Show sample of analyzed content
    logger.info("\n" + "="*70)
    logger.info("Sample of Vision-extracted content:")
    logger.info("="*70)

    sample_query = """
    SELECT uri, text_content
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality = 'image'
    AND text_content LIKE '%Vision API content extraction%'
    LIMIT 3
    """

    sample_results = bq_client.query(sample_query).result()
    for row in sample_results:
        logger.info(f"\n{row.uri.split('/')[-1]}:")
        lines = row.text_content.split('\n')[:5]  # First 5 lines
        for line in lines:
            logger.info(f"  {line}")

    # Next steps
    logger.info("\n" + "="*70)
    logger.info("Next Steps:")
    logger.info("="*70)
    logger.info("1. Run: uv run bq-semgrep index --update")
    logger.info("   This will regenerate embeddings with the Vision-extracted content")
    logger.info("2. Test searches like:")
    logger.info("   - uv run bq-semgrep search 'bird flying in nature'")
    logger.info("   - uv run bq-semgrep search 'people faces portrait'")
    logger.info("   - uv run bq-semgrep search 'text signs writing'")
    logger.info("   - uv run bq-semgrep search 'red blue colors'")

if __name__ == "__main__":
    main()