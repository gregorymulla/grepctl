#!/usr/bin/env python3
"""
Create comprehensive diagram showing the complete data pipeline:
Data Lake → Ingestion → Google Cloud APIs → Search Corpus
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.gcp.storage import GCS, Filestore
from diagrams.gcp.analytics import BigQuery, Dataflow, Dataproc
from diagrams.gcp.ml import AIHub, AutoML, VisionAPI, SpeechToText, NaturalLanguageAPI
from diagrams.gcp.compute import Functions, Run
from diagrams.gcp.api import Endpoints, APIGateway
from diagrams.gcp.database import SQL
from diagrams.gcp.devtools import Build, Tasks
from diagrams.programming.language import Python
from diagrams.programming.framework import React
from diagrams.onprem.client import User, Client
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL as GenericSQL
from diagrams.generic.compute import Rack
from diagrams.generic.blank import Blank

# Custom attributes
graph_attr = {
    "fontsize": "45",
    "bgcolor": "white",
    "pad": "1.0",
    "nodesep": "1.2",
    "ranksep": "2.5",
    "splines": "ortho",
    "compound": "true",
    "concentrate": "false"
}

node_attr = {
    "fontsize": "11",
    "fontname": "Arial",
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "lightblue"
}

# Main comprehensive pipeline diagram
with Diagram("BigQuery Semantic Grep: Complete Data Pipeline",
             filename="data_pipeline_complete",
             show=False,
             direction="LR",
             graph_attr=graph_attr,
             node_attr=node_attr):

    # ============ DATA LAKE ============
    with Cluster("1. GCS DATA LAKE", graph_attr={"bgcolor": "#E3F2FD", "style": "rounded,bold", "penwidth": "2"}):

        gcs_main = GCS("gcm-data-lake\n425+ files")

        with Cluster("Document Types (8 Modalities)"):
            # First row
            text_files = Storage("📄 Text Files\n.txt, .log\n~50 files")
            markdown_files = Storage("📝 Markdown\n.md\n~30 files")
            pdf_files = Storage("📑 PDF Docs\n.pdf\n~31 files")
            image_files = Storage("🖼️ Images\n.jpg, .png\n~100 files")

            # Second row
            json_files = Storage("📊 JSON Data\n.json, .jsonl\n~52 files")
            csv_files = Storage("📈 CSV Tables\n.csv, .tsv\n~45 files")
            audio_files = Storage("🎵 Audio\n.mp3, .wav\n~62 files")
            video_files = Storage("🎬 Video\n.mp4, .avi\n~55 files")

    # ============ INGESTION LAYER ============
    with Cluster("2. INGESTION & EXTRACTION", graph_attr={"bgcolor": "#F3E5F5", "style": "rounded,bold", "penwidth": "2"}):

        with Cluster("Ingestion Scripts"):
            ingest_controller = Python("grepctl\norchestrator")

            with Cluster("Modality Processors"):
                text_processor = Python("Text/Markdown\nProcessor\n• Direct read\n• UTF-8 decode")
                pdf_processor = Python("PDF Processor\n• PyPDF2 extract\n• Document AI OCR")
                image_processor = Python("Image Processor\n• Vision API\n• Feature extraction")
                audio_processor = Python("Audio Processor\n• Speech-to-Text\n• Transcription")
                video_processor = Python("Video Processor\n• Frame analysis\n• Audio extraction")
                structured_processor = Python("JSON/CSV\nProcessor\n• Parse & flatten")

    # ============ GOOGLE CLOUD APIs ============
    with Cluster("3. GOOGLE CLOUD AI/ML APIs", graph_attr={"bgcolor": "#FFF3E0", "style": "rounded,bold", "penwidth": "2"}):

        with Cluster("Document Processing"):
            vision_api = VisionAPI("Vision API\n━━━━━━━━━\n• Label detection\n• OCR\n• Object detection\n• Face detection\n• Color analysis")

            document_ai = AutoML("Document AI\n━━━━━━━━━\n• PDF OCR\n• Form parsing\n• Table extraction\n• Layout analysis")

        with Cluster("Media Processing"):
            speech_api = SpeechToText("Speech-to-Text\n━━━━━━━━━\n• Transcription\n• Punctuation\n• Speaker labels\n• Timestamps")

            video_intel = Endpoints("Video Intelligence\n━━━━━━━━━\n• Shot detection\n• Label detection\n• Speech transcription\n• Object tracking")

        with Cluster("Embedding Generation"):
            vertex_ai = AIHub("Vertex AI\n━━━━━━━━━\ntext-embedding-004\n• 768 dimensions\n• Multilingual\n• Batch processing")

    # ============ PROCESSING & TRANSFORMATION ============
    with Cluster("4. CONTENT PROCESSING", graph_attr={"bgcolor": "#E8F5E9", "style": "rounded,bold", "penwidth": "2"}):

        with Cluster("Text Processing"):
            extract = Tasks("Content Extraction\n━━━━━━━━━\n• Parse responses\n• Clean text\n• Remove noise")

            transform = Build("Transformation\n━━━━━━━━━\n• Normalize format\n• Add metadata\n• Chunk if needed")

            enrich = Functions("Enrichment\n━━━━━━━━━\n• Add timestamps\n• Add source info\n• Add modality tags")

    # ============ BIGQUERY STORAGE ============
    with Cluster("5. BIGQUERY SEARCH CORPUS", graph_attr={"bgcolor": "#FFEBEE", "style": "rounded,bold", "penwidth": "2"}):

        with Cluster("Main Table"):
            search_corpus = BigQuery("search_corpus\n━━━━━━━━━━━━━━━")

            schema = GenericSQL("""Column Schema:
