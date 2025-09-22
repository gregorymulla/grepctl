from google.cloud import aiplatform

aiplatform.init(project='semgrep-472018', location='us-central1')

# List all available models
models = aiplatform.Model.list(
    filter='labels.google_vertex_llm_model_type:*'
)
for model in models:
    print(f"Model: {model.display_name}")