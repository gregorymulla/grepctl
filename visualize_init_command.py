#!/usr/bin/env python3
"""
Create detailed diagram showing what happens when running:
grepctl init all --auto-ingest

Focus on BigQuery tables, models, APIs, and Vertex AI integration.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.gcp.storage import GCS
from diagrams.gcp.analytics import BigQuery, Dataproc, PubSub
from diagrams.gcp.ml import AIHub, AutoML, VisionAPI, SpeechToText, NaturalLanguageAPI
from diagrams.gcp.compute import Functions, Run
from diagrams.gcp.api import Endpoints, APIGateway
from diagrams.gcp.database import SQL, Bigtable
from diagrams.gcp.devtools import Build, Tasks
from diagrams.programming.language import Python
from diagrams.onprem.client import User
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL as GenericSQL

# Custom attributes
graph_attr = {
    "fontsize": "45",
    "bgcolor": "white",
    "pad": "0.8",
    "nodesep": "1.0",
    "ranksep": "2.0",
    "splines": "ortho",
    "compound": "true"
}

node_attr = {
    "fontsize": "11",
    "fontname": "Arial",
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "lightblue"
}

with Diagram("grepctl init all --auto-ingest: Detailed Architecture",
             filename="grepctl_init_detailed",
             show=False,
             direction="TB",
             graph_attr=graph_attr,
             node_attr=node_attr):

    # User command
    user = User("User")

    with Cluster("Command Execution", graph_attr={"bgcolor": "lightyellow", "style": "dashed"}):
        grepctl_cmd = Python("grepctl init all\n--bucket gcm-data-lake\n--auto-ingest")

    # Phase 1: API Enablement
    with Cluster("Phase 1: Enable Google Cloud APIs", graph_attr={"bgcolor": "lightcyan"}):
        with Cluster("Required APIs (7)"):
            apis = [
                Endpoints("bigquery.googleapis.com"),
                Endpoints("aiplatform.googleapis.com"),
                VisionAPI("vision.googleapis.com"),
                Endpoints("documentai.googleapis.com"),
                SpeechToText("speech.googleapis.com"),
                Endpoints("videointelligence.googleapis.com"),
                GCS("storage.googleapis.com")
            ]

    # Phase 2: BigQuery Setup
    with Cluster("Phase 2: BigQuery Infrastructure", graph_attr={"bgcolor": "lavender"}):

        with Cluster("Dataset: semgrep-472018.mmgrep"):
            dataset = BigQuery("mmgrep dataset\nLocation: US\nDescription: Multimodal grep")

        with Cluster("Core Tables"):
            search_corpus = GenericSQL("search_corpus\n━━━━━━━━━━━\n• uri (STRING)\n• modality (STRING)\n• source (STRING)\n• text_content (STRING)\n• embedding (ARRAY<FLOAT64>)\n• metadata (JSON)\n• created_at (TIMESTAMP)")

            external_files = GenericSQL("external_files\n━━━━━━━━━━━\n• uri (STRING)\n• size_bytes (INT64)\n• content_type (STRING)\n• last_modified (TIMESTAMP)")

            processing_log = GenericSQL("processing_log\n━━━━━━━━━━━\n• job_id (STRING)\n• modality (STRING)\n• status (STRING)\n• error_message (STRING)\n• processed_at (TIMESTAMP)")

    # Phase 3: Vertex AI Models
    with Cluster("Phase 3: Vertex AI Model Setup", graph_attr={"bgcolor": "mistyrose"}):

        with Cluster("Connection Configuration"):
            vertex_connection = APIGateway("vertex-ai-connection\nLocation: US\nType: CLOUD_RESOURCE")

        with Cluster("ML Models"):
            embedding_model = AIHub("text_embedding_model\n━━━━━━━━━━━━━\nREMOTE MODEL\nEndpoint: text-embedding-004\n768 dimensions\nMultilingual support")

            text_model = AIHub("text_model\n━━━━━━━━━━━━━\nREMOTE MODEL\nEndpoint: gemini-1.5-pro\nContext: 2M tokens\nMultimodal capable")

            vision_model = AIHub("vision_model\n━━━━━━━━━━━━━\nREMOTE MODEL\nEndpoint: gemini-1.5-flash\nImage understanding\nOCR + analysis")

    # Phase 4: Data Ingestion
    with Cluster("Phase 4: Auto-Ingestion Pipeline", graph_attr={"bgcolor": "lightgreen"}):

        with Cluster("GCS Data Lake"):
            gcs_bucket = GCS("gcm-data-lake\n425+ files\n8 modalities")

        with Cluster("Ingestion Scripts"):
            ingest_text = Python("Text/Markdown\nDirect extraction")
            ingest_pdf = Python("PDF Documents\nDocument AI + PyPDF2")
            ingest_images = Python("Images\nVision API analysis")
            ingest_audio = Python("Audio\nSpeech-to-Text")
            ingest_video = Python("Video\nVideo Intelligence")
            ingest_json = Python("JSON/CSV\nStructured parsing")

    # Phase 5: Processing & Embeddings
    with Cluster("Phase 5: Content Processing", graph_attr={"bgcolor": "wheat"}):

        with Cluster("Content Extraction"):
            extract = Tasks("Extract & Transform\n• Parse documents\n• Clean text\n• Extract metadata\n• Chunk content")

        with Cluster("Embedding Generation"):
            embeddings = Build("Generate Embeddings\n• Batch processing\n• 768-dim vectors\n• Cosine similarity\n• Semantic understanding")

    # Phase 6: Search Configuration
    with Cluster("Phase 6: Search Setup", graph_attr={"bgcolor": "lightsteelblue"}):

        with Cluster("Vector Search"):
            vector_search = BigQuery("VECTOR_SEARCH\n━━━━━━━━━━━━━\nFunction: VECTOR_SEARCH\nDistance: COSINE\nTop-K: configurable\nNo index needed (<5K docs)")

        with Cluster("Search Functions"):
            sql_functions = GenericSQL("SQL Functions\n━━━━━━━━━━━━━\n• ML.GENERATE_EMBEDDING\n• VECTOR_SEARCH\n• COSINE_DISTANCE\n• APPROX_TOP_K")

    # Result
    with Cluster("System Ready", graph_attr={"bgcolor": "lightgreen", "style": "bold"}):
        ready = Storage("✓ APIs Enabled\n✓ Dataset Created\n✓ Tables Ready\n✓ Models Deployed\n✓ Data Ingested\n✓ Embeddings Generated\n✓ Search Operational")

    # === Data Flow Connections ===

    # User initiates
    user >> Edge(label="executes", style="bold", color="darkgreen") >> grepctl_cmd

    # Phase 1: Enable APIs
    grepctl_cmd >> Edge(label="1. Enable APIs\n(gcloud services enable)", color="blue") >> apis[0]

    # Phase 2: Create BigQuery infrastructure
    apis[0] >> Edge(label="2. Create Dataset", color="purple") >> dataset
    dataset >> Edge(label="create tables", style="dashed") >> search_corpus
    dataset >> Edge(style="dashed") >> external_files
    dataset >> Edge(style="dashed") >> processing_log

    # Phase 3: Setup Vertex AI
    dataset >> Edge(label="3. Configure Vertex AI", color="red") >> vertex_connection
    vertex_connection >> Edge(label="create models", style="dashed") >> embedding_model
    vertex_connection >> Edge(style="dashed") >> text_model
    vertex_connection >> Edge(style="dashed") >> vision_model

    # Phase 4: Auto-ingestion
    embedding_model >> Edge(label="4. Start Ingestion", color="green") >> gcs_bucket
    gcs_bucket >> Edge(style="dashed") >> ingest_text
    gcs_bucket >> Edge(style="dashed") >> ingest_pdf
    gcs_bucket >> Edge(style="dashed") >> ingest_images
    gcs_bucket >> Edge(style="dashed") >> ingest_audio
    gcs_bucket >> Edge(style="dashed") >> ingest_video
    gcs_bucket >> Edge(style="dashed") >> ingest_json

    # All ingestion to extraction
    ingest_text >> Edge(color="orange") >> extract
    ingest_pdf >> Edge(color="orange") >> extract
    ingest_images >> Edge(color="orange") >> extract
    ingest_audio >> Edge(color="orange") >> extract
    ingest_video >> Edge(color="orange") >> extract
    ingest_json >> Edge(color="orange") >> extract

    # Phase 5: Generate embeddings
    extract >> Edge(label="5. Generate\nEmbeddings", color="purple") >> embeddings
    embeddings >> Edge(label="store in\nBigQuery", style="dashed") >> search_corpus

    # Phase 6: Configure search
    embeddings >> Edge(label="6. Setup Search", color="brown") >> vector_search
    vector_search >> Edge(style="dashed") >> sql_functions

    # Final result
    sql_functions >> Edge(label="System Ready", style="bold", color="green") >> ready


# Create a second diagram showing the BigQuery schema details
with Diagram("BigQuery Schema & Model Details",
             filename="bq_schema_models",
             show=False,
             direction="LR",
             graph_attr={"fontsize": "40", "bgcolor": "white", "pad": "0.5"}):

    with Cluster("BigQuery Dataset: mmgrep", graph_attr={"bgcolor": "lavender"}):

        with Cluster("Main Table: search_corpus"):
            schema = GenericSQL("""search_corpus (425+ rows)
