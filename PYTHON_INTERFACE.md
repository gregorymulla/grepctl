# Python Interface for Grepctl Search

## Quick Start: Semantic Search in 3 Lines

```python
from grepctl import SearchClient

client = SearchClient()
results = client.search("how to implement OAuth2 authentication", top_k=5)
```

Or even simpler with the convenience function:

```python
from grepctl import search
results = search("neural networks", top_k=5)
```

## 🎯 Smart Code Assistant

```python
"""
Build an intelligent code search assistant that understands context,
not just keywords. Ask questions in natural language!
"""

from grepctl import SearchClient
from typing import List

class CodeAssistant:
    def __init__(self):
        self.client = SearchClient()

    def ask(self, question: str) -> str:
        """Ask a question and get code examples from your codebase"""
        # Search for relevant code
        results = self.client.search(
            query=question,
            top_k=5,
            sources=['python', 'javascript', 'markdown'],
            rerank=True
        )

        if not results:
            return "No relevant code found. Try rephrasing your question."

        # Format the response
        response = f"📚 Found {len(results)} relevant examples:\n\n"

        for i, result in enumerate(results, 1):
            filename = result['uri'].split('/')[-1]
            score = result['score']

            response += f"{i}. 📄 {filename} (confidence: {score:.0%})\n"
            response += f"   ```\n   {result['content'][:200]}...\n   ```\n\n"

        return response

# Usage
assistant = CodeAssistant()
print(assistant.ask("How do I handle async errors in Python?"))
print(assistant.ask("Show me examples of REST API endpoints"))
```

## 🔍 Multi-Modal Knowledge Explorer

```python
"""
Search across PDFs, videos, images, and audio transcripts simultaneously.
Perfect for finding information scattered across different media types.
"""

from grepctl import SearchClient
from collections import defaultdict
from datetime import datetime

class KnowledgeExplorer:
    def __init__(self):
        self.client = SearchClient()
        self.search_history = []

    def explore(self, topic: str, media_types: List[str] = None) -> dict:
        """Explore a topic across different media types"""

        # Default to all media types
        if not media_types:
            media_types = ['pdf', 'video', 'audio', 'images', 'text']

        # Perform semantic search
        results = self.client.search(
            query=topic,
            top_k=30,
            sources=media_types
        )

        # Organize by media type
        organized = defaultdict(list)
        for result in results:
            source = result.get('source', 'unknown')
            organized[source].append({
                'content': result['content'][:300],
                'score': result['score'],
                'file': result['uri'].split('/')[-1],
                'metadata': result.get('metadata', {})
            })

        # Add to history
        self.search_history.append({
            'timestamp': datetime.now().isoformat(),
            'topic': topic,
            'results_count': len(results)
        })

        return dict(organized)

    def summarize_findings(self, topic: str) -> str:
        """Get a summary of findings across all media types"""
        findings = self.explore(topic)

        summary = f"🔎 Knowledge Report: {topic}\n"
        summary += "=" * 50 + "\n\n"

        for media_type, items in findings.items():
            emoji = {
                'pdf': '📄', 'video': '🎥', 'audio': '🎙️',
                'images': '🖼️', 'text': '📝'
            }.get(media_type, '📌')

            summary += f"{emoji} {media_type.upper()} ({len(items)} items)\n"

            if items:
                best = max(items, key=lambda x: x['score'])
                summary += f"  Best match: {best['file']} ({best['score']:.0%} confidence)\n"
                summary += f"  Preview: {best['content'][:100]}...\n\n"

        return summary

# Usage
explorer = KnowledgeExplorer()

# Explore a technical topic
findings = explorer.explore("machine learning deployment strategies")
for media_type, items in findings.items():
    print(f"\n{media_type}: {len(items)} relevant items found")

# Get a summary report
print(explorer.summarize_findings("kubernetes best practices"))
```

## 💡 Smart Context Retriever for RAG

