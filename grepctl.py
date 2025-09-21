#!/usr/bin/env python3
"""
grepctl - Comprehensive CLI utility for BigQuery Semantic Grep (mmgrep).
Manages all aspects of multimodal semantic search from setup to search.
"""

import click
import yaml
import json
import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich import print as rprint
from google.cloud import bigquery
from google.cloud import storage
import logging

# Setup console and logging
console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = Path.home() / '.grepctl.yaml'
DEFAULT_PROJECT = "semgrep-472018"
DEFAULT_DATASET = "mmgrep"
DEFAULT_BUCKET = "gcm-data-lake"

# Required Google Cloud APIs
REQUIRED_APIS = [
    'bigquery.googleapis.com',
    'aiplatform.googleapis.com',
    'vision.googleapis.com',
    'documentai.googleapis.com',
    'speech.googleapis.com',
    'videointelligence.googleapis.com',
    'storage.googleapis.com',
]

# Modality configurations
MODALITIES = {
    'text': {'extensions': ['.txt', '.log'], 'script': None},
    'markdown': {'extensions': ['.md', '.markdown'], 'script': None},
    'pdf': {'extensions': ['.pdf'], 'script': 'src/grepctl/scripts/extract_all_pdfs_hybrid.py'},
    'images': {'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'], 'script': None},  # complete_vision_analysis.py moved to obsolete
    'json': {'extensions': ['.json', '.jsonl'], 'script': 'src/grepctl/scripts/ingest_json_csv_fixed.py'},
    'csv': {'extensions': ['.csv', '.tsv'], 'script': 'src/grepctl/scripts/ingest_json_csv_fixed.py'},
    'audio': {'extensions': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'], 'script': 'src/grepctl/scripts/ingest_audio_files.py'},
    'video': {'extensions': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'], 'script': 'src/grepctl/scripts/ingest_video_files.py'},
}


class GrepCtl:
    """Main controller class for grepctl operations."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize GrepCtl with configuration."""
        self.config_path = config_path or CONFIG_FILE
        self.config = self.load_config()
        self.bq_client = None
        self.storage_client = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                console.print(f"[green]Loaded configuration from {self.config_path}[/green]")
                return config
        else:
            return {
                'project_id': DEFAULT_PROJECT,
                'dataset': DEFAULT_DATASET,
                'bucket': DEFAULT_BUCKET,
                'location': 'US',
                'vertex_connection': 'vertex-ai-connection',
                'batch_size': 100,
                'chunk_size': 1000,
                'chunk_overlap': 200,
            }

    def save_config(self):
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
        console.print(f"[green]Configuration saved to {self.config_path}[/green]")

    def get_bq_client(self):
        """Get or create BigQuery client."""
        if not self.bq_client:
            self.bq_client = bigquery.Client(project=self.config['project_id'])
        return self.bq_client

    def get_storage_client(self):
        """Get or create Storage client."""
        if not self.storage_client:
            self.storage_client = storage.Client(project=self.config['project_id'])
        return self.storage_client

    def run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command."""
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if check and result.returncode != 0:
            console.print(f"[red]Command failed: {result.stderr}[/red]")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    def run_python_script(self, script_name: str, wait: bool = True) -> bool:
        """Run a Python script using uv."""
        script_path = Path(__file__).parent / script_name
        if not script_path.exists():
            console.print(f"[yellow]Script {script_name} not found, skipping[/yellow]")
            return False

        cmd = ['uv', 'run', 'python', str(script_path)]

        if wait:
            with console.status(f"Running {script_name}..."):
                result = self.run_command(cmd, check=False)
                if result.returncode == 0:
                    console.print(f"[green]✓ {script_name} completed successfully[/green]")
                    return True
                else:
                    console.print(f"[red]✗ {script_name} failed[/red]")
                    return False
        else:
            subprocess.Popen(cmd)
            console.print(f"[green]Started {script_name} in background[/green]")
            return True


# Create global instance
ctl = GrepCtl()


@click.group()
@click.option('--config', '-c', type=click.Path(), help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """grepctl - Manage BigQuery Semantic Grep (mmgrep) system."""
    if config:
        global ctl
        ctl = GrepCtl(Path(config))
    ctx.ensure_object(dict)


# ============= INIT COMMANDS =============
@cli.group()
def init():
    """Initialize and setup the mmgrep system."""
    pass


@init.command('all')
@click.option('--bucket', '-b', default=DEFAULT_BUCKET, help='GCS bucket name')
@click.option('--project', '-p', default=DEFAULT_PROJECT, help='GCP project ID')
@click.option('--dataset', '-d', default=DEFAULT_DATASET, help='BigQuery dataset name')
@click.option('--auto-ingest', is_flag=True, help='Automatically ingest all data after setup')
def init_all(bucket, project, dataset, auto_ingest):
    """Complete one-command setup with optional auto-ingestion."""
    console.print(Panel.fit("🚀 [bold cyan]Complete System Initialization[/bold cyan]", border_style="cyan"))

    # Update configuration
    ctl.config['bucket'] = bucket
    ctl.config['project_id'] = project
    ctl.config['dataset'] = dataset
    ctl.save_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        # Enable APIs
        task = progress.add_task("Enabling Google Cloud APIs...", total=len(REQUIRED_APIS))
        for api in REQUIRED_APIS:
            cmd = ['gcloud', 'services', 'enable', api, '--project', project]
            ctl.run_command(cmd, check=False)
            progress.advance(task)

        # Create dataset
        task = progress.add_task("Creating BigQuery dataset...", total=1)
        try:
            client = ctl.get_bq_client()
            dataset_id = f"{project}.{dataset}"
            dataset_obj = bigquery.Dataset(dataset_id)
            dataset_obj.location = "US"
            client.create_dataset(dataset_obj, exists_ok=True)
            progress.advance(task)
        except Exception as e:
            console.print(f"[yellow]Dataset creation: {e}[/yellow]")
            progress.advance(task)

        # Create tables
        task = progress.add_task("Creating tables and models...", total=1)
        if Path('src/grepctl/scripts/setup_mmgrep.py').exists():
            ctl.run_python_script('src/grepctl/scripts/setup_mmgrep.py')
        progress.advance(task)

        # Auto-ingest if requested
        if auto_ingest:
            task = progress.add_task("Ingesting all modalities...", total=len(MODALITIES))
            for modality in MODALITIES:
                console.print(f"[cyan]Processing {modality}...[/cyan]")
                if modality in ['text', 'markdown']:
                    # Use grepctl ingest for text/markdown
                    cmd = ['uv', 'run', 'grepctl', 'ingest', '-b', bucket, '-m', modality]
                    ctl.run_command(cmd, check=False)
                elif MODALITIES[modality]['script']:
                    ctl.run_python_script(MODALITIES[modality]['script'])
                progress.advance(task)

            # Generate embeddings
            console.print("[cyan]Generating embeddings...[/cyan]")
            ctl.run_python_script('src/grepctl/scripts/fix_embeddings.py')

    console.print("[bold green]✅ System initialization complete![/bold green]")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("  1. Check status: [yellow]grepctl status[/yellow]")
    console.print("  2. Search data: [yellow]grepctl search 'your query'[/yellow]")


@init.command('config')
@click.option('--project', '-p', help='GCP project ID')
@click.option('--dataset', '-d', help='BigQuery dataset name')
@click.option('--bucket', '-b', help='GCS bucket name')
def init_config(project, dataset, bucket):
    """Generate or update .grepctl.yaml configuration."""
    if project:
        ctl.config['project_id'] = project
    if dataset:
        ctl.config['dataset'] = dataset
    if bucket:
        ctl.config['bucket'] = bucket

    ctl.save_config()
    console.print("\n[cyan]Current configuration:[/cyan]")
    console.print(yaml.dump(ctl.config, default_flow_style=False))


@init.command('dataset')
def init_dataset():
    """Create BigQuery dataset and tables."""
    console.print("[cyan]Creating BigQuery dataset and tables...[/cyan]")

    client = ctl.get_bq_client()
    dataset_id = f"{ctl.config['project_id']}.{ctl.config['dataset']}"

    # Create dataset
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = ctl.config.get('location', 'US')

    try:
        dataset = client.create_dataset(dataset, exists_ok=True)
        console.print(f"[green]✓ Dataset {dataset_id} ready[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create dataset: {e}[/red]")
        return

    # Run setup script if available
    if Path('src/grepctl/scripts/setup_mmgrep.py').exists():
        ctl.run_python_script('src/grepctl/scripts/setup_mmgrep.py')
    else:
        console.print("[yellow]setup_mmgrep.py not found, skipping table creation[/yellow]")


@init.command('models')
def init_models():
    """Create ML models for embeddings."""
    console.print("[cyan]Creating ML models...[/cyan]")

    client = ctl.get_bq_client()

    # Create embedding model
    model_query = f"""
    CREATE OR REPLACE MODEL `{ctl.config['project_id']}.{ctl.config['dataset']}.text_embedding_model`
    REMOTE WITH CONNECTION `{ctl.config['project_id']}.US.{ctl.config.get('vertex_connection', 'vertex-ai-connection')}`
    OPTIONS (ENDPOINT = 'text-embedding-004')
    """

    try:
        job = client.query(model_query)
        job.result()
        console.print("[green]✓ Embedding model created[/green]")
    except Exception as e:
        console.print(f"[yellow]Model creation: {e}[/yellow]")


# ============= APIS COMMANDS =============
@cli.group()
def apis():
    """Manage Google Cloud APIs."""
    pass


@apis.command('enable')
@click.option('--all', 'enable_all', is_flag=True, help='Enable all required APIs')
@click.option('--api', multiple=True, help='Specific API to enable')
def apis_enable(enable_all, api):
    """Enable required Google Cloud APIs."""
    apis_to_enable = REQUIRED_APIS if enable_all else list(api)

    if not apis_to_enable:
        console.print("[yellow]No APIs specified. Use --all or --api[/yellow]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Enabling {len(apis_to_enable)} APIs...", total=len(apis_to_enable))

        for api_name in apis_to_enable:
            cmd = ['gcloud', 'services', 'enable', api_name, '--project', ctl.config['project_id']]
            result = ctl.run_command(cmd, check=False)

            if result.returncode == 0:
                console.print(f"[green]✓ {api_name}[/green]")
            else:
                console.print(f"[red]✗ {api_name}: {result.stderr}[/red]")

            progress.advance(task)


@apis.command('check')
def apis_check():
    """Check status of required APIs."""
    console.print("[cyan]Checking API status...[/cyan]")

    table = Table(title="API Status")
    table.add_column("API", style="cyan")
    table.add_column("Status", style="green")

    for api in REQUIRED_APIS:
        cmd = ['gcloud', 'services', 'list', '--enabled', '--filter', f'name:{api}',
               '--project', ctl.config['project_id'], '--format', 'value(name)']
        result = ctl.run_command(cmd, check=False)

        if api in result.stdout:
            table.add_row(api, "✓ Enabled")
        else:
            table.add_row(api, "[red]✗ Disabled[/red]")

    console.print(table)


# ============= INGEST COMMANDS =============
@cli.group()
def ingest():
    """Ingest data from various sources."""
    pass


@ingest.command('all')
@click.option('--bucket', '-b', help='GCS bucket (overrides config)')
@click.option('--resume', is_flag=True, help='Resume from last checkpoint')
def ingest_all(bucket, resume):
    """Process all modalities from GCS bucket."""
    bucket = bucket or ctl.config['bucket']

    console.print(Panel.fit(f"📥 [bold cyan]Ingesting All Modalities from gs://{bucket}[/bold cyan]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Processing modalities...", total=len(MODALITIES))

        for modality, config in MODALITIES.items():
            console.print(f"\n[cyan]Processing {modality}...[/cyan]")

            if modality in ['text', 'markdown']:
                # Use grepctl for text/markdown
                cmd = ['uv', 'run', 'grepctl', 'ingest', '-b', bucket, '-m', modality]
                ctl.run_command(cmd, check=False)
            elif config['script']:
                ctl.run_python_script(config['script'])

            progress.advance(task)

    console.print("[green]✓ All modalities processed[/green]")
    console.print("\n[cyan]Next: Run 'grepctl index update' to generate embeddings[/cyan]")


@ingest.command('pdf')
def ingest_pdf():
    """Ingest and process PDF files."""
    console.print("[cyan]Processing PDF files...[/cyan]")
    if ctl.run_python_script('src/grepctl/scripts/extract_all_pdfs_hybrid.py'):
        console.print("[green]✓ PDF ingestion complete[/green]")


@ingest.command('images')
def ingest_images():
    """Ingest and analyze images with Vision API."""
    console.print("[cyan]Processing images with Vision API...[/cyan]")
    if ctl.run_python_script('src/grepctl/scripts/complete_vision_analysis.py'):
        console.print("[green]✓ Image analysis complete[/green]")


@ingest.command('audio')
def ingest_audio():
    """Ingest and transcribe audio files."""
    console.print("[cyan]Processing audio files...[/cyan]")
    if ctl.run_python_script('src/grepctl/scripts/ingest_audio_files.py'):
        console.print("[green]✓ Audio transcription complete[/green]")


@ingest.command('video')
def ingest_video():
    """Ingest and analyze video files."""
    console.print("[cyan]Processing video files...[/cyan]")
    if ctl.run_python_script('src/grepctl/scripts/ingest_video_files.py'):
        console.print("[green]✓ Video analysis complete[/green]")


@ingest.command('json')
def ingest_json():
    """Ingest JSON and CSV files."""
    console.print("[cyan]Processing JSON/CSV files...[/cyan]")
    if ctl.run_python_script('src/grepctl/scripts/ingest_json_csv_fixed.py'):
        console.print("[green]✓ JSON/CSV ingestion complete[/green]")


# ============= INDEX COMMANDS =============
@cli.group()
def index():
    """Manage vector embeddings and search index."""
    pass


@index.command('rebuild')
def index_rebuild():
    """Rebuild all embeddings from scratch."""
    console.print("[cyan]Rebuilding all embeddings...[/cyan]")

    cmd = ['uv', 'run', 'grepctl', 'index', '--rebuild']
    result = ctl.run_command(cmd, check=False)

    if result.returncode == 0:
        console.print("[green]✓ Index rebuilt successfully[/green]")
    else:
        console.print("[yellow]Index rebuild encountered issues, running fix...[/yellow]")
        ctl.run_python_script('src/grepctl/scripts/fix_embeddings.py')


@index.command('update')
def index_update():
    """Update missing embeddings."""
    console.print("[cyan]Updating embeddings...[/cyan]")

    # Run fix_embeddings.py which handles all embedding updates
    if ctl.run_python_script('src/grepctl/scripts/fix_embeddings.py'):
        console.print("[green]✓ Embeddings updated successfully[/green]")


@index.command('verify')
def index_verify():
    """Verify embedding health and dimensions."""
    console.print("[cyan]Verifying embeddings...[/cyan]")

    client = ctl.get_bq_client()

    query = f"""
    SELECT
        modality,
        COUNT(*) as total_docs,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 768 THEN 1 ELSE 0 END) as valid_embeddings,
        SUM(CASE WHEN embedding IS NULL THEN 1 ELSE 0 END) as null_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 0 THEN 1 ELSE 0 END) as empty_embeddings
    FROM `{ctl.config['project_id']}.{ctl.config['dataset']}.search_corpus`
    GROUP BY modality
    ORDER BY modality
    """

    results = client.query(query).result()

    table = Table(title="Embedding Health Check")
    table.add_column("Modality", style="cyan")
    table.add_column("Total", style="yellow")
    table.add_column("Valid (768-dim)", style="green")
    table.add_column("Missing", style="red")
    table.add_column("Empty", style="red")

    for row in results:
        table.add_row(
            row.modality,
            str(row.total_docs),
            str(row.valid_embeddings),
            str(row.null_embeddings),
            str(row.empty_embeddings)
        )

    console.print(table)


# ============= FIX COMMANDS =============
@cli.group()
def fix():
    """Troubleshooting and repair utilities."""
    pass


@fix.command('embeddings')
def fix_embeddings():
    """Fix dimension mismatches and empty arrays."""
    console.print("[cyan]Fixing embedding issues...[/cyan]")

    if ctl.run_python_script('src/grepctl/scripts/fix_embeddings.py'):
        console.print("[green]✓ Embedding issues resolved[/green]")


@fix.command('stuck')
@click.option('--modality', '-m', help='Specific modality to fix')
def fix_stuck(modality):
    """Handle stuck processing for any modality."""
    console.print(f"[cyan]Fixing stuck processing{f' for {modality}' if modality else ''}...[/cyan]")

    client = ctl.get_bq_client()

    # Clear empty embeddings
    query = f"""
    UPDATE `{ctl.config['project_id']}.{ctl.config['dataset']}.search_corpus`
    SET embedding = NULL
    WHERE ARRAY_LENGTH(embedding) = 0
    {f"AND modality = '{modality}'" if modality else ''}
    """

    job = client.query(query)
    job.result()

    if job.num_dml_affected_rows > 0:
        console.print(f"[green]✓ Reset {job.num_dml_affected_rows} stuck embeddings[/green]")

    # Re-run fix script
    ctl.run_python_script('src/grepctl/scripts/fix_embeddings.py')


@fix.command('validate')
def fix_validate():
    """Validate data integrity across all tables."""
    console.print("[cyan]Validating data integrity...[/cyan]")

    client = ctl.get_bq_client()

    checks = []

    # Check for duplicates
    query = f"""
    SELECT COUNT(*) as total, COUNT(DISTINCT uri) as unique_docs
    FROM `{ctl.config['project_id']}.{ctl.config['dataset']}.search_corpus`
    """
    result = list(client.query(query))[0]

    if result.total != result.unique_docs:
        checks.append(f"[red]✗ Found {result.total - result.unique_docs} duplicate documents[/red]")
    else:
        checks.append(f"[green]✓ No duplicate documents[/green]")

    # Check for missing content
    query = f"""
    SELECT COUNT(*) as missing_content
    FROM `{ctl.config['project_id']}.{ctl.config['dataset']}.search_corpus`
    WHERE text_content IS NULL OR text_content = ''
    """
    result = list(client.query(query))[0]

    if result.missing_content > 0:
        checks.append(f"[yellow]⚠ {result.missing_content} documents have no content[/yellow]")
    else:
        checks.append(f"[green]✓ All documents have content[/green]")

    # Display results
    for check in checks:
        console.print(check)


# ============= STATUS COMMAND =============
@cli.command()
def status():
    """Display comprehensive system status."""
    console.print(Panel.fit("📊 [bold cyan]System Status[/bold cyan]", border_style="cyan"))

    # Run show_status.py if available
    if Path('src/grepctl/scripts/show_status.py').exists():
        ctl.run_python_script('src/grepctl/scripts/show_status.py')
    else:
        # Fallback to basic status
        client = ctl.get_bq_client()

        query = f"""
        SELECT
            modality,
            COUNT(*) as total_docs,
            SUM(CASE WHEN ARRAY_LENGTH(embedding) = 768 THEN 1 ELSE 0 END) as with_embeddings
        FROM `{ctl.config['project_id']}.{ctl.config['dataset']}.search_corpus`
        GROUP BY modality
        ORDER BY modality
        """

        results = client.query(query).result()

        table = Table(title="Document Status")
        table.add_column("Modality", style="cyan")
        table.add_column("Documents", style="yellow")
        table.add_column("With Embeddings", style="green")

        for row in results:
            table.add_row(row.modality, str(row.total_docs), str(row.with_embeddings))

        console.print(table)


# ============= SEARCH COMMAND =============
@cli.command()
@click.argument('query')
@click.option('--top-k', '-k', default=10, help='Number of results')
@click.option('--modality', '-m', multiple=True, help='Filter by modality')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table')
def search(query, top_k, modality, output):
    """Search across all indexed documents."""

    # Use grepctl search command
    cmd = ['uv', 'run', 'grepctl', 'search', query, '-k', str(top_k), '-o', output]

    if modality:
        for m in modality:
            cmd.extend(['-s', m])

    result = ctl.run_command(cmd, check=False)

    if result.returncode == 0:
        print(result.stdout)
    else:
        console.print(f"[red]Search failed: {result.stderr}[/red]")


# ============= SERVE COMMAND =============
@cli.command()
@click.option('--host', '-h', default='0.0.0.0', help='Host to bind to')
@click.option('--port', '-p', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.option('--theme-config', type=click.Path(exists=True), help='Path to theme configuration file')
@click.option('--workers', '-w', default=1, help='Number of worker processes')
def serve(host, port, reload, theme_config, workers):
    """Start the REST API server with web UI."""
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


# ============= MAIN =============
def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()