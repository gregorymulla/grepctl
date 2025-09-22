from google.cloud import aiplatform

aiplatform.init(project='semgrep-472018', location='us-central1')

print("Listing all models in the project...")
# List all models without filter
models = aiplatform.Model.list()

if models:
    for model in models:
        print(f"Model: {model.display_name} (Resource: {model.resource_name})")
else:
    print("No models found in the project.")

# Also try to list available foundation models
print("\nTrying to access foundation models...")
try:
    from vertexai.generative_models import GenerativeModel

    # Test with a known model
    model = GenerativeModel("gemini-1.5-flash")
    print("Successfully initialized Gemini 1.5 Flash model")
except Exception as e:
    print(f"Error accessing foundation models: {e}")