#!/usr/bin/env python3
"""
Command-line interface for BigQuery Semantic Grep.
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config, load_config
from .bigquery.connection import BigQueryClient
from .search.vector_search import SemanticSearch
from .ingestion.base import IngestionPipeline

console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """BigQuery Semantic Grep - SQL-native semantic search across heterogeneous data."""
    ctx.ensure_object(dict)
    config_path = Path(config) if config else Path.home() / '.grepctl' / 'config.yaml'
    ctx.obj['config'] = load_config(config_path)
    ctx.obj['client'] = BigQueryClient(ctx.obj['config'])


@cli.command()
@click.argument('query')
@click.option('--top-k', '-k', default=20, help='Number of results to return')
@click.option('--sources', '-s', multiple=True, help='Filter by source types')
@click.option('--rerank', is_flag=True, help='Use LLM reranking for better precision')
@click.option('--regex', '-r', help='Additional regex filter')
@click.option('--start-date', help='Start date filter (YYYY-MM-DD)')
@click.option('--end-date', help='End date filter (YYYY-MM-DD)')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table')
@click.option('--show-query', is_flag=True, help='Show the SQL query instead of executing it')
@click.pass_context
def search(ctx, query, top_k, sources, rerank, regex, start_date, end_date, output, show_query):
    """Search across all indexed documents using semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    searcher = SemanticSearch(client, config)

    # If show-query flag is set, just show the query and exit
    if show_query:
        sql_query = searcher.get_search_query(
            query=query,
            top_k=top_k,
            source_filter=list(sources) if sources else None,
            use_rerank=rerank,
            regex_filter=regex,
            start_date=start_date,
            end_date=end_date
        )
        console.print("[bold cyan]Generated SQL Query:[/bold cyan]")
        console.print(sql_query)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching...", total=None)

        results = searcher.search(
            query=query,
            top_k=top_k,
            source_filter=list(sources) if sources else None,
            use_rerank=rerank,
            regex_filter=regex,
            start_date=start_date,
            end_date=end_date
        )

        progress.update(task, completed=True)

    if output == 'table':
        _display_results_table(results)
    elif output == 'json':
        import json
        click.echo(json.dumps(results, indent=2, default=str))
    else:  # csv
        _display_results_csv(results)


@cli.command()
@click.option('--bucket', '-b', required=True, help='GCS bucket name')
@click.option('--dataset', '-d', default='grepmm', help='BigQuery dataset name')
@click.option('--modalities', '-m', multiple=True,
              type=click.Choice(['pdf', 'images', 'audio', 'video', 'text', 'markdown', 'json', 'csv', 'documents']),
              help='Modalities to ingest')
