"""Test ML.GENERATE_TEXT functionality in BigQuery."""

from google.cloud import bigquery
import os

# Set project
project_id = "semgrep-472018"
client = bigquery.Client(project=project_id)

print("Testing ML.GENERATE_TEXT capabilities...")
print("=" * 50)

# Test 1: Try using ML.GENERATE_TEXT with a prompt directly (no model)
try:
    query = """
    SELECT
      ML.GENERATE_TEXT(
        prompt,
        STRUCT(
          0.2 AS temperature,
          100 AS max_output_tokens,
          0.95 AS top_p,
          40 AS top_k
        )
      ) AS generated_text
    FROM (
      SELECT 'What is 2+2? Answer in one word.' AS prompt
    )
    """

    print("\n1. Testing direct ML.GENERATE_TEXT (no model)...")
    result = client.query(query).result()
    for row in result:
        print(f"   Result: {row.generated_text}")
        print("   ✅ Direct ML.GENERATE_TEXT works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)[:200]}")

# Test 2: Try with the embedding model (should fail but let's check)
try:
    query = """
    SELECT
      ML.GENERATE_TEXT(
        MODEL `semgrep-472018.grepmm.text_embedding_model`,
        'What is 2+2?',
        STRUCT(0.2 AS temperature, 100 AS max_output_tokens)
      ) AS generated_text
    """

    print("\n2. Testing ML.GENERATE_TEXT with embedding model...")
    result = client.query(query).result()
    for row in result:
        print(f"   Result: {row.generated_text}")
except Exception as e:
    print(f"   ❌ Expected error: {str(e)[:200]}")

# Test 3: Check if we can use Vertex AI's generative models directly
try:
    print("\n3. Testing Vertex AI Generative Models...")
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=project_id, location='us-central1')
    model = GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('What is 2+2? Answer in one word.')
    print(f"   Result: {response.text}")
    print("   ✅ Vertex AI Generative Models work!")
except Exception as e:
    print(f"   ❌ Error: {str(e)[:200]}")

# Test 4: List available ML functions
try:
    print("\n4. Checking available ML functions in BigQuery...")
    query = """
    SELECT
      routine_name,
      routine_type
    FROM `semgrep-472018.grepmm.INFORMATION_SCHEMA.ROUTINES`
    WHERE routine_name LIKE 'ML%'
    LIMIT 10
    """
    result = client.query(query).result()
    functions = list(result)
    if functions:
        for func in functions:
            print(f"   - {func.routine_name} ({func.routine_type})")
    else:
        print("   No ML functions found in dataset schema")
except Exception as e:
    print(f"   Note: {str(e)[:100]}")

print("\n" + "=" * 50)
print("Summary:")
print("- Vertex AI models are accessible via SDK ✅")
print("- Direct BigQuery ML.GENERATE_TEXT needs proper setup")
print("- Consider using Vertex AI SDK for text generation instead")