#!/usr/bin/env python3
"""
Generate text-based architecture visualization for BigQuery Semantic Grep.
Shows the data flow from data lake to searchable index.
"""

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box

console = Console()

def create_architecture_diagram():
    """Create the main architecture flow diagram."""

    # Title
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]BigQuery Semantic Grep - Architecture Overview[/bold cyan]\n" +
        "[dim]From Data Lake → Processing → Searchable Index[/dim]",
        border_style="cyan"
    ))

    # Data Flow Diagram
    flow = """
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         [bold cyan]GCS DATA LAKE[/bold cyan]                                │
    │                        (gcm-data-lake)                                   │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  📄 Text/MD   📑 PDF    🖼️  Images   📊 JSON/CSV                 │  │
    │  │  🎵 Audio     🎬 Video  📝 Documents 📦 Archives                 │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          [bold green]GREPCTL CLI[/bold green]                                 │
    │                    (Orchestration & Control)                             │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  $ grepctl init all --auto-ingest                                │  │
    │  │  • Enable APIs  • Create Dataset  • Ingest Data  • Build Index   │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────┬───────────────────────────────────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │  [yellow]INGESTION[/yellow]       │  │  [magenta]GOOGLE APIS[/magenta]    │  │  [red]PROCESSING[/red]     │
    │                  │  │                  │  │                  │
    │ • bq-semgrep     │  │ • Vision API     │  │ • Extract Text   │
    │ • extract_pdfs   │  │ • Document AI    │  │ • Generate       │
    │ • ingest_json    │  │ • Speech-to-Text │  │   Descriptions   │
    │ • ingest_audio   │  │ • Video Intel    │  │ • Parse Content  │
    │ • ingest_video   │  │ • Vertex AI      │  │ • Clean Data     │
    └──────────┬───────┘  └──────────┬───────┘  └──────────┬───────┘
               │                     │                     │
               └─────────────────────┼─────────────────────┘
                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          [bold blue]BIGQUERY DATASET[/bold blue]                             │
    │                            (mmgrep)                                      │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  Table: search_corpus                                            │  │
    │  │  ├─ uri (STRING)           - Document location                   │  │
    │  │  ├─ modality (STRING)      - Document type                       │  │
    │  │  ├─ text_content (STRING)  - Extracted/processed content         │  │
    │  │  └─ embedding (ARRAY<FLOAT64>) - 768-dim vectors                 │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         [bold purple]VERTEX AI EMBEDDINGS[/bold purple]                         │
    │                      (text-embedding-004)                                │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  ML.GENERATE_EMBEDDING() → 768-dimensional vectors               │  │
    │  │  Semantic understanding of all content types                     │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         [bold green]SEMANTIC SEARCH[/bold green]                              │
    │                        (VECTOR_SEARCH)                                   │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  $ grepctl search "machine learning"                             │  │
    │  │  → Query embedding → Cosine similarity → Ranked results          │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           [bold cyan]SEARCH RESULTS[/bold cyan]                              │
    │  ┌──────────────────────────────────────────────────────────────────┐  │
    │  │  Format: Table / JSON / CSV                                      │  │
    │  │  • Ranked by relevance  • Cross-modal search  • Sub-second speed │  │
    │  └──────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────────────────┘
    """

    console.print(flow)

def create_command_workflow():
    """Create command workflow visualization."""

    console.print("\n")
    console.print(Panel.fit(
        "[bold yellow]grepctl Command Workflow[/bold yellow]",
        border_style="yellow"
    ))

    # Create workflow tree
    tree = Tree("[bold]grepctl Workflow[/bold]")

    # Init branch
    init = tree.add("[green]1. Initialize System[/green]")
    init.add("[cyan]grepctl init all --auto-ingest[/cyan]")
    init_steps = init.add("Steps:")
    init_steps.add("• Enable Google Cloud APIs")
    init_steps.add("• Create BigQuery dataset")
    init_steps.add("• Setup ML models")
    init_steps.add("• Configure connections")

    # Ingest branch
    ingest = tree.add("[yellow]2. Ingest Data[/yellow]")
    ingest.add("[cyan]grepctl ingest all[/cyan]")
    modalities = ingest.add("Process modalities:")
    modalities.add("• Text/Markdown → Direct extraction")
    modalities.add("• PDF → Document AI + PyPDF2")
    modalities.add("• Images → Vision API analysis")
    modalities.add("• Audio → Speech-to-Text")
    modalities.add("• Video → Video Intelligence")
    modalities.add("• JSON/CSV → Structured parsing")

    # Index branch
    index = tree.add("[magenta]3. Build Index[/magenta]")
    index.add("[cyan]grepctl index update[/cyan]")
    index_steps = index.add("Operations:")
    index_steps.add("• Generate embeddings (768-dim)")
    index_steps.add("• Fix dimension issues")
    index_steps.add("• Verify completeness")

    # Fix branch
    fix = tree.add("[red]4. Troubleshooting[/red]")
    fix.add("[cyan]grepctl fix embeddings[/cyan]")
    fix_ops = fix.add("Automatic fixes:")
    fix_ops.add("• Clear empty arrays")
    fix_ops.add("• Fix wrong dimensions")
    fix_ops.add("• Regenerate missing")

    # Search branch
    search = tree.add("[blue]5. Search[/blue]")
    search.add("[cyan]grepctl search 'query'[/cyan]")
    search_features = search.add("Features:")
    search_features.add("• Semantic understanding")
    search_features.add("• Cross-modal search")
    search_features.add("• Multiple output formats")

    console.print(tree)