```python
"""
Retrieve context-aware chunks for RAG (Retrieval Augmented Generation).
Perfect for building chatbots and Q&A systems.
"""

from grepctl import SearchClient
import re

class RAGRetriever:
    def __init__(self):
        self.client = SearchClient()
        self.context_cache = {}

    def get_context(self, question: str, max_tokens: int = 2000) -> str:
        """Get relevant context for answering a question"""

        # Check cache
        cache_key = f"{question}_{max_tokens}"
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]

        # Search for relevant content with reranking
        results = self.client.search(
            query=question,
            top_k=10,
            rerank=True
        )

        context_parts = []
        token_count = 0

        for result in results:
            # Estimate tokens (rough: 1 token ≈ 4 characters)
            chunk_tokens = len(result['content']) // 4

            if token_count + chunk_tokens > max_tokens:
                # Truncate to fit
                remaining_tokens = max_tokens - token_count
                truncated_text = result['content'][:remaining_tokens * 4]
                context_parts.append(truncated_text)
                break

            # Add source metadata
            metadata = f"[Source: {result['source']} - {result['uri'].split('/')[-1]}]\n"
            context_parts.append(metadata)
            context_parts.append(result['content'])
            context_parts.append("\n---\n")
            token_count += chunk_tokens

        context = "\n".join(context_parts)

        # Cache the result
        self.context_cache[cache_key] = context

        return context

    def answer_question(self, question: str) -> dict:
        """Get context and metadata for answering a question"""
        context = self.get_context(question)
        results = self.client.search(question, top_k=5)

        return {
            'question': question,
            'context': context,
            'sources': [
                {
                    'file': r['uri'].split('/')[-1],
                    'type': r['source'],
                    'relevance': r['score']
                }
                for r in results
            ],
            'token_count': len(context) // 4
        }

# Usage
retriever = RAGRetriever()

# Get context for a question
answer_data = retriever.answer_question("How do I implement caching in Python?")

print(f"Question: {answer_data['question']}")
print(f"Context tokens: {answer_data['token_count']}")
print(f"Sources: {len(answer_data['sources'])}")
for source in answer_data['sources']:
    print(f"  - {source['file']} ({source['type']}) - {source['relevance']:.0%} relevant")
print(f"\nContext preview:\n{answer_data['context'][:500]}...")
```

## 🚀 Batch Processing Pipeline

```python
"""
Process multiple searches efficiently.
Great for analyzing trends or bulk operations.
"""

from grepctl import SearchClient
import pandas as pd
from typing import List, Dict

class BatchSearcher:
    def __init__(self):
        self.client = SearchClient()

    def batch_search(self, queries: List[str], **search_params) -> pd.DataFrame:
        """Execute multiple searches and return as DataFrame"""
        results = []

        for query in queries:
            search_results = self.client.search(query, **search_params)
            for result in search_results:
                results.append({
                    'query': query,
                    'doc_id': result['doc_id'],
                    'source': result['source'],
                    'score': result['score'],
                    'content': result['content'][:200]
                })

        return pd.DataFrame(results)

    def analyze_topic_coverage(self, topics: List[str]) -> Dict:
        """Analyze how well different topics are covered"""

        df = self.batch_search(topics, top_k=20)

        analysis = {}
        for topic in topics:
            topic_results = df[df['query'] == topic]

            analysis[topic] = {
                'document_count': len(topic_results),
                'avg_relevance': topic_results['score'].mean() if len(topic_results) > 0 else 0,
                'source_distribution': topic_results['source'].value_counts().to_dict(),
                'top_match': topic_results.nlargest(1, 'score')['content'].values[0]
                            if len(topic_results) > 0 else "No results"
            }

        return analysis

    def find_knowledge_gaps(self, expected_topics: List[str], threshold: float = 0.7) -> List[str]:
        """Find topics that are poorly covered in your knowledge base"""
        df = self.batch_search(expected_topics, top_k=5)

        gaps = []
        for topic in expected_topics:
            topic_results = df[df['query'] == topic]

            if len(topic_results) == 0:
                gaps.append(topic)
            else:
                avg_score = topic_results['score'].mean()
                if avg_score < threshold:
                    gaps.append(topic)

        return gaps

# Usage
batch = BatchSearcher()

topics = [
    "authentication and authorization",
    "database optimization",
    "microservices architecture",
    "CI/CD pipelines",
    "error handling best practices"
]

# Get results as DataFrame
results_df = batch.batch_search(topics, top_k=5)
print(f"Found {len(results_df)} total results across {len(topics)} topics")
print(results_df.groupby('query')['score'].agg(['mean', 'max', 'count']))

# Analyze coverage
coverage = batch.analyze_topic_coverage(topics)
for topic, stats in coverage.items():
    print(f"\n📊 {topic}:")
    print(f"   Documents: {stats['document_count']}")
    print(f"   Avg relevance: {stats['avg_relevance']:.0%}")

# Find gaps
gaps = batch.find_knowledge_gaps(topics, threshold=0.6)
if gaps:
    print(f"\n⚠️ Knowledge gaps found in: {', '.join(gaps)}")
```

