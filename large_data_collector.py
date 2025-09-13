#!/usr/bin/env python3
"""
Large-scale multimodal data collector for GCS upload.
Downloads 100+ items per data type from various public sources.
"""

import json
import os
import requests
import shutil
import tempfile
import random
import time
from pathlib import Path
from typing import List, Dict
from google.cloud import storage


def download_text_samples(output_dir: Path, num_samples: int = 100) -> None:
    """Download text files from multiple sources."""
    print(f"Downloading {num_samples} text samples...")
    text_dir = output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    # 1. Project Gutenberg - top 100 books
    gutenberg_ids = list(range(1, 70000))  # Many book IDs available
    random.shuffle(gutenberg_ids)

    for book_id in gutenberg_ids:
        if downloaded >= num_samples:
            break

        urls = [
            f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
            f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
            f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"
        ]

        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200 and len(response.text) > 1000:
                    filename = f"book_{downloaded+1:03d}.txt"
                    file_path = text_dir / filename
                    file_path.write_text(response.text[:50000])  # First 50KB
                    downloaded += 1
                    print(f"  Downloaded text {downloaded}/{num_samples}: {filename}")
                    break
            except:
                continue

        # Small delay to be respectful
        if downloaded % 10 == 0:
            time.sleep(0.5)

    print(f"  Total text files downloaded: {downloaded}")


