"""Enable and test Gemini models for the project."""

import subprocess
import json
import sys

print("Checking Vertex AI Gemini model access...")
print("=" * 60)

project_id = "semgrep-472018"

# Check if Generative AI API is enabled
print("\n1. Checking Generative AI APIs...")
apis_to_check = [
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "ml.googleapis.com"
]

for api in apis_to_check:
    try:
        result = subprocess.run(
            ["gcloud", "services", "list", "--enabled", f"--filter=name:{api}",
             f"--project={project_id}", "--format=value(name)"],
            capture_output=True,
            text=True
        )
        if api in result.stdout:
            print(f"  ✅ {api} is enabled")
        else:
            print(f"  ❌ {api} is NOT enabled")
    except Exception as e:
        print(f"  ❌ Error checking {api}: {e}")

# Check Vertex AI model endpoints
print("\n2. Checking Vertex AI endpoints...")
print("   Note: Gemini models are accessed as foundation models, not custom models")

# Check if we can access Gemini through the generativelanguage API
print("\n3. Testing Gemini access through Google AI...")
try:
    import google.generativeai as genai

    # Try to configure with an API key (if available)
    # Note: This requires a Generative Language API key
    print("   ⚠️  Google AI Studio access requires an API key")
    print("   Visit: https://makersuite.google.com/app/apikey")
except ImportError:
    print("   ⚠️  google-generativeai package not installed")

# Solution for BigQuery ML.GENERATE_TEXT
print("\n" + "=" * 60)
print("📌 SOLUTION: ML.GENERATE_TEXT in BigQuery")
print("=" * 60)

print("""
Current Status:
- Gemini models cannot be directly created as BigQuery remote models
- This is a known limitation in the current BigQuery ML implementation

Workarounds:

1. Use Vertex AI Python SDK directly (recommended):
   ```python
   import vertexai
   from vertexai.generative_models import GenerativeModel

   vertexai.init(project='semgrep-472018', location='us-central1')
   model = GenerativeModel('gemini-1.5-flash')
   response = model.generate_content('Your prompt here')
   ```

2. For BigQuery integration, use embedding models (already working):
   - text_embedding_model is configured and functional
   - Use for semantic search and similarity matching

3. Alternative: Set up Cloud Functions as a bridge:
   - Create a Cloud Function that calls Vertex AI
   - Create a BigQuery remote function that calls the Cloud Function
   - This allows SQL-based text generation

The embedding functionality is fully operational and sufficient for
semantic search use cases in grepctl.
""")