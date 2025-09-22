"""Test Gemini model access in different regions."""

import vertexai
from vertexai.generative_models import GenerativeModel

project_id = "semgrep-472018"

# Try different regions
regions = ["us-central1", "us-east1", "us-west1", "us-east4"]

print("Testing Gemini model access in different regions...")
print("=" * 50)

for region in regions:
    try:
        print(f"\nTrying region: {region}")
        vertexai.init(project=project_id, location=region)

        # Try different model versions
        models_to_try = ["gemini-1.5-flash-002", "gemini-1.5-pro-002", "gemini-pro"]

        for model_name in models_to_try:
            try:
                model = GenerativeModel(model_name)
                response = model.generate_content("Say 'hello'", generation_config={"max_output_tokens": 10})
                print(f"  ✅ {model_name}: {response.text.strip()}")
                break  # If one works, we found a working model
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg:
                    continue
                else:
                    print(f"  ❌ {model_name}: {error_msg[:50]}...")
    except Exception as e:
        print(f"  ❌ Region error: {str(e)[:100]}")

print("\n" + "=" * 50)