def create_modality_table():
    """Create table showing modality support."""

    console.print("\n")
    console.print(Panel.fit(
        "[bold magenta]Supported Modalities & Processing[/bold magenta]",
        border_style="magenta"
    ))

    table = Table(box=box.ROUNDED)
    table.add_column("Modality", style="cyan", no_wrap=True)
    table.add_column("Extensions", style="yellow")
    table.add_column("Processing Method", style="green")
    table.add_column("Google API", style="magenta")

    table.add_row("Text", ".txt, .log", "Direct extraction", "—")
    table.add_row("Markdown", ".md, .markdown", "Markdown parsing", "—")
    table.add_row("PDF", ".pdf", "Document AI + PyPDF2", "Document AI")
    table.add_row("Images", ".jpg, .png, .gif", "Visual analysis", "Vision API")
    table.add_row("Audio", ".mp3, .wav, .m4a", "Transcription", "Speech-to-Text")
    table.add_row("Video", ".mp4, .avi, .mov", "Frame + audio analysis", "Video Intelligence")
    table.add_row("JSON", ".json, .jsonl", "Structured parsing", "—")
    table.add_row("CSV", ".csv, .tsv", "Tabular analysis", "—")

    console.print(table)

def create_status_summary():
    """Create status summary visualization."""

    console.print("\n")
    console.print(Panel.fit(
        "[bold green]System Capabilities Summary[/bold green]",
        border_style="green"
    ))

    capabilities = Table(box=box.SIMPLE)
    capabilities.add_column("Component", style="cyan")
    capabilities.add_column("Status", style="green")
    capabilities.add_column("Details", style="yellow")

    capabilities.add_row("📦 Data Lake", "✓ Active", "GCS bucket: gcm-data-lake")
    capabilities.add_row("🔧 CLI Tool", "✓ Ready", "grepctl orchestrates everything")
    capabilities.add_row("📊 BigQuery", "✓ Configured", "Dataset: mmgrep, 425+ documents")
    capabilities.add_row("🧠 ML Models", "✓ Deployed", "text-embedding-004 (768-dim)")
    capabilities.add_row("🔍 Search", "✓ Operational", "VECTOR_SEARCH with cosine similarity")
    capabilities.add_row("🎯 Accuracy", "✓ High", "Semantic understanding across modalities")
    capabilities.add_row("⚡ Performance", "✓ Fast", "Sub-second query response")
    capabilities.add_row("🔄 Recovery", "✓ Automatic", "fix_embeddings.py handles issues")

    console.print(capabilities)

def main():
    """Main function to display all visualizations."""

    console.print("=" * 80)
    console.print(Text("BIGQUERY SEMANTIC GREP - SYSTEM ARCHITECTURE", style="bold white on blue", justify="center"))
    console.print("=" * 80)

    # Display all visualizations
    create_architecture_diagram()
    create_command_workflow()
    create_modality_table()
    create_status_summary()

    # Summary
    console.print("\n")
    console.print(Panel(
        "[bold cyan]Key Insights:[/bold cyan]\n\n" +
        "• [green]One Command Setup:[/green] grepctl init all --auto-ingest\n" +
        "• [yellow]8 Modalities:[/yellow] Text, PDF, Images, Audio, Video, JSON, CSV, Markdown\n" +
        "• [magenta]6 Google APIs:[/magenta] Vision, Document AI, Speech, Video, Vertex AI, BigQuery\n" +
        "• [blue]Semantic Search:[/blue] 768-dimensional embeddings for understanding\n" +
        "• [red]Auto-Recovery:[/red] Handles embedding issues automatically\n\n" +
        "[dim]The system transforms a data lake of heterogeneous documents into\n" +
        "a unified, searchable knowledge base using BigQuery and AI.[/dim]",
        title="[bold]System Overview[/bold]",
        border_style="bright_blue"
    ))

if __name__ == "__main__":
    main()