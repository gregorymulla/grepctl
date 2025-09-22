#!/usr/bin/env python3
"""
Test script to verify Vertex AI model setup for ML.GENERATE_TEXT.
"""

from google.cloud import bigquery
import sys

def test_vertex_ai_models():
    """Test if Vertex AI models can be created and used."""

    client = bigquery.Client(project='semgrep-472018')

    print("Testing Vertex AI model setup...")
    print("=" * 70)

    # Test different model endpoints
    models_to_test = [
        ('gemini-1.5-flash', 'Latest Gemini Flash model'),
        ('gemini-1.5-pro', 'Gemini Pro model'),
        ('gemini-pro', 'Gemini Pro (older version)'),
        ('text-bison', 'Text Bison model'),
        ('text-bison-32k', 'Text Bison 32k context'),
    ]

    successful_models = []

    for model_name, description in models_to_test:
        print(f"\nTesting {description} ({model_name})...")

        try:
            # Try to create a temporary model
            query = f"""
            CREATE OR REPLACE MODEL `semgrep-472018.grepmm.test_model_{model_name.replace('-', '_').replace('.', '_')}`
            REMOTE WITH CONNECTION `us.vertex-ai-connection`
            OPTIONS (ENDPOINT = '{model_name}')
            """

            job = client.query(query)
            job.result(timeout=10)

            print(f"✓ Successfully created model with endpoint: {model_name}")
            successful_models.append(model_name)

            # Clean up test model
            cleanup = f"DROP MODEL IF EXISTS `semgrep-472018.grepmm.test_model_{model_name.replace('-', '_').replace('.', '_')}`"
            client.query(cleanup).result()

        except Exception as e:
            error_msg = str(e)
            if "Not found" in error_msg:
                print(f"✗ Model not available: {model_name}")
            elif "Unsupported" in error_msg:
                print(f"✗ Unsupported endpoint: {model_name}")
            else:
                print(f"✗ Error: {error_msg[:100]}...")

    print("\n" + "=" * 70)

    if successful_models:
        print(f"✓ Found {len(successful_models)} working model(s):")
        for model in successful_models:
            print(f"  - {model}")

        # Create the actual text model with the first successful one
        model_to_use = successful_models[0]
        print(f"\nCreating text_model with endpoint: {model_to_use}")

        try:
            query = f"""
            CREATE OR REPLACE MODEL `semgrep-472018.grepmm.text_model`
            REMOTE WITH CONNECTION `us.vertex-ai-connection`
            OPTIONS (ENDPOINT = '{model_to_use}')
            """
            job = client.query(query)
            job.result()
            print("✓ Successfully created text_model")

            # Test ML.GENERATE_TEXT
            test_query = """
            SELECT ML.GENERATE_TEXT(
                MODEL `semgrep-472018.grepmm.text_model`,
                'Say "Hello, ML.GENERATE_TEXT is working!"',
                STRUCT(0.2 AS temperature, 100 AS max_output_tokens)
            ) AS result
            """
            result = client.query(test_query).result()
            for row in result:
                print(f"\nTest ML.GENERATE_TEXT output:")
                print(row.result)

        except Exception as e:
            print(f"✗ Failed to create or test text_model: {e}")

    else:
        print("✗ No working Vertex AI models found.")
        print("\nTo enable ML.GENERATE_TEXT, you need to:")
        print("1. Enable the Vertex AI API in your project")
        print("2. Ensure the service account has proper permissions")
        print("3. Check if the models are available in your region (us-central1)")
        print("4. You may need to enable specific model APIs or request access")
        print("\nFor now, the system will use fallback methods for text extraction.")

    return successful_models

if __name__ == "__main__":
    models = test_vertex_ai_models()
    sys.exit(0 if models else 1)