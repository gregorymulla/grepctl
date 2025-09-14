#!/usr/bin/env python3
"""
Generate architecture diagram showing the BigQuery Semantic Grep data flow.
From data lake with multiple document types to searchable index.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.gcp.storage import GCS
from diagrams.gcp.analytics import BigQuery, Dataflow
from diagrams.gcp.ml import AIHub, AutoML, NaturalLanguageAPI, VisionAPI, SpeechToText
from diagrams.gcp.compute import Functions
from diagrams.programming.language import Python
from diagrams.generic.blank import Blank
from diagrams.onprem.client import User, Client
from diagrams.generic.storage import Storage
from diagrams.gcp.api import Endpoints

# Custom attributes for the diagram
graph_attr = {
    "fontsize": "45",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.8",
    "ranksep": "1.5",
    "splines": "ortho"
}

node_attr = {
    "fontsize": "12",
    "fontname": "Arial",
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "lightblue"
}

with Diagram("BigQuery Semantic Grep Architecture",
             filename="bq_semgrep_architecture",
             show=False,
             direction="LR",
             graph_attr=graph_attr,
             node_attr=node_attr):

    # User interaction
    user = User("User")

    with Cluster("Data Lake (GCS)"):
        gcs_bucket = GCS("gcm-data-lake")

        with Cluster("Document Types"):
            # Row 1
            text_files = Storage("Text/Markdown\n(.txt, .md)")
            pdf_files = Storage("PDF Documents\n(.pdf)")
            image_files = Storage("Images\n(.jpg, .png)")
            json_files = Storage("Structured Data\n(.json, .csv)")

            # Row 2
            audio_files = Storage("Audio Files\n(.mp3, .wav)")
            video_files = Storage("Video Files\n(.mp4, .avi)")

    with Cluster("Processing Pipeline", graph_attr={"style": "dashed", "color": "blue"}):

        with Cluster("grepctl CLI"):
            grepctl = Python("grepctl.py")

        with Cluster("Ingestion Scripts"):
            ingest_text = Python("bq-semgrep\ningest")
            ingest_pdf = Python("extract_pdfs\n_hybrid.py")
            ingest_image = Python("complete_vision\n_analysis.py")
            ingest_json = Python("ingest_json\n_csv.py")
            ingest_audio = Python("ingest_audio\n_files.py")
            ingest_video = Python("ingest_video\n_files.py")

    with Cluster("Google Cloud APIs", graph_attr={"style": "dotted", "color": "green"}):
        with Cluster("AI/ML Services"):
            vertex_ai = AIHub("Vertex AI\nEmbeddings")
            vision_api = VisionAPI("Vision API")
            document_ai = AutoML("Document AI")
            speech_api = SpeechToText("Speech-to-Text")
            video_intel = Endpoints("Video\nIntelligence")

    with Cluster("BigQuery", graph_attr={"style": "solid", "color": "orange"}):

        with Cluster("Dataset: mmgrep"):
            search_corpus = BigQuery("search_corpus\n(main table)")

        with Cluster("ML Models"):
            embedding_model = BigQuery("text_embedding\n_model")

        with Cluster("Search"):
            vector_search = BigQuery("VECTOR_SEARCH\nfunction")

    with Cluster("Search Interface"):
        search_cli = Python("bq-semgrep\nsearch")
        fix_script = Python("fix_embeddings.py")
        status_script = Python("show_status.py")

    # Results
    results = Client("Search Results\n(Table/JSON/CSV)")

    # ==== Data Flow Connections ====

    # User initiates
    user >> Edge(label="grepctl init all\n--auto-ingest", style="bold") >> grepctl

    # GCS to document types
    gcs_bucket >> Edge(color="darkblue") >> text_files
    gcs_bucket >> Edge(color="darkblue") >> pdf_files
    gcs_bucket >> Edge(color="darkblue") >> image_files
    gcs_bucket >> Edge(color="darkblue") >> json_files
    gcs_bucket >> Edge(color="darkblue") >> audio_files
    gcs_bucket >> Edge(color="darkblue") >> video_files

    # grepctl orchestrates ingestion
    grepctl >> Edge(label="orchestrate", style="dashed") >> ingest_text
    grepctl >> Edge(style="dashed") >> ingest_pdf
    grepctl >> Edge(style="dashed") >> ingest_image
    grepctl >> Edge(style="dashed") >> ingest_json
    grepctl >> Edge(style="dashed") >> ingest_audio
    grepctl >> Edge(style="dashed") >> ingest_video

    # Document types to ingestion scripts
    text_files >> Edge(color="blue") >> ingest_text
    pdf_files >> Edge(color="blue") >> ingest_pdf
    image_files >> Edge(color="blue") >> ingest_image
    json_files >> Edge(color="blue") >> ingest_json
    audio_files >> Edge(color="blue") >> ingest_audio
    video_files >> Edge(color="blue") >> ingest_video

    # Ingestion scripts to APIs
    ingest_pdf >> Edge(label="OCR", color="green") >> document_ai
    ingest_image >> Edge(label="analyze", color="green") >> vision_api
    ingest_audio >> Edge(label="transcribe", color="green") >> speech_api
    ingest_video >> Edge(label="analyze", color="green") >> video_intel

    # All ingestion to search_corpus
    ingest_text >> Edge(color="orange") >> search_corpus
    ingest_pdf >> Edge(color="orange") >> search_corpus
    ingest_image >> Edge(color="orange") >> search_corpus
    ingest_json >> Edge(color="orange") >> search_corpus
    ingest_audio >> Edge(color="orange") >> search_corpus
    ingest_video >> Edge(color="orange") >> search_corpus

    # APIs to search_corpus
    document_ai >> Edge(style="dotted", color="green") >> search_corpus
    vision_api >> Edge(style="dotted", color="green") >> search_corpus
    speech_api >> Edge(style="dotted", color="green") >> search_corpus
    video_intel >> Edge(style="dotted", color="green") >> search_corpus

    # Embedding generation
    search_corpus >> Edge(label="generate\nembeddings", color="purple") >> vertex_ai
    vertex_ai >> Edge(color="purple") >> embedding_model
    embedding_model >> Edge(label="768-dim\nvectors", color="purple") >> search_corpus

    # Fix and maintenance
    grepctl >> Edge(label="fix", style="dashed") >> fix_script
    fix_script >> Edge(label="repair", color="red") >> search_corpus

    # Search flow
    search_corpus >> Edge(color="darkgreen") >> vector_search
    user >> Edge(label="grepctl search\n'query'", style="bold") >> search_cli
    search_cli >> Edge(color="darkgreen") >> vector_search
    vector_search >> Edge(label="semantic\nresults", color="darkgreen") >> results

    # Status monitoring
    grepctl >> Edge(label="status", style="dashed") >> status_script
    status_script >> Edge(style="dotted") >> search_corpus
    status_script >> Edge(style="dotted") >> user


# Create a simplified flow diagram
with Diagram("BigQuery Semantic Grep - Data Flow",
             filename="bq_semgrep_flow",
             show=False,
             direction="TB",
             graph_attr={"fontsize": "40", "bgcolor": "white", "pad": "0.5"}):

    with Cluster("1. Data Sources"):
        data_lake = GCS("GCS Data Lake")
        docs = Storage("8 Modalities\n• Text/Markdown\n• PDF • Images\n• JSON/CSV\n• Audio • Video")

    with Cluster("2. Processing"):
        grepctl_main = Python("grepctl CLI")
        apis = AIHub("Google Cloud APIs\n• Vision • Document AI\n• Speech • Video Intel")

    with Cluster("3. Storage & Indexing"):
        bigquery = BigQuery("BigQuery Dataset")
        embeddings = AIHub("Vertex AI\nEmbeddings")

    with Cluster("4. Search"):
        search = Python("Semantic Search")
        output = Client("Results")

    # Flow
    data_lake >> Edge(label="multimodal\nfiles") >> docs
    docs >> Edge(label="ingest", style="bold") >> grepctl_main
    grepctl_main >> Edge(label="process") >> apis
    apis >> Edge(label="extract\ncontent") >> bigquery
    bigquery >> Edge(label="generate\n768-dim vectors") >> embeddings
    embeddings >> Edge(label="store") >> bigquery
    bigquery >> Edge(label="VECTOR_SEARCH") >> search
    search >> Edge(label="ranked\nresults") >> output


# Create a command workflow diagram
with Diagram("grepctl Command Workflow",
             filename="grepctl_workflow",
             show=False,
             direction="LR",
             graph_attr={"fontsize": "35", "bgcolor": "white"}):

    start = User("Start")

    with Cluster("Initialization"):
        init_all = Python("grepctl init all\n--auto-ingest")
        enable_apis = Functions("Enable APIs")
        create_dataset = BigQuery("Create Dataset")
        create_models = AIHub("Create Models")

    with Cluster("Data Processing"):
        ingest_all = Python("grepctl ingest all")
        process_modalities = Storage("Process\n8 Modalities")

    with Cluster("Indexing"):
        update_index = Python("grepctl index update")
        fix_embeddings = Python("grepctl fix\nembeddings")

    with Cluster("Usage"):
        check_status = Python("grepctl status")
        search_data = Python("grepctl search\n'query'")

    end = Client("Results")

    # Workflow
    start >> Edge(label="one command", style="bold", color="green") >> init_all
    init_all >> enable_apis >> create_dataset >> create_models
    create_models >> ingest_all >> process_modalities
    process_modalities >> update_index
    update_index >> Edge(label="if needed") >> fix_embeddings
    fix_embeddings >> check_status
    update_index >> check_status
    check_status >> search_data >> end


print("✅ Architecture diagrams generated:")
print("  - bq_semgrep_architecture.png - Complete system architecture")
print("  - bq_semgrep_flow.png - Simplified data flow")
print("  - grepctl_workflow.png - Command workflow")
print("\nTo view the diagrams, open the generated PNG files.")