━━━━━━━━━━━━
• uri (STRING)
  gs://bucket/path

• modality (STRING)
  text|pdf|images|audio|video

• source (STRING)
  file type identifier

• text_content (STRING)
  Extracted/processed text

• embedding (ARRAY<FLOAT64>)
  768-dimensional vector

• metadata (JSON)
  {title, date, processing_info}

• created_at (TIMESTAMP)
  Processing timestamp""")

        with Cluster("Statistics"):
            stats = GenericSQL("""Current Status:
━━━━━━━━━━━
Total: 425+ documents
• Text/MD: 80 docs
• PDF: 31 docs (16 extracted)
• Images: 100 docs (analyzed)
• Audio: 62 docs
• Video: 55 docs
• JSON/CSV: 97 docs

Embeddings: 400+ generated
Avg content: 2,500 chars
Storage: ~500MB""")

    # ============ SEARCH INTERFACE ============
    with Cluster("6. SEMANTIC SEARCH", graph_attr={"bgcolor": "#E0F2F1", "style": "rounded,bold", "penwidth": "2"}):

        vector_search = BigQuery("VECTOR_SEARCH\n━━━━━━━━━\nCosine similarity\nTop-K ranking")

        search_cli = Python("bq-semgrep search\n& grepctl search")

        results = Client("Search Results\n• Ranked by relevance\n• Cross-modal\n• Sub-second response")

    # ================ CONNECTIONS ================

    # Data Lake connections
    gcs_main >> Edge(style="dotted") >> text_files
    gcs_main >> Edge(style="dotted") >> markdown_files
    gcs_main >> Edge(style="dotted") >> pdf_files
    gcs_main >> Edge(style="dotted") >> image_files
    gcs_main >> Edge(style="dotted") >> json_files
    gcs_main >> Edge(style="dotted") >> csv_files
    gcs_main >> Edge(style="dotted") >> audio_files
    gcs_main >> Edge(style="dotted") >> video_files

    # Files to processors
    text_files >> Edge(color="blue", label="read") >> text_processor
    markdown_files >> Edge(color="blue") >> text_processor
    pdf_files >> Edge(color="blue", label="extract") >> pdf_processor
    image_files >> Edge(color="blue", label="analyze") >> image_processor
    json_files >> Edge(color="blue", label="parse") >> structured_processor
    csv_files >> Edge(color="blue") >> structured_processor
    audio_files >> Edge(color="blue", label="transcribe") >> audio_processor
    video_files >> Edge(color="blue", label="process") >> video_processor

    # Controller orchestration
    ingest_controller >> Edge(style="dashed", color="gray") >> text_processor
    ingest_controller >> Edge(style="dashed", color="gray") >> pdf_processor
    ingest_controller >> Edge(style="dashed", color="gray") >> image_processor
    ingest_controller >> Edge(style="dashed", color="gray") >> audio_processor
    ingest_controller >> Edge(style="dashed", color="gray") >> video_processor
    ingest_controller >> Edge(style="dashed", color="gray") >> structured_processor

    # Processors to APIs
    pdf_processor >> Edge(color="orange", label="OCR") >> document_ai
    image_processor >> Edge(color="orange", label="analyze") >> vision_api
    audio_processor >> Edge(color="orange", label="transcribe") >> speech_api
    video_processor >> Edge(color="orange", label="analyze") >> video_intel

    # APIs to processing
    document_ai >> Edge(color="green") >> extract
    vision_api >> Edge(color="green") >> extract
    speech_api >> Edge(color="green") >> extract
    video_intel >> Edge(color="green") >> extract
    text_processor >> Edge(color="green") >> extract
    structured_processor >> Edge(color="green") >> extract

    # Processing pipeline
    extract >> Edge() >> transform
    transform >> Edge() >> enrich

    # To BigQuery
    enrich >> Edge(color="red", label="insert", style="bold") >> search_corpus
    search_corpus >> Edge(style="dotted") >> schema
    search_corpus >> Edge(style="dotted") >> stats

    # Embedding generation
    search_corpus >> Edge(color="purple", label="generate\nembeddings") >> vertex_ai
    vertex_ai >> Edge(color="purple", label="768-dim\nvectors") >> search_corpus

    # Search flow
    search_corpus >> Edge(color="darkgreen") >> vector_search
    vector_search >> Edge(color="darkgreen") >> search_cli
    search_cli >> Edge(color="darkgreen") >> results


# Simplified flow diagram focusing on key steps
with Diagram("Data Pipeline: Simplified Flow",
             filename="data_pipeline_simple",
             show=False,
             direction="TB",
             graph_attr={"fontsize": "40", "bgcolor": "white", "pad": "0.8"}):

    with Cluster("DATA LAKE", graph_attr={"bgcolor": "#E3F2FD"}):
        lake = GCS("GCS Bucket\ngcm-data-lake")
        docs = Storage("8 Modalities\n425+ files")

    with Cluster("INGESTION", graph_attr={"bgcolor": "#F3E5F5"}):
        ingest = Python("grepctl\n6 processors")

    with Cluster("GOOGLE APIS", graph_attr={"bgcolor": "#FFF3E0"}):
        apis = Endpoints("5 AI/ML APIs\n• Vision\n• Document AI\n• Speech\n• Video\n• Vertex AI")

    with Cluster("PROCESSING", graph_attr={"bgcolor": "#E8F5E9"}):
        process = Functions("Extract\nTransform\nEnrich")

    with Cluster("BIGQUERY", graph_attr={"bgcolor": "#FFEBEE"}):
        bq = BigQuery("search_corpus\n425+ docs")
        embeddings = AIHub("768-dim\nembeddings")

    with Cluster("SEARCH", graph_attr={"bgcolor": "#E0F2F1"}):
        search = Python("Semantic\nSearch")

    # Flow
    lake >> docs >> Edge(label="read", style="bold") >> ingest
    ingest >> Edge(label="call", style="bold") >> apis
    apis >> Edge(label="extract", style="bold") >> process
    process >> Edge(label="store", style="bold") >> bq
    bq >> Edge(label="embed", color="purple", style="bold") >> embeddings
    embeddings >> Edge(color="purple", style="dashed") >> bq
    bq >> Edge(label="query", color="green", style="bold") >> search


# API usage detail diagram
with Diagram("Google Cloud API Integration Details",
             filename="api_integration_detail",
             show=False,
             direction="LR",
             graph_attr={"fontsize": "35", "bgcolor": "white"}):

    with Cluster("Input Files", graph_attr={"bgcolor": "#F5F5F5"}):
        pdf_in = Storage("PDF Files")
        img_in = Storage("Image Files")
        audio_in = Storage("Audio Files")
        video_in = Storage("Video Files")

    with Cluster("API Processing", graph_attr={"bgcolor": "#FFF8E1"}):

        with Cluster("Vision API"):
            vision_features = VisionAPI("""Features:
