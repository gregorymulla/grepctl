"""Enable Google Cloud services and verify model availability."""

import subprocess
import sys
from typing import List, Tuple
import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform
import click


REQUIRED_APIS = [
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "ml.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerymigration.googleapis.com",
    "bigquerystorage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "vision.googleapis.com",
    "language.googleapis.com",
    "translate.googleapis.com",
    "speech.googleapis.com",
]

FOUNDATION_MODELS = [
    "gemini-1.5-pro-002",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-1.0-pro-vision",
    "text-bison",
    "text-bison-32k",
    "code-bison",
    "code-bison-32k",
]


def enable_apis(project_id: str) -> Tuple[bool, str]:
    """Enable required Google Cloud APIs."""
    click.echo("\n📦 Enabling Google Cloud APIs...")
    click.echo("=" * 50)

    cmd = [
        "gcloud", "services", "enable",
        *REQUIRED_APIS,
        f"--project={project_id}"
    ]

    try:
        click.echo(f"Running: {' '.join(cmd[:3])} ...")
        for api in REQUIRED_APIS:
            click.echo(f"  • {api}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        if result.returncode == 0:
            click.echo(click.style("\n✓ All APIs enabled successfully!", fg="green"))
            return True, "APIs enabled"
        else:
            error_msg = result.stderr or "Unknown error"
            click.echo(click.style(f"\n✗ Error enabling APIs: {error_msg}", fg="red"))
            return False, error_msg

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        click.echo(click.style(f"\n✗ Failed to enable APIs: {error_msg}", fg="red"))
        return False, error_msg
    except FileNotFoundError:
        click.echo(click.style("\n✗ gcloud CLI not found. Please install Google Cloud SDK.", fg="red"))
        return False, "gcloud CLI not found"


def check_enabled_apis(project_id: str) -> List[str]:
    """Check which APIs are currently enabled."""
    try:
        result = subprocess.run(
            ["gcloud", "services", "list", "--enabled", f"--project={project_id}", "--format=value(config.name)"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except Exception:
        return []


def verify_models(project_id: str, location: str = "us-central1") -> Tuple[List[str], List[str]]:
    """Verify which foundation models are available."""
    click.echo("\n🤖 Verifying foundation model availability...")
    click.echo("=" * 50)

    # Initialize Vertex AI
    try:
        vertexai.init(project=project_id, location=location)
        aiplatform.init(project=project_id, location=location)
    except Exception as e:
        click.echo(click.style(f"✗ Failed to initialize Vertex AI: {e}", fg="red"))
        return [], FOUNDATION_MODELS

    available_models = []
    unavailable_models = []

    for model_name in FOUNDATION_MODELS:
        try:
            model = GenerativeModel(model_name)
            available_models.append(model_name)
            click.echo(click.style(f"✓ {model_name:<25} - Available", fg="green"))
        except Exception as e:
            unavailable_models.append(model_name)
            error_str = str(e)[:50] if len(str(e)) > 50 else str(e)
            click.echo(click.style(f"✗ {model_name:<25} - Not available: {error_str}", fg="yellow"))

    return available_models, unavailable_models


def enable_services_and_models(project_id: str = "semgrep-472018", location: str = "us-central1"):
    """Main function to enable all services and verify models."""
    click.echo(click.style("\n🚀 GrepCtl Service Enabler", fg="cyan", bold=True))
    click.echo(click.style("=" * 50, fg="cyan"))
    click.echo(f"Project: {project_id}")
    click.echo(f"Location: {location}\n")

    # Check current state
    click.echo("📋 Checking current API status...")
    enabled_apis = check_enabled_apis(project_id)
    missing_apis = [api for api in REQUIRED_APIS if api not in enabled_apis]

    if missing_apis:
        click.echo(f"Missing APIs: {', '.join(missing_apis)}")
        # Enable APIs
        success, message = enable_apis(project_id)
        if not success:
            click.echo(click.style(f"\n⚠️  Warning: Some APIs may not have been enabled: {message}", fg="yellow"))
    else:
        click.echo(click.style("✓ All required APIs are already enabled!", fg="green"))

    # Verify models
    available, unavailable = verify_models(project_id, location)

    # Summary
    click.echo("\n" + "=" * 50)
    click.echo(click.style("📊 Summary", fg="cyan", bold=True))
    click.echo("=" * 50)

    # Re-check APIs after enabling
    enabled_apis = check_enabled_apis(project_id)
    enabled_count = len([api for api in REQUIRED_APIS if api in enabled_apis])

    click.echo(f"\n✓ APIs Enabled: {enabled_count}/{len(REQUIRED_APIS)}")
    for api in REQUIRED_APIS:
        if api in enabled_apis:
            click.echo(click.style(f"  ✓ {api}", fg="green"))
        else:
            click.echo(click.style(f"  ✗ {api}", fg="red"))

    click.echo(f"\n✓ Models Available: {len(available)}/{len(FOUNDATION_MODELS)}")

    if unavailable:
        click.echo("\n⚠️  Some models are not available. This is normal if you don't have access to all model families.")

    click.echo("\n" + "=" * 50)
    if enabled_count == len(REQUIRED_APIS) and available:
        click.echo(click.style("✅ Setup complete! Your environment is ready.", fg="green", bold=True))
        click.echo("\nYou can now use grepctl commands with AI features.")
    else:
        click.echo(click.style("⚠️  Setup partially complete. Some features may be limited.", fg="yellow"))
        click.echo("\nPlease check your Google Cloud project permissions and quotas.")

    return enabled_count == len(REQUIRED_APIS), len(available) > 0


if __name__ == "__main__":
    enable_services_and_models()