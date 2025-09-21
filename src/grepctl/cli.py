#!/usr/bin/env python3
"""
Command-line interface for BigQuery Semantic Grep.
"""

import click
import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
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
@click.pass_context
def search(ctx, query, top_k, sources, rerank, regex, start_date, end_date, output):
    """Search across all indexed documents using semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    searcher = SemanticSearch(client, config)

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
@click.option('--dataset', '-d', default='mmgrep', help='BigQuery dataset name')
@click.option('--modalities', '-m', multiple=True,
              type=click.Choice(['pdf', 'images', 'audio', 'video', 'text', 'markdown', 'json', 'csv', 'documents']),
              help='Modalities to ingest')
@click.option('--chunk-size', default=1000, help='Chunk size for text splitting')
@click.option('--chunk-overlap', default=200, help='Overlap between chunks')
@click.option('--batch-size', default=100, help='Batch size for processing')
@click.pass_context
def ingest(ctx, bucket, dataset, modalities, chunk_size, chunk_overlap, batch_size):
    """Ingest data from GCS into BigQuery for semantic search."""
    config = ctx.obj['config']
    client = ctx.obj['client']

    # Update config with CLI parameters
    config.gcs_bucket = bucket
    config.dataset_name = dataset
    config.chunk_size = chunk_size
    config.chunk_overlap = chunk_overlap

    pipeline = IngestionPipeline(client, config)

    modalities_list = list(modalities) if modalities else ['all']

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Ingesting from gs://{bucket}...", total=None)

        stats = pipeline.run(
            modalities=modalities_list,
            batch_size=batch_size
        )

        progress.update(task, completed=True)

    # Display ingestion statistics
    table = Table(title="Ingestion Statistics")
    table.add_column("Modality", style="cyan")
    table.add_column("Documents", style="green")
    table.add_column("Chunks", style="yellow")
    table.add_column("Errors", style="red")

    for modality, counts in stats.items():
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

    console.print("[green]Setup completed successfully!")


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