━━━━━━━━━━━━━━━━━━━
COLUMNS:
• uri: STRING (PRIMARY KEY)
  gs://bucket/path/file.ext

• modality: STRING
  text|markdown|pdf|images|
  audio|video|json|csv

• source: STRING
  file|api|manual|scraped

• text_content: STRING
  Extracted/processed content
  AVG: 2,500 chars

• embedding: ARRAY<FLOAT64>
  768 dimensions
  text-embedding-004

• metadata: JSON
  {title, author, date,
   tags, processing_info}

• created_at: TIMESTAMP
  Processing timestamp""")

        with Cluster("Supporting Tables"):
            tables = GenericSQL("""external_files
━━━━━━━━━━━━
• GCS file registry
• Size & type tracking
• Last modified dates

processing_log
━━━━━━━━━━━━
• Job tracking
• Error logging
• Performance metrics

embeddings_cache
━━━━━━━━━━━━
• Cached embeddings
• Query history
• Relevance scores""")

    with Cluster("Vertex AI Models", graph_attr={"bgcolor": "mistyrose"}):

        with Cluster("Embedding Model"):
            embed_detail = AIHub("""text_embedding_model
━━━━━━━━━━━━━━━━━
Model: text-embedding-004
• 768-dimensional vectors
• Multilingual (100+ langs)
• Context: 2,048 tokens
• Batch size: 100
• QPS limit: 600/min