def download_json_samples(output_dir: Path, num_samples: int = 100) -> None:
    """Download JSON data from various APIs."""
    print(f"Downloading {num_samples} JSON samples...")
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    # 1. GitHub repos - search for popular repos
    try:
        for page in range(1, (num_samples // 30) + 2):  # 30 per page
            if downloaded >= num_samples:
                break

            url = f"https://api.github.com/search/repositories?q=stars:>100&sort=stars&per_page=30&page={page}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                for repo in data.get('items', []):
                    if downloaded >= num_samples:
                        break
                    filename = f"repo_{downloaded+1:03d}.json"
                    file_path = json_dir / filename
                    file_path.write_text(json.dumps(repo, indent=2))
                    downloaded += 1
                    print(f"  Downloaded JSON {downloaded}/{num_samples}: {filename}")

            time.sleep(2)  # GitHub rate limiting
    except Exception as e:
        print(f"  GitHub API error: {e}")

    # 2. JSONPlaceholder API for remaining samples
    endpoints = ['posts', 'comments', 'albums', 'photos', 'todos', 'users']

    while downloaded < num_samples:
        endpoint = random.choice(endpoints)
        item_id = random.randint(1, 100)

        try:
            url = f"https://jsonplaceholder.typicode.com/{endpoint}/{item_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                filename = f"json_{downloaded+1:03d}.json"
                file_path = json_dir / filename
                file_path.write_text(json.dumps(response.json(), indent=2))
                downloaded += 1
                print(f"  Downloaded JSON {downloaded}/{num_samples}: {filename}")
        except:
            continue

    print(f"  Total JSON files downloaded: {downloaded}")


def download_csv_samples(output_dir: Path, num_samples: int = 100) -> None:
    """Download CSV files from various sources."""
    print(f"Downloading {num_samples} CSV samples...")
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    # Various CSV data sources
    csv_sources = [
        "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv",
        "https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv",
        "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv",
        "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
        "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv",
        "https://raw.githubusercontent.com/datasets/inflation/main/data/inflation.csv",
        "https://raw.githubusercontent.com/datasets/natural-gas/main/data/daily.csv",
        "https://raw.githubusercontent.com/datasets/oil-prices/main/data/brent-daily.csv",
    ]

    # Download base CSV files
    for i, url in enumerate(csv_sources):
        if downloaded >= num_samples:
            break

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Create variations of the same CSV with different row counts
                lines = response.text.split('\n')
                header = lines[0] if lines else ""

                # Create multiple files from the same source with different subsets
                for j in range(min(15, num_samples - downloaded)):
                    filename = f"csv_{downloaded+1:03d}.csv"
                    file_path = csv_dir / filename

                    # Take different slices of data
                    start = min(j * 10, len(lines) - 50)
                    end = min(start + 50 + (j * 5), len(lines))
                    subset = [header] + lines[start:end]

                    file_path.write_text('\n'.join(subset))
                    downloaded += 1
                    print(f"  Downloaded CSV {downloaded}/{num_samples}: {filename}")

                    if downloaded >= num_samples:
                        break
        except Exception as e:
            print(f"  Failed to download CSV: {e}")
            continue

    # Generate synthetic CSV data for remaining samples
    while downloaded < num_samples:
        filename = f"csv_{downloaded+1:03d}.csv"
        file_path = csv_dir / filename

        # Generate simple synthetic data
        data = "id,name,value,category\n"
        for row in range(50):
            data += f"{row},item_{row},{random.randint(1,1000)},category_{random.randint(1,10)}\n"

        file_path.write_text(data)
        downloaded += 1
        print(f"  Downloaded CSV {downloaded}/{num_samples}: {filename}")

    print(f"  Total CSV files downloaded: {downloaded}")


def download_markdown_samples(output_dir: Path, num_samples: int = 100) -> None:
    """Download markdown files from GitHub."""
    print(f"Downloading {num_samples} markdown samples...")
    md_dir = output_dir / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    # Search for repos with good READMEs
    try:
        for page in range(1, 5):  # Get repos from multiple pages
            if downloaded >= num_samples:
                break

            url = f"https://api.github.com/search/repositories?q=stars:>10&sort=stars&per_page=100&page={page}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                repos = response.json().get('items', [])

                for repo in repos:
                    if downloaded >= num_samples:
                        break

                    owner = repo['owner']['login']
                    name = repo['name']

                    # Try to get README
                    for branch in ['main', 'master']:
                        readme_url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/README.md"

                        try:
                            readme_response = requests.get(readme_url, timeout=10)
                            if readme_response.status_code == 200:
                                filename = f"readme_{downloaded+1:03d}.md"
                                file_path = md_dir / filename
                                file_path.write_text(readme_response.text[:100000])  # Limit size
                                downloaded += 1
                                print(f"  Downloaded markdown {downloaded}/{num_samples}: {filename}")
                                break
                        except:
                            continue

                time.sleep(2)  # Rate limiting
    except Exception as e:
        print(f"  GitHub API error: {e}")

    # Generate synthetic markdown for remaining
    while downloaded < num_samples:
        filename = f"markdown_{downloaded+1:03d}.md"
        file_path = md_dir / filename

        content = f"""# Sample Document {downloaded+1}

## Overview
This is a synthetic markdown document generated for testing purposes.

## Features
- Feature 1: Description of feature
- Feature 2: Another feature
- Feature 3: Yet another feature

## Installation
```bash
pip install sample-package-{downloaded+1}
```

## Usage
```python
import sample_{downloaded+1}
sample_{downloaded+1}.run()
```

## License
MIT License
"""
        file_path.write_text(content)
        downloaded += 1
        print(f"  Downloaded markdown {downloaded}/{num_samples}: {filename}")

    print(f"  Total markdown files downloaded: {downloaded}")


def download_image_samples(output_dir: Path, num_samples: int = 100) -> None:
    """Download images from Lorem Picsum."""
    print(f"Downloading {num_samples} image samples...")
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    for i in range(num_samples):
        try:
            # Use different dimensions for variety
            width = 200 + (i % 10) * 50
            height = 200 + ((i + 5) % 10) * 30

            url = f"https://picsum.photos/{width}/{height}?random={i}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                filename = f"image_{downloaded+1:03d}.jpg"
                file_path = image_dir / filename
                file_path.write_bytes(response.content)
                downloaded += 1
                print(f"  Downloaded image {downloaded}/{num_samples}: {filename}")

            # Small delay every 10 images
            if downloaded % 10 == 0:
                time.sleep(1)

        except Exception as e:
            print(f"  Failed to download image {i}: {e}")
            continue

    print(f"  Total images downloaded: {downloaded}")


def upload_to_gcs(bucket_name: str, local_dir: Path, project_id: str = "semgrep-472018") -> None:
    """Upload directory contents to Google Cloud Storage."""
    print(f"\nUploading to gs://{bucket_name}/...")

    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)

        uploaded_count = 0
        failed_count = 0

        for root, dirs, files in os.walk(local_dir):
            for file_name in files:
                file_path = Path(root) / file_name
                blob_path = f"large-dataset/{os.path.relpath(file_path, local_dir)}"
                blob = bucket.blob(blob_path)

                try:
                    blob.upload_from_filename(str(file_path))
                    uploaded_count += 1

                    if uploaded_count % 20 == 0:
                        print(f"  Uploaded {uploaded_count} files...")

                except Exception as e:
                    failed_count += 1
                    print(f"  Failed to upload {blob_path}: {e}")

        print(f"\n✅ Successfully uploaded {uploaded_count} files to gs://{bucket_name}/large-dataset/")
        if failed_count > 0:
            print(f"⚠️  Failed to upload {failed_count} files")

    except Exception as e:
        print(f"❌ Failed to connect to GCS: {e}")
        print("\nTo fix authentication issues:")
        print("1. Run: gcloud auth application-default login")
        print("2. Or set: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")


def main():
    """Main function to download and upload multimodal data."""
    import argparse

    parser = argparse.ArgumentParser(description="Download and upload large multimodal dataset to GCS")
    parser.add_argument("--num-samples", type=int, default=100,
                       help="Number of samples per data type (default: 100)")
    parser.add_argument("--bucket", default="gcm-data-lake", help="GCS bucket name")
    parser.add_argument("--project", default="semgrep-472018", help="GCP project ID")
    parser.add_argument("--output-dir", default="/tmp/large_multimodal_data",
                       help="Local directory for downloads")
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        print(f"Cleaning existing directory {output_dir}...")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Large Multimodal Data Collector ===")
    print(f"Target: {args.num_samples} samples per data type\n")

    # Download different types of data
    download_text_samples(output_dir, args.num_samples)
    download_json_samples(output_dir, args.num_samples)
    download_csv_samples(output_dir, args.num_samples)
    download_markdown_samples(output_dir, args.num_samples)
    download_image_samples(output_dir, args.num_samples)

    # Count total files
    total_files = sum(1 for _ in output_dir.rglob("*") if _.is_file())
    print(f"\n=== Total files downloaded: {total_files} ===")

    # Upload to GCS
    upload_to_gcs(args.bucket, output_dir, args.project)


if __name__ == "__main__":
    main()