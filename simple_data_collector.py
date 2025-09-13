#!/usr/bin/env python3
"""
Simplified multimodal data collector for GCS upload.
Downloads various types of public data and uploads to Google Cloud Storage.
"""

import json
import os
import requests
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict
from google.cloud import storage


def download_text_samples(output_dir: Path, num_samples: int = 5) -> None:
    """Download sample text files from Project Gutenberg."""
    print(f"Downloading {num_samples} text samples from Project Gutenberg...")
    text_dir = output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    # Popular public domain books
    book_ids = [
        ("1342", "pride_and_prejudice.txt"),
        ("11", "alice_in_wonderland.txt"),
        ("84", "frankenstein.txt"),
        ("1661", "sherlock_holmes.txt"),
        ("98", "tale_of_two_cities.txt"),
    ]

    for i, (book_id, filename) in enumerate(book_ids[:num_samples]):
        url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = text_dir / filename
                file_path.write_text(response.text[:50000])  # Save first 50KB
                print(f"  Downloaded: {filename}")
            else:
                # Try alternative URL format
                url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    file_path = text_dir / filename
                    file_path.write_text(response.text[:50000])
                    print(f"  Downloaded: {filename}")
        except Exception as e:
            print(f"  Failed to download book {book_id}: {e}")


def download_json_samples(output_dir: Path, num_samples: int = 5) -> None:
    """Download sample JSON data from public APIs."""
    print(f"Downloading {num_samples} JSON samples from public APIs...")
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    apis = [
        ("https://api.github.com/repos/python/cpython", "python_repo.json"),
        ("https://api.github.com/repos/tensorflow/tensorflow", "tensorflow_repo.json"),
        ("https://api.github.com/repos/facebook/react", "react_repo.json"),
        ("https://api.github.com/repos/torvalds/linux", "linux_repo.json"),
        ("https://api.github.com/repos/microsoft/vscode", "vscode_repo.json"),
    ]

    for i, (url, filename) in enumerate(apis[:num_samples]):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = json_dir / filename
                file_path.write_text(json.dumps(response.json(), indent=2))
                print(f"  Downloaded: {filename}")
        except Exception as e:
            print(f"  Failed to download {filename}: {e}")


def download_csv_samples(output_dir: Path, num_samples: int = 5) -> None:
    """Download sample CSV files from public sources."""
    print(f"Downloading {num_samples} CSV samples...")
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Use simple CSV data
    csv_samples = [
        ("https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv", "covid_data.csv"),
        ("https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv", "airports.csv"),
        ("https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv", "country_codes.csv"),
        ("https://raw.githubusercontent.com/datasets/population/main/data/population.csv", "population.csv"),
        ("https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv", "gdp.csv"),
    ]

    for i, (url, filename) in enumerate(csv_samples[:num_samples]):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = csv_dir / filename
                # Save first 100 lines to keep size manageable
                lines = response.text.split('\n')[:100]
                file_path.write_text('\n'.join(lines))
                print(f"  Downloaded: {filename}")
        except Exception as e:
            print(f"  Failed to download {filename}: {e}")


def download_markdown_samples(output_dir: Path, num_samples: int = 5) -> None:
    """Download README files from popular GitHub repos."""
    print(f"Downloading {num_samples} markdown samples from GitHub...")
    md_dir = output_dir / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)

    repos = [
        ("facebook/react", "react_readme.md"),
        ("tensorflow/tensorflow", "tensorflow_readme.md"),
        ("vuejs/vue", "vue_readme.md"),
        ("torvalds/linux", "linux_readme.md"),
        ("microsoft/TypeScript", "typescript_readme.md"),
    ]

    for i, (repo, filename) in enumerate(repos[:num_samples]):
        try:
            url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                # Try master branch
                url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
                response = requests.get(url, timeout=30)

            if response.status_code == 200:
                file_path = md_dir / filename
                file_path.write_text(response.text)
                print(f"  Downloaded: {filename}")
        except Exception as e:
            print(f"  Failed to download {filename}: {e}")


def download_image_samples(output_dir: Path, num_samples: int = 5) -> None:
    """Download sample images from Lorem Picsum."""
    print(f"Downloading {num_samples} image samples...")
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, min(num_samples + 1, 6)):
        try:
            # Lorem Picsum provides random images
            url = f"https://picsum.photos/400/300?random={i}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = image_dir / f"image_{i:03d}.jpg"
                file_path.write_bytes(response.content)
                print(f"  Downloaded: image_{i:03d}.jpg")
        except Exception as e:
            print(f"  Failed to download image {i}: {e}")


def upload_to_gcs(bucket_name: str, local_dir: Path, project_id: str = "semgrep-472018") -> None:
    """Upload directory contents to Google Cloud Storage."""
    print(f"\nUploading to gs://{bucket_name}/...")

    try:
        # Initialize client with explicit project
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)

        uploaded_count = 0
        for root, dirs, files in os.walk(local_dir):
            for file_name in files:
                file_path = Path(root) / file_name
                # Create blob path relative to local_dir
                blob_path = f"demo-data/{os.path.relpath(file_path, local_dir)}"
                blob = bucket.blob(blob_path)

                try:
                    blob.upload_from_filename(str(file_path))
                    print(f"  Uploaded: {blob_path}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"  Failed to upload {blob_path}: {e}")

        print(f"\nSuccessfully uploaded {uploaded_count} files to gs://{bucket_name}/demo-data/")

    except Exception as e:
        print(f"Failed to connect to GCS: {e}")
        print("\nTo fix authentication issues:")
        print("1. Run: gcloud auth application-default login")
        print("2. Or set: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")


def main():
    """Main function to download and upload multimodal data."""
    import argparse

    parser = argparse.ArgumentParser(description="Download and upload multimodal data to GCS")
    parser.add_argument("--num-samples", type=int, default=5, help="Number of samples per data type")
    parser.add_argument("--bucket", default="gcm-data-lake", help="GCS bucket name")
    parser.add_argument("--project", default="semgrep-472018", help="GCP project ID")
    args = parser.parse_args()

    # Create temporary directory for downloads
    output_dir = Path("/tmp/multimodal_data")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Multimodal Data Collector ===\n")

    # Download different types of data
    num_samples = args.num_samples

    download_text_samples(output_dir, num_samples)
    download_json_samples(output_dir, num_samples)
    download_csv_samples(output_dir, num_samples)
    download_markdown_samples(output_dir, num_samples)
    download_image_samples(output_dir, num_samples)

    # List downloaded files
    print(f"\n=== Downloaded files in {output_dir} ===")
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(str(output_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{sub_indent}{file}')

    # Upload to GCS
    upload_to_gcs(args.bucket, output_dir, args.project)


if __name__ == "__main__":
    main()