SQL Usage:
SELECT
  ML.GENERATE_EMBEDDING(
    MODEL `text_embedding_model`,
    (SELECT text_content AS content),
    STRUCT(TRUE AS flatten_json_output)
  ) AS embedding
FROM corpus""")

        with Cluster("Generation Models"):
            gen_models = AIHub("""text_model (Gemini 1.5 Pro)
━━━━━━━━━━━━━━━━━
• Context: 2M tokens
• Multimodal input
• JSON mode support
• Function calling

vision_model (Gemini 1.5 Flash)
━━━━━━━━━━━━━━━━━
• Image analysis
• OCR capability
• Object detection
• Scene understanding""")

    with Cluster("Vector Search Configuration", graph_attr={"bgcolor": "lightgreen"}):

        search_config = BigQuery("""VECTOR_SEARCH Configuration
━━━━━━━━━━━━━━━━━━━━
No index required (<5K docs)

Direct search:
SELECT uri, text_content,
  VECTOR_SEARCH(
    TABLE `search_corpus`,
    'embedding',
    (SELECT embedding FROM query),
    top_k => 20,
    distance_type => 'COSINE'
  ).distance AS score
FROM search_corpus
ORDER BY score DESC

Performance:
• Sub-second queries
• No maintenance needed
• Auto-scaling""")

    # Connections
    schema >> Edge(label="embeddings via", style="dashed") >> embed_detail
    embed_detail >> Edge(label="enables", style="dashed") >> search_config
    gen_models >> Edge(label="enhances", style="dashed") >> search_config


# Create a third diagram showing the complete initialization timeline
with Diagram("Initialization Timeline & Resource Creation",
             filename="init_timeline",
             show=False,
             direction="TB",
             graph_attr={"fontsize": "35", "bgcolor": "white", "rankdir": "TB"}):

    start = User("START:\ngrepctl init all --auto-ingest")

    with Cluster("⏱️ T+0 to T+30 seconds", graph_attr={"bgcolor": "lightcyan"}):
        with Cluster("API Enablement"):
            enable_apis = Tasks("Enable 7 APIs\n━━━━━━━━━━━\n✓ BigQuery\n✓ Vertex AI\n✓ Vision\n✓ Document AI\n✓ Speech\n✓ Video Intel\n✓ Storage")

    with Cluster("⏱️ T+30 to T+60 seconds", graph_attr={"bgcolor": "lavender"}):
        with Cluster("BigQuery Setup"):
            create_dataset = BigQuery("Create Dataset\n━━━━━━━━━━━\nProject: semgrep-472018\nDataset: mmgrep\nLocation: US")
            create_tables = GenericSQL("Create 3 Tables\n━━━━━━━━━━━\n• search_corpus\n• external_files\n• processing_log")

    with Cluster("⏱️ T+60 to T+90 seconds", graph_attr={"bgcolor": "mistyrose"}):
        with Cluster("Model Deployment"):
            create_connection = APIGateway("Create Connection\n━━━━━━━━━━━\nvertex-ai-connection\nGrant IAM roles")
            deploy_models = AIHub("Deploy 3 Models\n━━━━━━━━━━━\n• text_embedding_model\n• text_model\n• vision_model")

    with Cluster("⏱️ T+90 to T+300 seconds", graph_attr={"bgcolor": "lightgreen"}):
        with Cluster("Data Ingestion"):
            scan_bucket = GCS("Scan Bucket\n━━━━━━━━━━━\nFind 425+ files\nCategorize by type")
            process_files = Python("Process Files\n━━━━━━━━━━━\n• Text: Direct\n• PDF: OCR\n• Images: Vision\n• Audio: Speech\n• Video: Analysis")

    with Cluster("⏱️ T+300 to T+600 seconds", graph_attr={"bgcolor": "wheat"}):
        with Cluster("Embedding Generation"):
            generate_embeddings = Build("Generate Embeddings\n━━━━━━━━━━━\n425+ documents\nBatch size: 100\n768-dim vectors")
            fix_issues = Python("Fix Issues\n━━━━━━━━━━━\n• Clear empty arrays\n• Fix dimensions\n• Retry failures")

    with Cluster("⏱️ T+600 seconds", graph_attr={"bgcolor": "lightgreen", "style": "bold"}):
        complete = Storage("✅ COMPLETE\n━━━━━━━━━━━\n• All APIs enabled\n• Dataset ready\n• 425+ docs indexed\n• Embeddings generated\n• Search operational\n\n$ grepctl search 'query'")

    # Timeline flow
    start >> Edge(label="0s", style="bold") >> enable_apis
    enable_apis >> Edge(label="30s", style="bold") >> create_dataset
    create_dataset >> Edge(style="dashed") >> create_tables
    create_tables >> Edge(label="60s", style="bold") >> create_connection
    create_connection >> Edge(style="dashed") >> deploy_models
    deploy_models >> Edge(label="90s", style="bold") >> scan_bucket
    scan_bucket >> Edge(style="dashed") >> process_files
    process_files >> Edge(label="5 min", style="bold") >> generate_embeddings
    generate_embeddings >> Edge(style="dashed") >> fix_issues
    fix_issues >> Edge(label="10 min", style="bold", color="green") >> complete


print("✅ Detailed initialization diagrams generated:")
print("  - grepctl_init_detailed.png - Complete init command architecture")
print("  - bq_schema_models.png - BigQuery tables and Vertex AI models")
print("  - init_timeline.png - Timeline of resource creation")
print("\nThese diagrams show exactly what happens during:")
print("  $ grepctl init all --bucket gcm-data-lake --auto-ingest")