#!/usr/bin/env python3
"""
Simple test script for GCS upload functionality
"""

import os
from pathlib import Path
from google.cloud import storage

def test_gcs_upload():
    """Test uploading a simple file to GCS"""
    bucket_name = "gcm-data-lake"
    test_dir = Path("/tmp/gcs_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create a test file
    test_file = test_dir / "test.txt"
    test_file.write_text("Hello from bq-semgrep test!")

    # Try to upload
    try:
        client = storage.Client(project="semgrep-472018")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("test/test.txt")
        blob.upload_from_filename(str(test_file))
        print(f"Successfully uploaded to gs://{bucket_name}/test/test.txt")
        return True
    except Exception as e:
        print(f"Upload failed: {e}")
        return False

if __name__ == "__main__":
    test_gcs_upload()