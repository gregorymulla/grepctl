#!/bin/bash
set -e

# ==============================================================================
# Vertex AI Setup Script for BigQuery Semantic Grep
# ==============================================================================
# This script enables Vertex AI and configures all necessary permissions
# for semantic search capabilities in BigQuery
# ==============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-semgrep-472018}"
LOCATION="${2:-US}"
DATASET_NAME="${3:-mmgrep}"
CONNECTION_NAME="bigquery-gcs"

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

# Main setup function
setup_vertex_ai() {
    echo -e "${BLUE}==============================================================================
Vertex AI Setup for BigQuery Semantic Grep
==============================================================================${NC}"
    echo ""
    print_info "Project: $PROJECT_ID"
    print_info "Location: $LOCATION"
    print_info "Dataset: $DATASET_NAME"
    echo ""

    # Step 1: Enable Vertex AI API
    print_info "Step 1: Enabling Vertex AI API..."
    if gcloud services list --enabled --project="$PROJECT_ID" | grep -q "aiplatform.googleapis.com"; then
        print_success "Vertex AI API is already enabled"
    else
        gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID"
        print_success "Vertex AI API enabled"
        print_info "Waiting 30 seconds for API to propagate..."
        sleep 30
    fi

    # Step 2: Get the BigQuery connection service account
    print_info "Step 2: Getting BigQuery connection service account..."
    SERVICE_ACCOUNT=$(bq show --connection --location="$LOCATION" --project_id="$PROJECT_ID" "$CONNECTION_NAME" \
        | grep serviceAccountId | sed 's/.*"serviceAccountId": "\(.*\)".*/\1/')

    if [ -z "$SERVICE_ACCOUNT" ]; then
        print_error "Could not find service account for connection $CONNECTION_NAME"
        print_info "Creating connection..."
        bq mk --connection --location="$LOCATION" --project_id="$PROJECT_ID" \
            --connection_type=CLOUD_RESOURCE "$CONNECTION_NAME"

        SERVICE_ACCOUNT=$(bq show --connection --location="$LOCATION" --project_id="$PROJECT_ID" "$CONNECTION_NAME" \
            | grep serviceAccountId | sed 's/.*"serviceAccountId": "\(.*\)".*/\1/')
    fi

    print_success "Service account: $SERVICE_ACCOUNT"

    # Step 3: Grant Vertex AI permissions
    print_info "Step 3: Granting Vertex AI permissions to service account..."

    # Grant Vertex AI User role
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/aiplatform.user" \
        --quiet

    print_success "Granted roles/aiplatform.user"

    # Also grant BigQuery Data Editor role (if not already granted)
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/bigquery.dataEditor" \
        --quiet

    print_success "Granted roles/bigquery.dataEditor"

    # Grant Storage Object Viewer for GCS access
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/storage.objectViewer" \
        --quiet

    print_success "Granted roles/storage.objectViewer"

    # Step 4: Wait for permissions to propagate
    print_info "Step 4: Waiting for permissions to propagate (60 seconds)..."
    sleep 60

    # Step 5: Create embedding model using alternative approach
    print_info "Step 5: Creating embedding model in BigQuery..."

    # Try multiple approaches
    MODELS_CREATED=0

    # Approach 1: Try text-embedding-004
    print_info "Attempting to create model with text-embedding-004..."
    if bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "
        CREATE OR REPLACE MODEL \`$PROJECT_ID.$DATASET_NAME.text_embedding_model\`
        REMOTE WITH CONNECTION \`$PROJECT_ID.$LOCATION.$CONNECTION_NAME\`
        OPTIONS (
            endpoint = 'text-embedding-004'
        )
    " 2>/dev/null; then
        print_success "Created text_embedding_model with text-embedding-004"
        MODELS_CREATED=$((MODELS_CREATED + 1))
    else
        print_warning "Could not create model with text-embedding-004"
    fi

    # Approach 2: Try text-bison for embeddings
    print_info "Attempting to create model with text-bison..."
    if bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "
        CREATE OR REPLACE MODEL \`$PROJECT_ID.$DATASET_NAME.text_model\`
        REMOTE WITH CONNECTION \`$PROJECT_ID.$LOCATION.$CONNECTION_NAME\`
        OPTIONS (
            endpoint = 'text-bison'
        )
    " 2>/dev/null; then
        print_success "Created text_model with text-bison"
        MODELS_CREATED=$((MODELS_CREATED + 1))
    else
        print_warning "Could not create model with text-bison"
    fi

    # Approach 3: Try gemini-pro
    print_info "Attempting to create model with gemini-pro..."
    if bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "
        CREATE OR REPLACE MODEL \`$PROJECT_ID.$DATASET_NAME.gemini_model\`
        REMOTE WITH CONNECTION \`$PROJECT_ID.$LOCATION.$CONNECTION_NAME\`
        OPTIONS (
            endpoint = 'gemini-pro'
        )
    " 2>/dev/null; then
        print_success "Created gemini_model with gemini-pro"
        MODELS_CREATED=$((MODELS_CREATED + 1))
    else
        print_warning "Could not create model with gemini-pro"
    fi

    # Step 6: Verify setup
    print_info "Step 6: Verifying setup..."

    # Check if any models were created
    if [ $MODELS_CREATED -gt 0 ]; then
        print_success "Successfully created $MODELS_CREATED model(s)"
    else
        print_warning "No models could be created automatically"
        print_info "You may need to create models manually in the BigQuery console"
    fi

    # Check API status
    if gcloud services list --enabled --project="$PROJECT_ID" | grep -q "aiplatform.googleapis.com"; then
        print_success "✓ Vertex AI API is enabled"
    else
        print_error "✗ Vertex AI API is not enabled"
    fi

    # Check permissions
    ROLES=$(gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:$SERVICE_ACCOUNT" \
        --format="value(bindings.role)")

    if echo "$ROLES" | grep -q "aiplatform.user"; then
        print_success "✓ Service account has Vertex AI permissions"
    else
        print_error "✗ Service account missing Vertex AI permissions"
    fi

    # Step 7: Display next steps
    echo ""
    echo -e "${GREEN}==============================================================================
Setup Complete!
==============================================================================${NC}"
    echo ""
    echo "Summary:"
    echo "  • Vertex AI API: Enabled"
    echo "  • Service Account: $SERVICE_ACCOUNT"
    echo "  • Permissions: Configured"
    echo "  • Models Created: $MODELS_CREATED"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "1. If models were not created automatically, create them manually:"
    echo "   ${BLUE}bq query --use_legacy_sql=false \"CREATE OR REPLACE MODEL ...\"${NC}"
    echo ""
    echo "2. Generate embeddings for documents:"
    echo "   ${BLUE}uv run bq-semgrep index --update${NC}"
    echo ""
    echo "3. Build vector index:"
    echo "   ${BLUE}uv run bq-semgrep index --rebuild${NC}"
    echo ""
    echo "4. Test semantic search:"
    echo "   ${BLUE}uv run bq-semgrep search \"your query\" --rerank${NC}"
    echo ""

    if [ $MODELS_CREATED -eq 0 ]; then
        echo -e "${YELLOW}IMPORTANT: Models could not be created automatically.${NC}"
        echo "This might be due to:"
        echo "  • Permissions still propagating (wait a few more minutes)"
        echo "  • Regional availability of models"
        echo "  • Quota limitations"
        echo ""
        echo "Try creating a model manually in BigQuery console or wait and retry."
    fi
}

# Run the setup
setup_vertex_ai "$@"