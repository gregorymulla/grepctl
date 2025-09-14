#!/bin/bash
set -e

# ==============================================================================
# BigQuery Semantic Grep (mmgrep) - Automated Setup Script
# ==============================================================================
# This script automates the complete setup of the BigQuery Semantic Grep system
# including dataset creation, external tables, data ingestion, and embeddings.
# ==============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-semgrep-472018}"
DATASET_NAME="${BQ_DATASET:-mmgrep}"
LOCATION="${BQ_LOCATION:-US}"
GCS_BUCKET="${GCS_BUCKET:-gcm-data-lake}"
GCS_PREFIX="${GCS_PREFIX:-multimodal-dataset}"
CONNECTION_NAME="bigquery-gcs"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check for gcloud
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi

    # Check for bq
    if ! command_exists bq; then
        print_error "bq CLI is not installed. Please install it first."
        exit 1
    fi

    # Check for gsutil
    if ! command_exists gsutil; then
        print_error "gsutil is not installed. Please install it first."
        exit 1
    fi

    # Check for uv (Python package manager)
    if ! command_exists uv; then
        print_warning "uv is not installed. Will use pip instead."
        USE_UV=false
    else
        USE_UV=true
    fi

    print_success "All prerequisites are installed"
}

# Function to setup Google Cloud authentication
setup_authentication() {
    print_info "Setting up Google Cloud authentication..."

    # Set project
    gcloud config set project "$PROJECT_ID"

    # Set quota project for ADC
    gcloud auth application-default set-quota-project "$PROJECT_ID"

    # Verify authentication
    CURRENT_USER=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    if [ -z "$CURRENT_USER" ]; then
        print_error "No active Google Cloud account found. Please run: gcloud auth login"
        exit 1
    fi

    print_success "Authenticated as: $CURRENT_USER"
    print_success "Project set to: $PROJECT_ID"
}

# Function to create BigQuery dataset
create_dataset() {
    print_info "Creating BigQuery dataset: $DATASET_NAME..."

    # Check if dataset exists
    if bq ls -d --project_id="$PROJECT_ID" | grep -q "$DATASET_NAME"; then
        print_warning "Dataset $DATASET_NAME already exists"
    else
        bq mk --dataset --location="$LOCATION" --project_id="$PROJECT_ID" "$DATASET_NAME"
        print_success "Dataset $DATASET_NAME created"
    fi
}

