"""Setup and test ML.GENERATE_TEXT functionality for BigQuery."""

import subprocess
import json
from google.cloud import bigquery
import click
from typing import Dict, Any, Tuple


def check_ml_generate_text_status(project_id: str) -> Dict[str, Any]:
    """Check the current status of ML.GENERATE_TEXT capability."""
    client = bigquery.Client(project=project_id)
    status = {
        "available": False,
        "method": None,
        "models": [],
        "errors": [],
        "recommendations": []
    }

    # Check 1: Try to list existing models
    try:
        query = f"""
        SELECT
          model_name,
          model_type,
          creation_time
        FROM `{project_id}.grepmm.INFORMATION_SCHEMA.MODELS`
        """
        result = client.query(query).result()
        models = list(result)
        for model in models:
            status["models"].append({
                "name": model.model_name,
                "type": model.model_type,
                "created": str(model.creation_time)
            })
    except Exception as e:
        status["errors"].append(f"Cannot list models: {str(e)[:100]}")

    # Check 2: Verify Vertex AI connection exists
    try:
        cmd = ['bq', 'ls', '--connection', '--location=us',
               '--project_id=' + project_id, '--format=json']
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        connections = json.loads(output) if output else []

        has_vertex_connection = False
        for conn in connections:
            conn_name = conn.get('name', '') if isinstance(conn, dict) else ''
            if 'vertex-ai' in conn_name.lower():
                has_vertex_connection = True
                break

        if not has_vertex_connection:
            status["errors"].append("No Vertex AI connection found")
            status["recommendations"].append(
                "Create a Vertex AI connection in BigQuery Console or via CLI"
            )
    except Exception as e:
        status["errors"].append(f"Cannot check connections: {str(e)[:100]}")

    # Check 3: Test if we can use ML.GENERATE_EMBEDDING (which we know works)
    try:
        query = f"""
        SELECT ARRAY_LENGTH(ml_generate_embedding_result) as dim
        FROM ML.GENERATE_EMBEDDING(
            MODEL `{project_id}.grepmm.text_embedding_model`,
            (SELECT 'test' as content)
        )
        """
        result = client.query(query).result()
        dim = list(result)[0].dim
        if dim > 0:
            status["available"] = True
            status["method"] = "embedding_model"
    except Exception as e:
        pass

    # Provide recommendations based on current state
    if not status["available"]:
        status["recommendations"].extend([
            "ML.GENERATE_TEXT in BigQuery requires specific model setup",
            "Current Google Cloud limitations:",
            "  - Gemini models cannot be created as BigQuery remote models",
            "  - PaLM/Bison models are being deprecated",
            "Alternative solutions:",
            "  1. Use Vertex AI SDK directly for text generation",
            "  2. Create a Cloud Function to wrap Vertex AI calls",
            "  3. Use the embedding model for semantic search (already working)"
        ])

    return status


def setup_alternative_text_generation(project_id: str) -> Dict[str, Any]:
    """Setup alternative text generation using Cloud Functions."""
    setup_guide = {
        "method": "cloud_function_wrapper",
        "steps": [],
        "code_samples": {}
    }

    # Step 1: Cloud Function code
    setup_guide["code_samples"]["cloud_function"] = '''
import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
import json

@functions_framework.http
def generate_text(request):
    """HTTP Cloud Function for text generation."""
    request_json = request.get_json(silent=True)

    prompt = request_json.get('prompt', '')
    model_name = request_json.get('model', 'gemini-1.5-flash-002')
    temperature = request_json.get('temperature', 0.7)
    max_tokens = request_json.get('max_output_tokens', 1024)

    try:
        vertexai.init(project='PROJECT_ID', location='us-central1')
        model = GenerativeModel(model_name)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )

        return json.dumps({"generated_text": response.text})
    except Exception as e:
        return json.dumps({"error": str(e)}), 500
'''

    # Step 2: BigQuery Remote Function
    setup_guide["code_samples"]["bigquery_function"] = f'''
CREATE OR REPLACE FUNCTION `{project_id}.grepmm.generate_text`(prompt STRING)
RETURNS STRING
REMOTE WITH CONNECTION `us.vertex-ai-connection`
OPTIONS (
    endpoint = 'https://YOUR-REGION-YOUR-PROJECT.cloudfunctions.net/generate-text',
    max_batching_rows = 1
);
'''

    # Step 3: Usage example
    setup_guide["code_samples"]["usage"] = f'''
SELECT
  prompt,
  `{project_id}.grepmm.generate_text`(prompt) AS generated_text
FROM (
  SELECT 'Explain quantum computing in one sentence' AS prompt
  UNION ALL
  SELECT 'What is the capital of France?'
);
'''

    setup_guide["steps"] = [
        "Deploy Cloud Function with the provided code",
        "Create BigQuery remote function pointing to Cloud Function",
        "Use the function in SQL queries for text generation"
    ]

    return setup_guide


def display_ml_status(project_id: str = "semgrep-472018"):
    """Display comprehensive ML.GENERATE_TEXT status and setup guide."""
    click.echo(click.style("\n📊 ML.GENERATE_TEXT Status Report", fg="cyan", bold=True))
    click.echo("=" * 60)

    # Check current status
    status = check_ml_generate_text_status(project_id)

    # Display status
    if status["available"]:
        click.echo(click.style("✅ ML capabilities are available", fg="green"))
        click.echo(f"   Method: {status['method']}")
    else:
        click.echo(click.style("⚠️  ML.GENERATE_TEXT not directly available", fg="yellow"))

    # Display models
    if status["models"]:
        click.echo("\n📦 Existing Models:")
        for model in status["models"]:
            click.echo(f"   • {model['name']} ({model['type']})")

    # Display errors
    if status["errors"]:
        click.echo("\n❌ Issues Found:")
        for error in status["errors"]:
            click.echo(f"   • {error}")

    # Display recommendations
    if status["recommendations"]:
        click.echo("\n💡 Recommendations:")
        for rec in status["recommendations"]:
            click.echo(f"   {rec}")

    # Provide alternative setup
    click.echo("\n" + "=" * 60)
    click.echo(click.style("🔧 Alternative Setup Guide", fg="cyan", bold=True))
    click.echo("=" * 60)

    setup = setup_alternative_text_generation(project_id)

    click.echo("\nRecommended Approach: Cloud Function Wrapper")
    click.echo("\nSteps:")
    for i, step in enumerate(setup["steps"], 1):
        click.echo(f"  {i}. {step}")

    click.echo("\n📝 For detailed implementation, check the generated code samples.")
    click.echo("   The embedding model is working and can be used for semantic search.")

    # Save setup guide to file
    with open("ml_generate_text_setup.md", "w") as f:
        f.write("# ML.GENERATE_TEXT Setup Guide\n\n")
        f.write("## Current Status\n")
        f.write(f"- Project: {project_id}\n")
        f.write(f"- ML Available: {status['available']}\n")
        f.write(f"- Working Models: {len(status['models'])}\n\n")

        f.write("## Alternative Implementation\n\n")
        f.write("### Cloud Function Code\n")
        f.write("```python\n")
        f.write(setup["code_samples"]["cloud_function"])
        f.write("\n```\n\n")

        f.write("### BigQuery Remote Function\n")
        f.write("```sql\n")
        f.write(setup["code_samples"]["bigquery_function"])
        f.write("\n```\n\n")

        f.write("### Usage Example\n")
        f.write("```sql\n")
        f.write(setup["code_samples"]["usage"])
        f.write("\n```\n")

    click.echo("\n✅ Setup guide saved to: ml_generate_text_setup.md")


if __name__ == "__main__":
    display_ml_status()