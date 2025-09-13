# bq-semgrep

A Python package for BigQuery and Semgrep integration.

## Prerequisites

### Google Cloud Setup

1. **Google Cloud Project**: You need access to a Google Cloud Project with BigQuery and Cloud Storage enabled.
   - Example project: `semgrep-472018`

2. **Google Cloud Storage Bucket**: A GCS bucket for storing data.
   - Example bucket: `gcm-data-lake`

3. **Authentication**: Authenticate with Google Cloud:
   ```bash
   gcloud auth login
   gcloud config set project semgrep-472018
   ```

4. **Verify Access**: Use these commands to verify your Google Cloud access:
   ```bash
   # Check current authenticated account
   gcloud auth list

   # Verify current project
   gcloud config get-value project

   # Check storage bucket access
   gcloud storage buckets list

   # Check specific bucket access
   gcloud storage ls gs://gcm-data-lake/

   # Check BigQuery access
   bq ls

   # Check your IAM permissions for the project
   gcloud projects get-iam-policy semgrep-472018 \
     --flatten="bindings[].members" \
     --filter="bindings.members:$(gcloud config get-value account)" \
     --format="table(bindings.role)"
   ```

5. **Required Permissions**: Your account needs the following IAM roles:
   - `roles/storage.admin` or `roles/storage.objectViewer` for bucket access
   - `roles/bigquery.admin` or `roles/bigquery.dataEditor` for BigQuery operations

### Development Environment

- Python 3.11+
- uv package manager

## Installation

```bash
# Install dependencies
uv sync

# Run the package
uv run bq-semgrep
```

## Configuration

Set your Google Cloud project:
```bash
export GOOGLE_CLOUD_PROJECT=semgrep-472018
export GCS_BUCKET=gcm-data-lake
```

## Usage

### Running the Main Package

```bash
# Run with uv
uv run bq-semgrep

# Or install in development mode
uv pip install -e .
bq-semgrep
```

### Data Collection Scripts

#### Simple Data Collector (Recommended)

The `simple_data_collector.py` script downloads various types of public data and uploads to GCS:

```bash
# Run with default settings (5 samples per type)
uv run python simple_data_collector.py

# Run with more samples
uv run python simple_data_collector.py --num-samples 20

# Specify custom bucket and project
uv run python simple_data_collector.py --bucket my-bucket --project my-project
```

**Data types collected:**
- Text files from Project Gutenberg (classic literature)
- JSON data from GitHub API (repository information)
- CSV files from public datasets (COVID data, airports, etc.)
- Markdown files from popular GitHub repositories
- Images from Lorem Picsum service

#### Advanced Data Collector

The `download_upload_resources.py` script downloads multimodal demo data and uploads it to GCS:

1. **Install dependencies**:
   ```bash
   uv add google-cloud-storage arxiv datasets tensorflow-datasets imageio imageio-ffmpeg
   ```

2. **Set up Google Cloud authentication**:
   ```bash
   # Option 1: Use gcloud auth (recommended)
   gcloud auth application-default login

   # Option 2: Use service account key
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

3. **Run the script**:
   ```bash
   # Full dataset (100 samples per modality)
   uv run python download_upload_resources.py \
       --bucket gcm-data-lake \
       --num_samples 100

   # Small test run (5 samples per modality)
   uv run python download_upload_resources.py \
       --bucket gcm-data-lake \
       --num_samples 5 \
       --output_dir /tmp/semgrep_data
   ```

**Script Options**:
- `--bucket`: GCS bucket name (required)
- `--num_samples`: Number of items per modality (default: 100)
- `--output_dir`: Local directory for downloads (default: temp directory)
- `--language`: Language for audio samples (default: 'en')
- `--arxiv_category`: arXiv category for papers (default: 'cs.CL')

**Data Types Downloaded**:
- Chat conversations from Cornell Movie-Dialogs Corpus
- Audio clips from Mozilla Common Voice
- Video clips from UCF101 dataset
- PDF papers from arXiv
- README files from popular GitHub repositories

**Note**: The full download can consume several GB of bandwidth and disk space. Use smaller `--num_samples` for testing.