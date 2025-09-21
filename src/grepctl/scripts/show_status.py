#!/usr/bin/env python3
"""
Display comprehensive system capabilities and document indexing status.
"""

from google.cloud import bigquery
from datetime import datetime

def get_status():
    """Get comprehensive system status."""

    bq = bigquery.Client(project='semgrep-472018')

    # Get statistics by modality
    query = '''
    SELECT
        modality,
        COUNT(*) as count,
        SUM(CASE WHEN embedding IS NOT NULL AND ARRAY_LENGTH(embedding) > 0 THEN 1 ELSE 0 END) as has_embedding,
        SUM(CASE WHEN text_content IS NOT NULL THEN 1 ELSE 0 END) as searchable,
        SUM(CASE
            WHEN modality = 'image' AND text_content LIKE '%Vision API%' THEN 1
            WHEN modality = 'audio' AND text_content LIKE '%Speech-to-Text%' THEN 1
            WHEN modality = 'video' AND text_content LIKE '%Video Intelligence%' THEN 1
            WHEN modality = 'pdf' AND (text_content LIKE '%Document AI%' OR text_content LIKE '%PyPDF2%') THEN 1
            WHEN modality IN ('text', 'markdown') THEN 1
            WHEN modality IN ('json', 'csv') AND text_content IS NOT NULL THEN 1
            ELSE 0
        END) as full_analysis
    FROM `semgrep-472018.grepmm.search_corpus`
    GROUP BY modality
    ORDER BY
        CASE modality
            WHEN 'text' THEN 1
            WHEN 'image' THEN 2
            WHEN 'pdf' THEN 3
            WHEN 'json' THEN 4
            WHEN 'csv' THEN 5
            WHEN 'audio' THEN 6
            WHEN 'video' THEN 7
            ELSE 8
        END
    '''

    # Separate text and markdown count
    text_query = '''
    SELECT
        SUM(CASE WHEN uri LIKE '%.txt' THEN 1 ELSE 0 END) as text_count,
        SUM(CASE WHEN uri LIKE '%.md' THEN 1 ELSE 0 END) as markdown_count,
        COUNT(*) as total_text
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE modality = 'text'
    '''

    # Get total counts
    total_query = '''
    SELECT
        COUNT(*) as total_docs,
        SUM(CASE WHEN embedding IS NOT NULL AND ARRAY_LENGTH(embedding) > 0 THEN 1 ELSE 0 END) as total_embedded,
        SUM(CASE WHEN text_content IS NOT NULL THEN 1 ELSE 0 END) as total_searchable
    FROM `semgrep-472018.grepmm.search_corpus`
    '''

    text_results = list(bq.query(text_query))
    text_count = text_results[0].text_count if text_results[0].text_count else 0
    markdown_count = text_results[0].markdown_count if text_results[0].markdown_count else 0

    total_results = list(bq.query(total_query))
    total_docs = total_results[0].total_docs
    total_embedded = total_results[0].total_embedded
    total_searchable = total_results[0].total_searchable

    # Print header
    print("\n" + "="*75)
    print(" "*20 + "🚀 GREPCTL STATUS REPORT 🚀")
    print("="*75)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Print capabilities table
    print("System Capabilities Summary:")
    print()
    print("| Modality | Count | Embeddings | Search | Enhanced Processing     |")
    print("|----------|-------|------------|--------|-------------------------|")

    results = list(bq.query(query))

    # Track statistics
    modality_stats = {}

    for row in results:
        if row.modality == 'text':
            # Split text into text and markdown
            if text_count > 0:
                print(f"| Text     | {text_count:<5} | ✅          | ✅      | ✅ Full-text indexed     |")
            if markdown_count > 0:
                print(f"| Markdown | {markdown_count:<5} | ✅          | ✅      | ✅ Full-text indexed     |")
            modality_stats['text'] = (text_count, text_count)
            modality_stats['markdown'] = (markdown_count, markdown_count)

        elif row.modality == 'pdf':
            if row.full_analysis == row.count:
                status = '✅ Document AI/PyPDF2'
            else:
                status = f'⏳ {row.full_analysis}/{row.count} extracted'

            if row.has_embedding == row.count:
                embed = '✅'
            else:
                embed = f'⏳ ({row.has_embedding}/{row.count})'

            print(f"| PDF      | {row.count:<5} | {embed:<11}| ✅      | {status:<24}|")
            modality_stats['pdf'] = (row.count, row.full_analysis)

        elif row.modality == 'image':
            if row.full_analysis == row.count:
                vision_status = '✅ Vision API analyzed'
            else:
                vision_status = f'⏳ {row.full_analysis}/{row.count} analyzed'

            embed = '✅' if row.has_embedding == row.count else f'⏳ ({row.has_embedding}/{row.count})'
            print(f"| Images   | {row.count:<5} | {embed:<11}| ✅      | {vision_status:<24}|")
            modality_stats['image'] = (row.count, row.full_analysis)

        elif row.modality == 'json':
            embed = '✅' if row.has_embedding == row.count else f'⏳ ({row.has_embedding}/{row.count})'
            status = '✅ Structured parsing' if row.searchable == row.count else f'⏳ {row.searchable}/{row.count} parsed'
            print(f"| JSON     | {row.count:<5} | {embed:<11}| ✅      | {status:<24}|")
            modality_stats['json'] = (row.count, row.searchable)

        elif row.modality == 'csv':
            embed = '✅' if row.has_embedding == row.count else f'⏳ ({row.has_embedding}/{row.count})'
            status = '✅ Tabular parsing' if row.searchable == row.count else f'⏳ {row.searchable}/{row.count} parsed'
            print(f"| CSV      | {row.count:<5} | {embed:<11}| ✅      | {status:<24}|")
            modality_stats['csv'] = (row.count, row.searchable)

        elif row.modality == 'audio':
            embed = '✅' if row.has_embedding == row.count else f'⏳ ({row.has_embedding}/{row.count})'
            if row.full_analysis == row.count:
                status = '✅ Speech-to-Text'
            else:
                status = f'⏳ {row.full_analysis}/{row.count} transcribed'
            print(f"| Audio    | {row.count:<5} | {embed:<11}| ✅      | {status:<24}|")
            modality_stats['audio'] = (row.count, row.full_analysis)

        elif row.modality == 'video':
            embed = '✅' if row.has_embedding == row.count else f'⏳ ({row.has_embedding}/{row.count})'
            if row.full_analysis == row.count:
                status = '✅ Video Intelligence'
            else:
                status = f'⏳ {row.full_analysis}/{row.count} analyzed'
            print(f"| Video    | {row.count:<5} | {embed:<11}| ✅      | {status:<24}|")
            modality_stats['video'] = (row.count, row.full_analysis)

    print()
    print("-"*75)
    print(f"TOTAL DOCUMENTS: {total_docs} | Embedded: {total_embedded} | Searchable: {total_searchable}")
    print("-"*75)

    # Print detailed status
    print("\n📊 Detailed Status:")

    # Text/Markdown
    if 'text' in modality_stats or 'markdown' in modality_stats:
        total_text = modality_stats.get('text', (0, 0))[0] + modality_stats.get('markdown', (0, 0))[0]
        print(f"  📄 Text/Markdown: {total_text} documents fully indexed ✅")

    # Images
    if 'image' in modality_stats:
        count, analyzed = modality_stats['image']
        if analyzed == count:
            print(f"  🖼️  Images: All {count} analyzed with Vision API ✅")
        else:
            print(f"  🖼️  Images: {analyzed}/{count} analyzed ({count - analyzed} pending)")

    # PDFs
    if 'pdf' in modality_stats:
        count, extracted = modality_stats['pdf']
        if extracted == count:
            print(f"  📑 PDFs: All {count} extracted ✅")
        else:
            print(f"  📑 PDFs: {extracted}/{count} extracted ({count - extracted} need processing)")

    # JSON
    if 'json' in modality_stats:
        count, parsed = modality_stats['json']
        print(f"  📊 JSON: {parsed}/{count} parsed and searchable")

    # CSV
    if 'csv' in modality_stats:
        count, parsed = modality_stats['csv']
        print(f"  📊 CSV: {parsed}/{count} parsed and searchable")

    # Audio
    if 'audio' in modality_stats:
        count, transcribed = modality_stats['audio']
        if transcribed == count:
            print(f"  🎤 Audio: All {count} transcribed with Speech-to-Text ✅")
        else:
            print(f"  🎤 Audio: {transcribed}/{count} transcribed")

    # Video
    if 'video' in modality_stats:
        count, analyzed = modality_stats['video']
        if analyzed == count:
            print(f"  🎬 Video: All {count} analyzed with Video Intelligence ✅")
        else:
            print(f"  🎬 Video: {analyzed}/{count} analyzed")

    # Print capabilities summary
    print("\n🚀 Enabled APIs and Features:")
    print("  • Vertex AI - Text embeddings (text-embedding-004)")
    print("  • Vision API - Image content analysis")
    print("  • Document AI - PDF text extraction")
    print("  • Speech-to-Text API - Audio transcription")
    print("  • Video Intelligence API - Video scene/object analysis")

    # Print next steps if needed
    print("\n📝 Next Steps:")

    has_pending = False

    # Check for documents without embeddings
    docs_without_embeddings = total_docs - total_embedded
    if docs_without_embeddings > 0:
        print(f"  1. Generate embeddings for {docs_without_embeddings} documents:")
        print("     uv run grepctl index --update")
        has_pending = True

    # Check for incomplete processing
    if 'pdf' in modality_stats and modality_stats['pdf'][1] < modality_stats['pdf'][0]:
        step_num = 2 if has_pending else 1
        print(f"  {step_num}. Complete PDF extraction:")
        print("     uv run python extract_all_pdfs_hybrid.py")
        has_pending = True

    if 'json' in modality_stats and modality_stats['json'][0] > 52:
        step_num = 3 if has_pending else 1
        print(f"  {step_num}. Ingest more JSON files:")
        print("     uv run python ingest_json_csv_fixed.py")
        has_pending = True

    if not has_pending:
        print("  ✅ All documents are indexed and ready for search!")
        print("\n  Try searching:")
        print("     uv run grepctl search 'your query here'")

    # Print command reference
    print("\n📚 Command Reference:")
    print("  Search:  uv run grepctl search 'query'")
    print("  Status:  uv run python show_status.py")
    print("  Index:   uv run grepctl index --update")
    print()
    print("  Ingest Commands by Type:")
    print("    • JSON/CSV:  uv run python ingest_json_csv_fixed.py")
    print("    • Audio:     uv run python ingest_audio_files.py")
    print("    • Video:     uv run python ingest_video_files.py")
    print("    • PDFs:      uv run python extract_all_pdfs_hybrid.py")

    print("\n" + "="*75)

if __name__ == "__main__":
    get_status()