## 🎨 Quick Examples

```python
from grepctl import SearchClient, search

# Initialize once, use many times
client = SearchClient()

# Simple search
results = client.search("python async programming")

# Just get content strings
contents = client.search_simple("database optimization", limit=5)
for content in contents:
    print(content[:200])

# Search with filters
results = client.search(
    "security vulnerabilities",
    top_k=10,
    sources=['pdf', 'markdown'],
    rerank=True,
    regex_filter=r"CVE-\d{4}",
    start_date="2023-01-01"
)

# One-liner search without creating client
from grepctl import search
results = search("machine learning", top_k=3)

# Get system stats
stats = client.get_stats()
print(f"Documents indexed: {stats['document_count']:,}")
```

## 📊 Pandas Integration

```python
import pandas as pd
from grepctl import SearchClient

client = SearchClient()

# Search and convert to DataFrame
results = client.search("data analysis", top_k=50)
df = pd.DataFrame(results)

# Analyze results
print(df.groupby('source')['score'].agg(['mean', 'count']))
print(df.nlargest(5, 'score')[['score', 'uri', 'content']])

# Export results
df.to_csv('search_results.csv', index=False)
df.to_json('search_results.json', orient='records')
```

## 🔧 Installation

```bash
# Using uv (recommended)
uv add grepctl

# Using pip
pip install grepctl

# For development
git clone <repo>
cd bq-semgrep
uv sync
```

## ⚙️ Configuration

The SearchClient will automatically use your existing grepctl configuration from `~/.grepctl/config.yaml`:

```yaml
project_id: your-project
dataset_name: grepmm
location: us-central1
```

Or you can specify a custom config path:

```python
client = SearchClient(config_path="/path/to/config.yaml")
```

Or override the project ID:

```python
client = SearchClient(project_id="my-project-id")
```

## 📚 API Reference

### SearchClient Methods

```python
# Full search with all options
results = client.search(
    query="search text",           # Search query
    top_k=10,                      # Number of results
    sources=['pdf', 'text'],       # Filter by source types
    rerank=False,                  # Use LLM reranking
    regex_filter=r"pattern",       # Regex filter
    start_date="2023-01-01",       # Date range start
    end_date="2024-12-31"          # Date range end
)

# Simple search - just returns content strings
contents = client.search_simple("query", limit=5)

# Get system statistics
stats = client.get_stats()
```

### Convenience Function

```python
from grepctl import search

# Quick search without client
results = search("query", top_k=10, rerank=True)
```

## 🚀 Ready to Build!

You now have a powerful, simple Python API for semantic search across all your data. The SearchClient handles all the complexity of BigQuery connections, embedding models, and vector search - you just focus on building great applications!

For more examples, check out:
- `examples/search_api_example.py` - Complete working examples
- `examples/search_api_notebook.py` - Jupyter notebook examples

Happy searching! 🔍