• LABEL_DETECTION
• TEXT_DETECTION
• OBJECT_LOCALIZATION
• IMAGE_PROPERTIES
• FACE_DETECTION""")

        with Cluster("Document AI"):
            doc_features = AutoML("""Capabilities:
• OCR_PROCESSOR
• FORM_PARSER
• TABLE_EXTRACTOR
• LAYOUT_PARSER""")

        with Cluster("Speech-to-Text"):
            speech_features = SpeechToText("""Config:
• Language: en-US
• Punctuation: ON
• Model: latest_long
• Sample rate: 16kHz""")

        with Cluster("Video Intelligence"):
            video_features = Endpoints("""Analysis:
• SHOT_DETECTION
• LABEL_DETECTION
• SPEECH_TRANSCRIPTION
• OBJECT_TRACKING""")

    with Cluster("Output Format", graph_attr={"bgcolor": "#E8F5E9"}):

        vision_out = GenericSQL("""Vision Output:
{
  labels: [...],
  text: "extracted",
  objects: [...],
  colors: [...],
  faces: count
}""")

        doc_out = GenericSQL("""Document Output:
{
  text: "full content",
  pages: [...],
  tables: [...],
  confidence: 0.95
}""")

        speech_out = GenericSQL("""Speech Output:
{
  transcript: "...",
  words: [...],
  confidence: 0.92
}""")

        video_out = GenericSQL("""Video Output:
{
  shots: [...],
  labels: [...],
  transcript: "...",
  objects: [...]
}""")

    with Cluster("BigQuery Storage", graph_attr={"bgcolor": "#FFEBEE"}):
        final_storage = BigQuery("search_corpus\nUnified format")

    # Connections
    pdf_in >> Edge(label="process") >> doc_features >> Edge(label="extract") >> doc_out
    img_in >> Edge(label="analyze") >> vision_features >> Edge(label="extract") >> vision_out
    audio_in >> Edge(label="transcribe") >> speech_features >> Edge(label="convert") >> speech_out
    video_in >> Edge(label="analyze") >> video_features >> Edge(label="extract") >> video_out

    vision_out >> Edge(color="red") >> final_storage
    doc_out >> Edge(color="red") >> final_storage
    speech_out >> Edge(color="red") >> final_storage
    video_out >> Edge(color="red") >> final_storage


print("✅ Data pipeline diagrams generated:")
print("  - data_pipeline_complete.png - Comprehensive pipeline from data lake to search")
print("  - data_pipeline_simple.png - Simplified vertical flow")
print("  - api_integration_detail.png - Detailed Google Cloud API integration")
print("\nThese diagrams show the complete data flow:")
print("  Data Lake (425+ files) → Ingestion (6 processors) → Google APIs (5 services)")
print("  → Processing → BigQuery (search_corpus) → Embeddings → Semantic Search")