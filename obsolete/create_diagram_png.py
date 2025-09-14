#!/usr/bin/env python3
"""
Create PNG architecture diagram for BigQuery Semantic Grep using matplotlib.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Create figure and axis
fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(5, 9.5, 'BigQuery Semantic Grep Architecture',
        fontsize=20, fontweight='bold', ha='center')
ax.text(5, 9.2, 'From Data Lake to Searchable Index',
        fontsize=14, ha='center', style='italic', color='gray')

# Define colors
color_gcs = '#4285F4'  # Google Blue
color_process = '#34A853'  # Google Green
color_apis = '#FBBC04'  # Google Yellow
color_bq = '#EA4335'  # Google Red
color_vertex = '#9333EA'  # Purple
color_search = '#10B981'  # Emerald

# 1. GCS Data Lake
gcs_box = FancyBboxPatch((0.5, 7), 9, 1.5,
                          boxstyle="round,pad=0.1",
                          facecolor=color_gcs, alpha=0.2,
                          edgecolor=color_gcs, linewidth=2)
ax.add_patch(gcs_box)
ax.text(5, 8, 'GCS DATA LAKE', fontsize=14, fontweight='bold', ha='center')
ax.text(5, 7.6, 'gcm-data-lake', fontsize=11, ha='center', style='italic')

# Document types
docs = ['📄 Text/MD', '📑 PDF', '🖼️ Images', '📊 JSON/CSV',
        '🎵 Audio', '🎬 Video']
x_positions = [1.5, 3, 4.5, 6, 7.5, 9]
for i, (x, doc) in enumerate(zip(x_positions, docs)):
    ax.text(x, 7.3, doc, fontsize=10, ha='center')

# 2. grepctl CLI
grepctl_box = FancyBboxPatch((1, 5.5), 8, 1,
                              boxstyle="round,pad=0.1",
                              facecolor=color_process, alpha=0.2,
                              edgecolor=color_process, linewidth=2)
ax.add_patch(grepctl_box)
ax.text(5, 6.2, 'GREPCTL CLI', fontsize=14, fontweight='bold', ha='center')
ax.text(5, 5.8, '$ grepctl init all --auto-ingest',
        fontsize=11, ha='center', family='monospace',
        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

# 3. Processing Layer
# Ingestion Scripts
ingest_box = FancyBboxPatch((0.5, 3.5), 2.5, 1.5,
                             boxstyle="round,pad=0.1",
                             facecolor='lightblue', alpha=0.3,
                             edgecolor='blue', linewidth=1)
ax.add_patch(ingest_box)
ax.text(1.75, 4.6, 'INGESTION', fontsize=12, fontweight='bold', ha='center')
scripts = ['bq-semgrep', 'extract_pdfs', 'ingest_*']
for i, script in enumerate(scripts):
    ax.text(1.75, 4.2 - i*0.25, f'• {script}', fontsize=9, ha='center')

# Google APIs
api_box = FancyBboxPatch((3.5, 3.5), 3, 1.5,
                          boxstyle="round,pad=0.1",
                          facecolor=color_apis, alpha=0.2,
                          edgecolor=color_apis, linewidth=1)
ax.add_patch(api_box)
ax.text(5, 4.6, 'GOOGLE APIS', fontsize=12, fontweight='bold', ha='center')
apis = ['Vision • Document AI', 'Speech • Video Intel', 'Vertex AI']
for i, api in enumerate(apis):
    ax.text(5, 4.2 - i*0.25, api, fontsize=9, ha='center')

# Processing
process_box = FancyBboxPatch((7, 3.5), 2.5, 1.5,
                              boxstyle="round,pad=0.1",
                              facecolor='lightcoral', alpha=0.3,
                              edgecolor='red', linewidth=1)
ax.add_patch(process_box)
ax.text(8.25, 4.6, 'PROCESSING', fontsize=12, fontweight='bold', ha='center')
processes = ['Extract', 'Transform', 'Clean']
for i, proc in enumerate(processes):
    ax.text(8.25, 4.2 - i*0.25, f'• {proc}', fontsize=9, ha='center')

# 4. BigQuery Dataset
bq_box = FancyBboxPatch((1, 2), 8, 1,
                         boxstyle="round,pad=0.1",
                         facecolor=color_bq, alpha=0.2,
                         edgecolor=color_bq, linewidth=2)
ax.add_patch(bq_box)
ax.text(5, 2.7, 'BIGQUERY DATASET (mmgrep)', fontsize=14, fontweight='bold', ha='center')
ax.text(5, 2.3, 'Table: search_corpus | 425+ documents | uri • modality • text_content • embedding',
        fontsize=10, ha='center', style='italic')

# 5. Vertex AI Embeddings
vertex_box = FancyBboxPatch((2, 0.8), 6, 0.8,
                             boxstyle="round,pad=0.1",
                             facecolor=color_vertex, alpha=0.2,
                             edgecolor=color_vertex, linewidth=2)
ax.add_patch(vertex_box)
ax.text(5, 1.3, 'VERTEX AI EMBEDDINGS', fontsize=12, fontweight='bold', ha='center', color='white',
        bbox=dict(boxstyle="round,pad=0.3", facecolor=color_vertex, alpha=0.8))
ax.text(5, 0.95, 'text-embedding-004 → 768-dimensional vectors', fontsize=10, ha='center', style='italic')

# 6. Search Results
search_box = FancyBboxPatch((2.5, 0), 5, 0.5,
                             boxstyle="round,pad=0.1",
                             facecolor=color_search, alpha=0.2,
                             edgecolor=color_search, linewidth=2)
ax.add_patch(search_box)
ax.text(5, 0.25, 'SEMANTIC SEARCH (VECTOR_SEARCH)', fontsize=11, fontweight='bold', ha='center')

# Add arrows showing data flow
arrow_props = dict(arrowstyle='->', lw=2, color='gray', alpha=0.6)

# GCS to grepctl
ax.annotate('', xy=(5, 5.5), xytext=(5, 7),
            arrowprops=arrow_props)

# grepctl to processing layer
ax.annotate('', xy=(1.75, 3.5), xytext=(3, 5.5),
            arrowprops=arrow_props)
ax.annotate('', xy=(5, 3.5), xytext=(5, 5.5),
            arrowprops=arrow_props)
ax.annotate('', xy=(8.25, 3.5), xytext=(7, 5.5),
            arrowprops=arrow_props)

# Processing to BigQuery
ax.annotate('', xy=(5, 2), xytext=(1.75, 3.5),
            arrowprops=arrow_props)
ax.annotate('', xy=(5, 2), xytext=(5, 3.5),
            arrowprops=arrow_props)
ax.annotate('', xy=(5, 2), xytext=(8.25, 3.5),
            arrowprops=arrow_props)

# BigQuery to Vertex AI
ax.annotate('', xy=(5, 0.8), xytext=(5, 2),
            arrowprops=dict(arrowstyle='<->', lw=2, color=color_vertex, alpha=0.6))

# Vertex AI to Search
ax.annotate('', xy=(5, 0), xytext=(5, 0.8),
            arrowprops=arrow_props)

# Add legend
legend_elements = [
    patches.Patch(color=color_gcs, alpha=0.5, label='Storage'),
    patches.Patch(color=color_process, alpha=0.5, label='Orchestration'),
    patches.Patch(color=color_apis, alpha=0.5, label='AI/ML APIs'),
    patches.Patch(color=color_bq, alpha=0.5, label='BigQuery'),
    patches.Patch(color=color_vertex, alpha=0.5, label='Embeddings'),
    patches.Patch(color=color_search, alpha=0.5, label='Search')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

# Add annotations
ax.text(0.2, 6, 'INPUT', fontsize=10, fontweight='bold', rotation=90, va='center')
ax.text(0.2, 2.5, 'PROCESS', fontsize=10, fontweight='bold', rotation=90, va='center')
ax.text(0.2, 0.5, 'OUTPUT', fontsize=10, fontweight='bold', rotation=90, va='center')

# Save the figure
plt.tight_layout()
plt.savefig('bq_semgrep_architecture.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

# Create a simplified flow diagram
fig2, ax2 = plt.subplots(1, 1, figsize=(12, 8))
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis('off')

# Title
ax2.text(5, 9.5, 'BigQuery Semantic Grep - Data Flow',
         fontsize=18, fontweight='bold', ha='center')

# Define positions for flow
positions = [
    (5, 8, 'Data Lake\n(8 modalities)', color_gcs),
    (5, 6.5, 'grepctl CLI\n(orchestration)', color_process),
    (5, 5, 'Processing\n(APIs + Scripts)', color_apis),
    (5, 3.5, 'BigQuery\n(storage)', color_bq),
    (5, 2, 'Embeddings\n(768-dim)', color_vertex),
    (5, 0.5, 'Search\n(results)', color_search)
]

# Draw boxes and text
for x, y, text, color in positions:
    box = FancyBboxPatch((x-1.5, y-0.4), 3, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor=color, alpha=0.3,
                          edgecolor=color, linewidth=2)
    ax2.add_patch(box)
    ax2.text(x, y, text, fontsize=12, ha='center', va='center', fontweight='bold')

# Draw arrows between boxes
for i in range(len(positions)-1):
    ax2.annotate('', xy=(5, positions[i+1][1]+0.4), xytext=(5, positions[i][1]-0.4),
                arrowprops=dict(arrowstyle='->', lw=3, color='gray', alpha=0.7))

# Add side annotations
ax2.text(1, 8, '• Text/Markdown\n• PDF • Images\n• JSON/CSV\n• Audio • Video',
         fontsize=9, va='center')
ax2.text(9, 6.5, 'One command:\ngrepctl init all\n--auto-ingest',
         fontsize=9, ha='center', va='center',
         bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5))
ax2.text(1, 5, '• Vision API\n• Document AI\n• Speech-to-Text\n• Video Intel',
         fontsize=9, va='center')
ax2.text(9, 3.5, 'Table:\nsearch_corpus', fontsize=9, ha='center', va='center')
ax2.text(1, 2, 'ML.GENERATE\n_EMBEDDING()', fontsize=9, va='center')
ax2.text(9, 0.5, 'VECTOR_SEARCH\n+ Cosine similarity', fontsize=9, ha='center', va='center')

# Save the flow diagram
plt.tight_layout()
plt.savefig('bq_semgrep_flow.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

print("✅ PNG diagrams created successfully:")
print("  - bq_semgrep_architecture.png - Complete system architecture")
print("  - bq_semgrep_flow.png - Simplified data flow")
print("\nThe diagrams show how the system transforms a data lake with multiple")
print("document types into a searchable index using BigQuery and Google Cloud AI.")