# Function to create core tables
create_core_tables() {
    print_info "Creating core tables..."

    # Create documents table
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
CREATE OR REPLACE TABLE \`$PROJECT_ID.$DATASET_NAME.documents\` (
    doc_id STRING NOT NULL,
    uri STRING NOT NULL,
    modality STRING NOT NULL,
    source STRING NOT NULL,
    created_at TIMESTAMP NOT NULL,
    author STRING,
    channel STRING,
    text_content STRING,
    mime_type STRING,
    meta JSON,
    chunk_index INT64,
    chunk_start INT64,
    chunk_end INT64,
    embedding ARRAY<FLOAT64>
)
PARTITION BY DATE(created_at)
CLUSTER BY modality, source;
EOF

    # Create document_chunks table
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
CREATE OR REPLACE TABLE \`$PROJECT_ID.$DATASET_NAME.document_chunks\` (
    doc_id STRING NOT NULL,
    uri STRING NOT NULL,
    modality STRING NOT NULL,
    source STRING NOT NULL,
    created_at TIMESTAMP NOT NULL,
    author STRING,
    channel STRING,
    text_content STRING,
    mime_type STRING,
    meta JSON,
    chunk_index INT64,
    chunk_start INT64,
    chunk_end INT64,
    embedding ARRAY<FLOAT64>
)
PARTITION BY DATE(created_at)
CLUSTER BY modality, source;
EOF

    # Create search_corpus table
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
CREATE OR REPLACE TABLE \`$PROJECT_ID.$DATASET_NAME.search_corpus\` (
    doc_id STRING NOT NULL,
    uri STRING NOT NULL,
    modality STRING NOT NULL,
    source STRING NOT NULL,
    created_at TIMESTAMP NOT NULL,
    author STRING,
    channel STRING,
    text_content STRING,
    mime_type STRING,
    meta JSON,
    chunk_index INT64,
    chunk_start INT64,
    chunk_end INT64,
    embedding ARRAY<FLOAT64>
)
PARTITION BY DATE(created_at)
CLUSTER BY modality, source;
EOF

    print_success "Core tables created"
}

# Function to create BigQuery connection for GCS
create_gcs_connection() {
    print_info "Creating BigQuery connection for GCS..."

    # Check if connection exists
    if bq show --connection --location="$LOCATION" --project_id="$PROJECT_ID" "$CONNECTION_NAME" >/dev/null 2>&1; then
        print_warning "Connection $CONNECTION_NAME already exists"
    else
        bq mk --connection --location="$LOCATION" --project_id="$PROJECT_ID" \
            --connection_type=CLOUD_RESOURCE "$CONNECTION_NAME"
        print_success "Connection $CONNECTION_NAME created"
    fi

    # Get service account for the connection
    SERVICE_ACCOUNT=$(bq show --connection --location="$LOCATION" --project_id="$PROJECT_ID" "$CONNECTION_NAME" \
        | grep serviceAccountId | sed 's/.*"serviceAccountId": "\(.*\)".*/\1/')

    if [ -n "$SERVICE_ACCOUNT" ]; then
        print_info "Granting GCS access to service account: $SERVICE_ACCOUNT"
        gsutil iam ch "serviceAccount:$SERVICE_ACCOUNT:objectViewer" "gs://$GCS_BUCKET" || true
        print_success "GCS access granted"
    fi
}

# Function to create external tables
create_external_tables() {
    print_info "Creating external tables..."

    MODALITIES=("text" "pdf" "images" "audio" "video" "json" "csv" "markdown" "documents")

    for modality in "${MODALITIES[@]}"; do
        print_info "Creating external table for $modality..."

        bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
CREATE OR REPLACE EXTERNAL TABLE \`$PROJECT_ID.$DATASET_NAME.obj_${modality}\`
WITH CONNECTION \`$PROJECT_ID.$LOCATION.$CONNECTION_NAME\`
OPTIONS (
    object_metadata = 'SIMPLE',
    uris = ['gs://$GCS_BUCKET/$GCS_PREFIX/${modality}/*']
);
EOF
    done

    print_success "All external tables created"
}

# Function to ingest text and markdown files
ingest_simple_data() {
    print_info "Ingesting text and markdown files..."

    # Ingest text files
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
INSERT INTO \`$PROJECT_ID.$DATASET_NAME.documents\`
SELECT
    GENERATE_UUID() AS doc_id,
    uri AS uri,
    'text' AS modality,
    'file' AS source,
    CURRENT_TIMESTAMP() AS created_at,
    NULL AS author,
    NULL AS channel,
    SAFE_CAST(data AS STRING) AS text_content,
    content_type AS mime_type,
    TO_JSON(STRUCT(
        size,
        updated AS last_modified,
        generation
    )) AS meta,
    NULL AS chunk_index,
    NULL AS chunk_start,
    NULL AS chunk_end,
    NULL AS embedding
FROM \`$PROJECT_ID.$DATASET_NAME.obj_text\`
WHERE uri NOT IN (
    SELECT DISTINCT uri FROM \`$PROJECT_ID.$DATASET_NAME.documents\`
    WHERE modality = 'text'
);
EOF

    # Ingest markdown files
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
INSERT INTO \`$PROJECT_ID.$DATASET_NAME.documents\`
SELECT
    GENERATE_UUID() AS doc_id,
    uri AS uri,
    'text' AS modality,
    'markdown' AS source,
    CURRENT_TIMESTAMP() AS created_at,
    NULL AS author,
    NULL AS channel,
    SAFE_CAST(data AS STRING) AS text_content,
    content_type AS mime_type,
    TO_JSON(STRUCT(
        size,
        updated AS last_modified,
        generation
    )) AS meta,
    NULL AS chunk_index,
    NULL AS chunk_start,
    NULL AS chunk_end,
    NULL AS embedding
FROM \`$PROJECT_ID.$DATASET_NAME.obj_markdown\`
WHERE uri NOT IN (
    SELECT DISTINCT uri FROM \`$PROJECT_ID.$DATASET_NAME.documents\`
    WHERE source = 'markdown'
);
EOF

    print_success "Simple data ingested"
}

# Function to create search corpus
create_search_corpus() {
    print_info "Creating search corpus..."

    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" <<EOF
CREATE OR REPLACE TABLE \`$PROJECT_ID.$DATASET_NAME.search_corpus\`
PARTITION BY DATE(created_at)
CLUSTER BY modality, source AS
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
    CAST(NULL AS ARRAY<FLOAT64>) AS embedding
FROM \`$PROJECT_ID.$DATASET_NAME.documents\`
WHERE text_content IS NOT NULL;
EOF

    print_success "Search corpus created"
}

# Function to verify setup
verify_setup() {
    print_info "Verifying setup..."

    # Check dataset
    if bq ls -d --project_id="$PROJECT_ID" | grep -q "$DATASET_NAME"; then
        print_success "✓ Dataset exists: $DATASET_NAME"
    else
        print_error "✗ Dataset not found: $DATASET_NAME"
    fi

    # Check tables
    TABLE_COUNT=$(bq ls "$PROJECT_ID:$DATASET_NAME" | grep -c TABLE)
    EXTERNAL_COUNT=$(bq ls "$PROJECT_ID:$DATASET_NAME" | grep -c EXTERNAL)
    print_success "✓ Tables created: $TABLE_COUNT regular, $EXTERNAL_COUNT external"

    # Check document count
    DOC_COUNT=$(bq query --use_legacy_sql=false --format=csv --project_id="$PROJECT_ID" \
        "SELECT COUNT(*) FROM \`$PROJECT_ID.$DATASET_NAME.documents\`" | tail -1)
    print_success "✓ Documents ingested: $DOC_COUNT"

    # Check search corpus
    CORPUS_COUNT=$(bq query --use_legacy_sql=false --format=csv --project_id="$PROJECT_ID" \
        "SELECT COUNT(*) FROM \`$PROJECT_ID.$DATASET_NAME.search_corpus\`" | tail -1)
    print_success "✓ Search corpus size: $CORPUS_COUNT"
}

# Function to create configuration file
create_config_file() {
    print_info "Creating configuration file..."

    CONFIG_DIR="$HOME/.bq-semgrep"
    mkdir -p "$CONFIG_DIR"

    cat > "$CONFIG_DIR/config.yaml" <<EOF
# BigQuery Semantic Grep Configuration
project_id: "$PROJECT_ID"
dataset_name: "$DATASET_NAME"
location: "$LOCATION"

# GCS settings
gcs_bucket: "$GCS_BUCKET"
gcs_prefix: "$GCS_PREFIX"
gcs_connection: "projects/$PROJECT_ID/locations/$LOCATION/connections/$CONNECTION_NAME"

# Model configurations - will be auto-generated
text_model: ""
embedding_model: ""

# Chunking parameters
chunk_size: 1000
chunk_overlap: 200
max_chunk_size: 1200

# Search parameters
default_top_k: 20
search_multiplier: 5
max_search_count: 200
rerank_threshold: 50

# Vector index parameters
index_type: "IVF"
distance_type: "COSINE"
ivf_min_train_size: 10000

# Processing parameters
batch_size: 100
max_workers: 4
timeout_seconds: 300

# Logging
log_level: "INFO"
EOF

    print_success "Configuration file created at: $CONFIG_DIR/config.yaml"
}

# Function to display next steps
display_next_steps() {
    echo ""
    echo -e "${GREEN}==============================================================================
Setup Complete! BigQuery Semantic Grep (mmgrep) is ready to use.
==============================================================================${NC}"
    echo ""
    echo "Summary:"
    echo "  • Project: $PROJECT_ID"
    echo "  • Dataset: $DATASET_NAME"
    echo "  • Location: $LOCATION"
    echo "  • GCS Bucket: gs://$GCS_BUCKET/$GCS_PREFIX"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "1. Generate embeddings for semantic search:"
    echo "   ${BLUE}uv run bq-semgrep index --update${NC}"
    echo ""
    echo "2. Build vector index:"
    echo "   ${BLUE}uv run bq-semgrep index --rebuild${NC}"
    echo ""
    echo "3. Test semantic search:"
    echo "   ${BLUE}uv run bq-semgrep search \"your search query\"${NC}"
    echo ""
    echo "4. Check system status:"
    echo "   ${BLUE}uv run bq-semgrep status${NC}"
    echo ""
    echo "5. For more data ingestion (PDFs, images, etc.):"
    echo "   ${BLUE}uv run bq-semgrep ingest --bucket $GCS_BUCKET -m pdf -m images${NC}"
    echo ""
    echo "For SQL access, use:"
    echo "   ${BLUE}SELECT * FROM \`$PROJECT_ID.$DATASET_NAME.search_corpus\` LIMIT 10${NC}"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}==============================================================================
BigQuery Semantic Grep (mmgrep) - Automated Setup
==============================================================================${NC}"
    echo ""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project)
                PROJECT_ID="$2"
                shift 2
                ;;
            --dataset)
                DATASET_NAME="$2"
                shift 2
                ;;
            --bucket)
                GCS_BUCKET="$2"
                shift 2
                ;;
            --location)
                LOCATION="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --project PROJECT_ID    Google Cloud project ID (default: $PROJECT_ID)"
                echo "  --dataset DATASET_NAME  BigQuery dataset name (default: $DATASET_NAME)"
                echo "  --bucket BUCKET_NAME    GCS bucket name (default: $GCS_BUCKET)"
                echo "  --location LOCATION     BigQuery location (default: $LOCATION)"
                echo "  --help                  Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run setup steps
    check_prerequisites
    setup_authentication
    create_dataset
    create_core_tables
    create_gcs_connection
    create_external_tables
    ingest_simple_data
    create_search_corpus
    create_config_file
    verify_setup
    display_next_steps
}

# Run main function
main "$@"