@click.option('--chunk-size', default=1000, help='Chunk size for text splitting')
@click.option('--chunk-overlap', default=200, help='Overlap between chunks')
@click.option('--batch-size', default=100, help='Batch size for processing')
@click.option('--no-video', is_flag=True, help='Skip video processing to save time and costs')
@click.option('--no-audio', is_flag=True, help='Skip audio processing to save time and costs')
@click.option('--no-setup', is_flag=True, help='Skip initial setup step')
@click.pass_context
def ingest(ctx, bucket, dataset, modalities, chunk_size, chunk_overlap, batch_size, no_video, no_audio, no_setup):
    """Ingest data from GCS into BigQuery for semantic search. Runs setup first unless --no-setup is specified."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    # Run setup first unless --no-setup is specified
    if not no_setup:
        console.print("[yellow]Running setup first...[/yellow]")

        from .bigquery.schema import SchemaManager
        manager = SchemaManager(client, config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Create dataset
            task = progress.add_task("Creating dataset...", total=None)
            manager.create_dataset()
            progress.update(task, completed=True)

            # Create tables
            task = progress.add_task("Creating tables...", total=None)
            manager.create_tables()
            progress.update(task, completed=True)

            # Create external tables
            task = progress.add_task("Creating external tables...", total=None)
            manager.create_external_tables()
            progress.update(task, completed=True)

            # Create functions
            task = progress.add_task("Creating functions...", total=None)
            manager.create_functions()
            progress.update(task, completed=True)

            # Create embedding model
            task = progress.add_task("Creating embedding model...", total=None)
            manager.init_models()
            progress.update(task, completed=True)

        console.print("[green]Setup completed successfully![/green]\n")

    # Update config with CLI parameters
    config.gcs_bucket = bucket
    config.dataset_name = dataset
    config.chunk_size = chunk_size
    config.chunk_overlap = chunk_overlap

    pipeline = IngestionPipeline(client, config)

    modalities_list = list(modalities) if modalities else ['all']

    # Filter out video/audio if flags are set
    if no_video and 'video' in modalities_list:
        modalities_list.remove('video')
        console.print("[yellow]Skipping video processing (--no-video flag set)[/yellow]")
    if no_audio and 'audio' in modalities_list:
        modalities_list.remove('audio')
        console.print("[yellow]Skipping audio processing (--no-audio flag set)[/yellow]")

    # Handle 'all' with exclusions
    if 'all' in modalities_list:
        all_modalities = ['pdf', 'images', 'audio', 'video', 'text', 'markdown', 'json', 'csv', 'documents']
        if no_video:
            all_modalities.remove('video')
            console.print("[yellow]Excluding video from 'all' modalities (--no-video flag set)[/yellow]")
        if no_audio:
            all_modalities.remove('audio')
            console.print("[yellow]Excluding audio from 'all' modalities (--no-audio flag set)[/yellow]")
        modalities_list = all_modalities

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Ingesting from gs://{bucket}...", total=None)

        stats = pipeline.run(
            modalities=modalities_list,
            batch_size=batch_size,
            generate_embeddings=True
        )

        progress.update(task, completed=True)

    # Display ingestion statistics
    table = Table(title="Ingestion Statistics")
    table.add_column("Modality", style="cyan")
    table.add_column("Documents", style="green")
    table.add_column("Chunks", style="yellow")
    table.add_column("Errors", style="red")

    if 'modalities' in stats:
        for modality, counts in stats['modalities'].items():
            table.add_row(
                modality,
                str(counts.get('documents', 0)),
                str(counts.get('chunks', 0)),
                str(counts.get('errors', 0))
            )

    console.print(table)


@cli.command()
@click.option('--rebuild', is_flag=True, help='Rebuild vector index from scratch')
@click.option('--update', is_flag=True, help='Update embeddings for new documents')
@click.pass_context
def index(ctx, rebuild, update):
    """Manage vector index and embeddings."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .ingestion.embeddings import EmbeddingManager

    manager = EmbeddingManager(client, config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if rebuild:
            task = progress.add_task("Rebuilding vector index...", total=None)
            stats = manager.rebuild_index()
            progress.update(task, completed=True)
            console.print(f"[green]Index rebuilt successfully. {stats['documents_indexed']} documents indexed.")
        elif update:
            task = progress.add_task("Updating embeddings...", total=None)
            stats = manager.update_embeddings()
            progress.update(task, completed=True)
            console.print(f"[green]Embeddings updated. {stats['new_embeddings']} new embeddings generated.")
        else:
            console.print("[yellow]Please specify --rebuild or --update")


@cli.command()
@click.option('--connection', help='BigQuery connection name for GCS')
@click.pass_context
def setup(ctx, connection):
    """Setup BigQuery dataset and tables for semantic grep."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    if connection:
        config.gcs_connection = connection

    from .bigquery.schema import SchemaManager

    manager = SchemaManager(client, config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create dataset
        task = progress.add_task("Creating dataset...", total=None)
        manager.create_dataset()
        progress.update(task, completed=True)

        # Create tables
        task = progress.add_task("Creating tables...", total=None)
        manager.create_tables()
        progress.update(task, completed=True)

        # Create external tables
        task = progress.add_task("Creating external tables...", total=None)
        manager.create_external_tables()
        progress.update(task, completed=True)

        # Create functions
        task = progress.add_task("Creating functions...", total=None)
        manager.create_functions()
        progress.update(task, completed=True)

        # Create embedding model
        task = progress.add_task("Creating embedding model...", total=None)
        manager.init_models()
        progress.update(task, completed=True)

    console.print("[green]Setup completed successfully!")


@cli.command()
@click.pass_context
def check(ctx):
    """Check system health and service availability."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .health_check import HealthChecker
    from rich.panel import Panel
    from rich.text import Text

    checker = HealthChecker(client, config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running health checks...", total=None)
        results = checker.run_all_checks()
        progress.update(task, completed=True)

    # Display results
    console.print("\n[bold cyan]System Health Check Results[/bold cyan]\n")

    # Overall status
    if results['overall_status'] == 'healthy':
        status_text = Text("✅ HEALTHY", style="bold green")
    else:
        status_text = Text("❌ UNHEALTHY", style="bold red")

    console.print(Panel(
        f"Overall Status: {status_text}\n"
        f"Passed: {results['summary']['passed']} | "
        f"Failed: {results['summary']['failed']} | "
        f"Warnings: {results['summary']['warnings']}",
        title="Summary",
        border_style="cyan"
    ))

    # Detailed results for each check
    for check_name, check_result in results['checks'].items():
        # Determine style based on status
        if check_result['status'] == 'passed':
            title_style = "green"
            status_icon = "✅"
        else:
            title_style = "red"
            status_icon = "❌"

        # Build content
        content_lines = []

        # Add details
        if check_result.get('details'):
            for key, value in check_result['details'].items():
                content_lines.append(value)

        # Add errors
        if check_result.get('errors'):
            content_lines.append("")
            content_lines.append("[bold red]Errors:[/bold red]")
            for error in check_result['errors']:
                content_lines.append(f"  • {error}")

        # Add warnings
        if check_result.get('warnings'):
            content_lines.append("")
            content_lines.append("[bold yellow]Warnings:[/bold yellow]")
            for warning in check_result['warnings']:
                content_lines.append(f"  • {warning}")

        # Add instructions
        if check_result.get('instructions'):
            content_lines.append("")
            content_lines.append("[bold cyan]How to fix:[/bold cyan]")
            for instruction in check_result['instructions']:
                content_lines.append(instruction)

        # Display panel
        console.print(Panel(
            "\n".join(content_lines),
            title=f"{status_icon} {check_name.upper()}",
            border_style=title_style,
            padding=(1, 2)
        ))

    # Final recommendations
    if results['summary']['failed'] > 0:
        console.print("\n[bold yellow]⚠️  Action Required:[/bold yellow]")
        console.print("Run the commands shown above to fix the failed checks.")
        console.print("After fixing, run 'grepctl check' again to verify.\n")
    elif results['summary']['warnings'] > 0:
        console.print("\n[bold yellow]ℹ️  Optional Improvements:[/bold yellow]")
        console.print("Some optional features are not configured.")
        console.print("Review the warnings above if you want to enable them.\n")
    else:
        console.print("\n[bold green]✨ All systems operational![/bold green]")
        console.print("Your grepctl installation is fully configured.\n")


@cli.command()
@click.option('--project', '-p', default='semgrep-472018', help='Google Cloud project ID')
@click.option('--location', '-l', default='us-central1', help='Vertex AI location')
@click.pass_context
def enable(ctx, project, location):
    """Enable all required Google Cloud APIs and verify model availability."""
    from .enable_services import enable_services_and_models

    apis_success, models_success = enable_services_and_models(project, location)

    if not apis_success or not models_success:
        sys.exit(1)


@cli.command()
@click.option('--setup', is_flag=True, help='Setup PDF metadata table')
@click.option('--ingest', is_flag=True, help='Ingest PDFs with metadata')
@click.option('--add-metadata', is_flag=True, help='Add sample metadata for PDFs')
@click.option('--extract', is_flag=True, help='Extract text from PDFs using Document AI')
@click.pass_context
def pdfs(ctx, setup, ingest, add_metadata, extract):
    """Manage PDF ingestion and metadata for semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .ingestion.pdf_processor import PDFProcessor

    processor = PDFProcessor(client, config)

    if setup:
        console.print("[yellow]Setting up PDF metadata table...[/yellow]")
        processor.create_pdf_metadata_table()
        console.print("[green]✓ PDF metadata table ready[/green]")

    if add_metadata:
        console.print("[yellow]Adding sample PDF metadata...[/yellow]")
        processor.add_sample_pdf_metadata()
        console.print("[green]✓ Sample metadata added[/green]")

    if ingest:
        console.print("[yellow]Ingesting PDFs with metadata...[/yellow]")

        # First ingest to documents table
        docs_count = processor.ingest_pdfs_with_metadata()
        console.print(f"[green]✓ Ingested {docs_count} PDFs to documents table[/green]")

        # Then update search corpus
        corpus_count = processor.update_search_corpus()
        console.print(f"[green]✓ Added {corpus_count} PDFs to search corpus[/green]")

        # Generate embeddings
        console.print("[yellow]Generating embeddings for PDFs...[/yellow]")
        from .ingestion.embeddings import EmbeddingManager
        embed_manager = EmbeddingManager(client, config)
        stats = embed_manager.update_embeddings()
        console.print(f"[green]✓ Generated {stats['new_embeddings']} new embeddings[/green]")

        console.print("\n[bold green]PDFs ready for semantic search![/bold green]")
        console.print("Try: grepctl search 'machine learning transformer' --top-k 5")

    if extract:
        console.print("[yellow]Extracting text from PDFs using Document AI...[/yellow]")
        console.print("[dim]This will process up to 5 PDFs at a time[/dim]")

        processed = processor.process_pdfs_with_document_ai()
        console.print(f"[green]✓ Processed {processed} PDFs with Document AI[/green]")

        if processed > 0:
            # Regenerate embeddings for updated PDFs
            console.print("[yellow]Regenerating embeddings for updated PDFs...[/yellow]")
            from .ingestion.embeddings import EmbeddingManager
            embed_manager = EmbeddingManager(client, config)
            stats = embed_manager.update_embeddings()
            console.print(f"[green]✓ Updated {stats['new_embeddings']} embeddings[/green]")

    if not (setup or ingest or add_metadata or extract):
        console.print("[yellow]Please specify an action: --setup, --add-metadata, --ingest, or --extract[/yellow]")


@cli.command()
@click.option('--setup', is_flag=True, help='Setup image descriptions table')
@click.option('--ingest', is_flag=True, help='Ingest images with descriptions')
@click.option('--add-descriptions', is_flag=True, help='Add sample descriptions for demo')
@click.pass_context
def images(ctx, setup, ingest, add_descriptions):
    """Manage image ingestion and descriptions for semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .ingestion.image_processor import ImageProcessor

    processor = ImageProcessor(client, config)

    if setup:
        console.print("[yellow]Setting up image descriptions table...[/yellow]")
        processor.create_image_descriptions_table()
        console.print("[green]✓ Image descriptions table ready[/green]")

    if add_descriptions:
        console.print("[yellow]Adding sample image descriptions...[/yellow]")
        processor.add_sample_descriptions()
        console.print("[green]✓ Sample descriptions added[/green]")

    if ingest:
        console.print("[yellow]Ingesting images with descriptions...[/yellow]")

        # First ingest to documents table
        docs_count = processor.ingest_images_with_descriptions()
        console.print(f"[green]✓ Ingested {docs_count} images to documents table[/green]")

        # Then update search corpus
        corpus_count = processor.update_search_corpus()
        console.print(f"[green]✓ Added {corpus_count} images to search corpus[/green]")

        # Generate embeddings
        console.print("[yellow]Generating embeddings for images...[/yellow]")
        from .ingestion.embeddings import EmbeddingManager
        embed_manager = EmbeddingManager(client, config)
        stats = embed_manager.update_embeddings()
        console.print(f"[green]✓ Generated {stats['new_embeddings']} new embeddings[/green]")

        console.print("\n[bold green]Images ready for semantic search![/bold green]")
        console.print("Try: grepctl search 'bird' --top-k 5")

    if not (setup or ingest or add_descriptions):
        console.print("[yellow]Please specify an action: --setup, --add-descriptions, or --ingest[/yellow]")


@cli.command()
@click.option('--setup', is_flag=True, help='Setup audio metadata tables')
@click.option('--transcribe', is_flag=True, help='Transcribe audio files from GCS')
@click.option('--batch-size', default=10, help='Number of files to process in each batch')
@click.option('--add-speakers', is_flag=True, help='Add speaker identification metadata')
@click.option('--process-batch', is_flag=True, help='Process a batch of audio files')
@click.pass_context
def audio(ctx, setup, transcribe, batch_size, add_speakers, process_batch):
    """Manage audio ingestion and transcription for semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .ingestion.audio_processor import AudioProcessor

    processor = AudioProcessor(client, config)

    if setup:
        console.print("[yellow]Setting up audio metadata tables...[/yellow]")
        processor.create_audio_metadata_table()
        console.print("[green]✓ Audio metadata tables ready[/green]")

    if transcribe or process_batch:
        console.print(f"[yellow]Processing audio files with batch size {batch_size}...[/yellow]")
        console.print("[dim]Using Cloud Speech-to-Text API v2[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Transcribing audio files...", total=None)

            stats = processor.process_audio_files(batch_size=batch_size)

            progress.update(task, completed=True)

        # Display results
        table = Table(title="Audio Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files Processed", str(stats['files_processed']))
        table.add_row("Files Failed", str(stats['files_failed']))
        table.add_row("Total Duration", f"{stats['total_duration_seconds']:.1f} seconds")
        table.add_row("Chunks Created", str(stats['chunks_created']))
        table.add_row("Processing Time", f"{stats['duration']:.1f} seconds")

        console.print(table)

        if stats['files_processed'] > 0:
            # Update search corpus
            console.print("[yellow]Updating search corpus...[/yellow]")
            corpus_count = processor.update_search_corpus()
            console.print(f"[green]✓ Added {corpus_count} audio documents to search corpus[/green]")

            # Generate embeddings
            console.print("[yellow]Generating embeddings for audio documents...[/yellow]")
            from .ingestion.embeddings import EmbeddingManager
            embed_manager = EmbeddingManager(client, config)
            embed_stats = embed_manager.update_embeddings()
            console.print(f"[green]✓ Generated {embed_stats['new_embeddings']} new embeddings[/green]")

            console.print("\n[bold green]Audio files ready for semantic search![/bold green]")
            console.print("Try: grepctl search 'conversation speech' --top-k 5")

    if add_speakers:
        console.print("[yellow]Speaker identification metadata feature coming soon![/yellow]")
        console.print("Audio files are already processed with speaker diarization when available.")

    if not (setup or transcribe or process_batch or add_speakers):
        console.print("[yellow]Please specify an action: --setup, --transcribe, or --process-batch[/yellow]")
        console.print("\nExamples:")
        console.print("  grepctl audio --setup                # Setup audio metadata tables")
        console.print("  grepctl audio --transcribe            # Process all audio files")
        console.print("  grepctl audio --process-batch --batch-size 5  # Process in smaller batches")


@cli.command()
@click.option('--setup', is_flag=True, help='Setup video processing tables')
@click.option('--process', is_flag=True, help='Process video files from GCS')
@click.option('--batch-size', default=5, help='Number of videos to process in each batch')
@click.option('--mode', type=click.Choice(['minimal', 'efficient', 'full']),
              default='efficient', help='Processing mode (minimal=cheapest, full=complete)')
@click.option('--search', help='Search videos using text query')
@click.option('--search-type', type=click.Choice(['transcript', 'ocr', 'visual', 'hybrid']),
              default='hybrid', help='Type of video search')
@click.option('--top-k', '-k', default=10, help='Number of results to return')
@click.pass_context
def video(ctx, setup, process, batch_size, mode, search, search_type, top_k):
    """Manage video ingestion with shot detection, transcription, and OCR."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    from .ingestion.video_processor import VideoProcessor

    processor = VideoProcessor(client, config)

    if setup:
        console.print("[yellow]Setting up video processing tables...[/yellow]")
        processor.create_video_tables()
        console.print("[green]✓ Video processing tables ready[/green]")
        console.print("  - video_metadata: Store video info and labels")
        console.print("  - video_segments: Store shot segments with embeddings")
        console.print("  - video_transcripts: Store audio transcriptions")
        console.print("  - video_ocr_text: Store detected on-screen text")

    if process:
        console.print(f"[yellow]Processing video files with batch size {batch_size}...[/yellow]")
        console.print(f"[dim]Mode: {mode} - ", end="")

        if mode == 'minimal':
            console.print("Lowest cost, basic analysis only[/dim]")
        elif mode == 'efficient':
            console.print("Balanced cost/quality, sampled analysis[/dim]")
        elif mode == 'full':
            console.print("Complete analysis, highest cost[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing videos...", total=None)

            stats = processor.process_video_files(batch_size=batch_size, sample_mode=mode)

            progress.update(task, completed=True)

        # Display results
        table = Table(title="Video Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files Processed", str(stats['files_processed']))
        table.add_row("Files Failed", str(stats['files_failed']))
        table.add_row("Total Duration", f"{stats['total_duration_seconds']:.1f} seconds")
        table.add_row("Segments Created", str(stats['segments_created']))
        table.add_row("Transcripts Created", str(stats['transcripts_created']))
        table.add_row("OCR Detections", str(stats['ocr_detections']))
        table.add_row("Processing Time", f"{stats['duration']:.1f} seconds")

        console.print(table)

        if stats['files_processed'] > 0:
            console.print("\n[bold green]Videos ready for semantic search![/bold green]")
            console.print("Try: grepctl video --search 'presentation slides' --search-type hybrid")

    if search:
        console.print(f"[yellow]Searching videos for: '{search}'[/yellow]")
        console.print(f"[dim]Search type: {search_type}[/dim]")

        results = processor.search_videos(search, search_type=search_type, top_k=top_k)

        if results:
            # Display search results
            table = Table(title="Video Search Results", show_lines=True)
            table.add_column("Rank", style="cyan", width=6)
            table.add_column("Type", style="green", width=12)
            table.add_column("Score", style="yellow", width=8)
            table.add_column("Content/Label", style="white", overflow="fold")
            table.add_column("Timestamp", style="blue", width=15)
            table.add_column("Video", style="magenta", width=30, overflow="ellipsis")

            for i, result in enumerate(results, 1):
                # Format timestamp as clickable link
                start_time = result.get('start_time', 0)
                end_time = result.get('end_time', start_time)
                timestamp = f"{int(start_time)}s-{int(end_time)}s"

                # Get content based on result type
                if result.get('result_type') == 'transcript':
                    content = f"[Speaker {result.get('speaker_id', '?')}] {result.get('text', '')[:100]}..."
                elif result.get('result_type') == 'ocr':
                    content = f"OCR: {result.get('text', '')[:100]}..."
                else:
                    content = f"Shot: {result.get('shot_label', 'Visual segment')}"

                video_name = result.get('uri', '').split('/')[-1]

                table.add_row(
                    str(i),
                    result.get('result_type', 'unknown'),
                    f"{result.get('score', 0):.3f}",
                    content,
                    timestamp,
                    video_name
                )

            console.print(table)

            # Provide deep links
            console.print("\n[dim]To view a specific segment, use the timestamp to seek in the video.[/dim]")
        else:
            console.print(f"[yellow]No results found for '{search}'[/yellow]")

    if not (setup or process or search):
        console.print("[yellow]Please specify an action: --setup, --process, or --search[/yellow]")
        console.print("\nExamples:")
        console.print("  grepctl video --setup                           # Setup video processing tables")
        console.print("  grepctl video --process --mode minimal          # Cheapest processing (~$0.05/min)")
        console.print("  grepctl video --process --mode efficient        # Balanced processing (~$0.15/min)")
        console.print("  grepctl video --process --mode full             # Complete analysis (~$0.40/min)")
        console.print("  grepctl video --search 'meeting notes'          # Search video content")
        console.print("  grepctl video --search 'logo' --search-type ocr # Search on-screen text")
        console.print("\n[dim]Processing modes:")
        console.print("  minimal:   Shot detection + transcription (samples every 30s)")
        console.print("  efficient: Shot detection + transcription (samples every 10s)")
        console.print("  full:      All features including OCR + labels (no sampling)[/dim]")


@cli.command()
@click.pass_context
def status(ctx):
    """Check the status of the semantic grep system."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    try:
        # Check dataset
        dataset_exists = client.check_dataset_exists(config.dataset_name)

        # Get document count
        doc_count = client.get_document_count()

        # Get index status
        index_status = client.get_index_status()

        # Create status table
        table = Table(title="System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        table.add_row(
            "Dataset",
            "✓" if dataset_exists else "✗",
            config.dataset_name if dataset_exists else "Not found"
        )

        table.add_row(
            "Documents",
            "✓" if doc_count > 0 else "✗",
            f"{doc_count:,} documents"
        )

        table.add_row(
            "Vector Index",
            "✓" if index_status['exists'] else "✗",
            f"Last updated: {index_status.get('last_updated', 'Never')}"
        )

        table.add_row(
            "Models",
            "✓",
            f"Text: {config.text_model.split('/')[-1]}, Embedding: {config.embedding_model.split('/')[-1]}"
        )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error checking status: {e}")


@cli.command()
@click.option('--host', '-h', default='0.0.0.0', help='Host to bind to')
@click.option('--port', '-p', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.option('--theme-config', type=click.Path(exists=True), help='Path to theme configuration file')
@click.option('--workers', '-w', default=1, help='Number of worker processes')
@click.pass_context
def serve(ctx, host, port, reload, theme_config, workers):
    """Start the REST API server with web UI."""
    config = ctx.obj['config']

    console.print(Panel.fit(
        f"🚀 [bold cyan]Starting grepctl API Server[/bold cyan]\n"
        f"[green]➜[/green] API: http://{host}:{port}/api/docs\n"
        f"[green]➜[/green] Web UI: http://{host}:{port}",
        border_style="cyan"
    ))

    try:
        # Check if uvicorn is installed
        try:
            import uvicorn
        except ImportError:
            console.print("[red]Error: uvicorn not installed. Run: uv add 'uvicorn[standard]'[/red]")
            sys.exit(1)

        # Set theme config environment variable if provided
        if theme_config:
            os.environ['GREPCTL_THEME_CONFIG'] = theme_config

        # Set config in environment for the server to use
        os.environ['GREPCTL_PROJECT_ID'] = config.project_id
        os.environ['GREPCTL_DATASET_NAME'] = config.dataset_name
        os.environ['GREPCTL_LOCATION'] = config.location

        # Run the server
        uvicorn.run(
            "grepctl.api.server:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info"
        )
    except Exception as e:
        console.print(f"[red]Failed to start server: {e}[/red]")
        sys.exit(1)


def _display_results_table(results):
    """Display search results in a table format."""
    table = Table(title="Search Results", show_lines=True)
    table.add_column("Rank", style="cyan", width=6)
    table.add_column("Source", style="green", width=12)
    table.add_column("Score", style="yellow", width=8)
    table.add_column("Content", style="white", overflow="fold")
    table.add_column("URI", style="blue", width=30, overflow="ellipsis")

    for i, result in enumerate(results, 1):
        text_content = result.get('text_content', '')
        content_preview = text_content[:200] + "..." if len(text_content) > 200 else text_content
        score_val = result.get('rel_score') or result.get('distance', 0)
        score = f"{score_val:.3f}" if score_val is not None else "N/A"

        table.add_row(
            str(i),
            result.get('source', 'unknown'),
            score,
            content_preview,
            result.get('uri', '')
        )

    console.print(table)


def _display_results_csv(results):
    """Display search results in CSV format."""
    import csv
    import sys

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=['rank', 'doc_id', 'uri', 'source', 'modality', 'score', 'text_content']
    )
    writer.writeheader()

    for i, result in enumerate(results, 1):
        writer.writerow({
            'rank': i,
            'doc_id': result['doc_id'],
            'uri': result['uri'],
            'source': result['source'],
            'modality': result['modality'],
            'score': result.get('rel_score', result.get('distance', 0)),
            'text_content': result['text_content'][:500]
        })


def main():
    """Main entry point for the CLI."""
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()