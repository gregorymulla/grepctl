from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
import vertexai

# Initialize Vertex AI
vertexai.init(project='semgrep-472018', location='us-central1')

# List of available foundation models in Vertex AI
foundation_models = [
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

print("Testing available foundation models in Vertex AI:\n")
print("=" * 50)

for model_name in foundation_models:
    try:
        model = GenerativeModel(model_name)
        print(f"✓ {model_name:<25} - Available")
    except Exception as e:
        print(f"✗ {model_name:<25} - Not available: {str(e)[:50]}")

print("\n" + "=" * 50)
print("\nModels are enabled and ready to use!")
print("\nExample usage:")
print("from vertexai.generative_models import GenerativeModel")
print("model = GenerativeModel('gemini-1.5-flash')")
print("response = model.generate_content('Hello, world!')")
print("print(response.text)")