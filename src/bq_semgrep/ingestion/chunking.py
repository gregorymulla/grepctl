"""
Document chunking for long text content.
"""

import logging
from typing import Dict, Any, List, Optional

from ..config import Config
from ..bigquery.connection import BigQueryClient
from ..bigquery.queries import QueryTemplates


logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunk long documents for better retrieval."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize document chunker."""
        self.client = client
        self.config = config
        self.queries = QueryTemplates()

    def chunk_all_documents(self) -> Dict[str, Any]:
        """Chunk all documents in the database."""
        logger.info("Starting document chunking...")

        stats = {
            'documents_processed': 0,
            'chunks_created': 0,
            'errors': 0
        }

        # Create chunks using SQL
        query = self.queries.chunk_documents(
            self.config.project_id,
            self.config.dataset_name,
            self.config.chunk_size,
            self.config.chunk_overlap
        )

        try:
            job = self.client.execute_query(query)
            job.result()

            # Get chunk count
            count_query = f"""
            SELECT COUNT(*) as count
            FROM `{self.config.project_id}.{self.config.dataset_name}.document_chunks`
            """
            result = self.client.execute_query_and_wait(count_query)
            stats['chunks_created'] = result[0]['count'] if result else 0

            logger.info(f"Created {stats['chunks_created']} chunks")

        except Exception as e:
            logger.error(f"Failed to chunk documents: {e}")
            stats['errors'] += 1

        return stats

    def chunk_document(self, text: str, doc_id: str) -> List[Dict[str, Any]]:
        """
        Chunk a single document into overlapping segments.

        Args:
            text: The text content to chunk
            doc_id: The document ID

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        if not text or len(text) <= self.config.chunk_size * 2:
            # Document is short enough, no chunking needed
            return []

        chunk_start = 0
        chunk_index = 0

        while chunk_start < len(text):
            chunk_end = min(
                chunk_start + self.config.chunk_size + self.config.chunk_overlap,
                len(text)
            )

            chunk_text = text[chunk_start:chunk_end]

            chunks.append({
                'doc_id': f"{doc_id}:{chunk_index}",
                'chunk_index': chunk_index,
                'chunk_start': chunk_start,
                'chunk_end': chunk_end,
                'text_content': chunk_text
            })

            chunk_start += self.config.chunk_size - self.config.chunk_overlap
            chunk_index += 1

        logger.debug(f"Created {len(chunks)} chunks for document {doc_id}")
        return chunks

    def smart_chunk_document(self, text: str, doc_id: str) -> List[Dict[str, Any]]:
        """
        Smart chunking that tries to respect sentence boundaries.

        Args:
            text: The text content to chunk
            doc_id: The document ID

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        if not text or len(text) <= self.config.chunk_size * 2:
            return []

        # Split into sentences (simple approach)
        sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')

        current_chunk = []
        current_length = 0
        chunk_index = 0
        chunk_start = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.config.chunk_size:
                if current_chunk:
                    # Create chunk
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'doc_id': f"{doc_id}:{chunk_index}",
                        'chunk_index': chunk_index,
                        'chunk_start': chunk_start,
                        'chunk_end': chunk_start + len(chunk_text),
                        'text_content': chunk_text
                    })

                    # Start new chunk with overlap
                    overlap_sentences = []
                    overlap_length = 0

                    # Add sentences from the end for overlap
                    for sent in reversed(current_chunk):
                        if overlap_length + len(sent) <= self.config.chunk_overlap:
                            overlap_sentences.insert(0, sent)
                            overlap_length += len(sent)
                        else:
                            break

                    current_chunk = overlap_sentences + [sentence]
                    current_length = overlap_length + sentence_length
                    chunk_start += len(chunk_text) - overlap_length
                    chunk_index += 1
                else:
                    # Single sentence is too long, use regular chunking
                    regular_chunks = self.chunk_document(sentence, f"{doc_id}_sent{chunk_index}")
                    chunks.extend(regular_chunks)
                    current_chunk = []
                    current_length = 0
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'doc_id': f"{doc_id}:{chunk_index}",
                'chunk_index': chunk_index,
                'chunk_start': chunk_start,
                'chunk_end': chunk_start + len(chunk_text),
                'text_content': chunk_text
            })

        logger.debug(f"Smart chunked document {doc_id} into {len(chunks)} chunks")
        return chunks

    def update_search_corpus(self) -> Dict[str, Any]:
        """Update the search corpus with chunked documents."""
        logger.info("Updating search corpus...")

        stats = {
            'total_documents': 0,
            'errors': 0
        }

        query = self.queries.create_search_corpus(
            self.config.project_id,
            self.config.dataset_name,
            self.config.chunk_size
        )

        try:
            job = self.client.execute_query(query)
            job.result()

            # Get document count
            count_query = f"""
            SELECT COUNT(*) as count
            FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            """
            result = self.client.execute_query_and_wait(count_query)
            stats['total_documents'] = result[0]['count'] if result else 0

            logger.info(f"Search corpus updated with {stats['total_documents']} documents")

        except Exception as e:
            logger.error(f"Failed to update search corpus: {e}")
            stats['errors'] += 1

        return stats

    def get_chunk_statistics(self) -> Dict[str, Any]:
        """Get statistics about document chunks."""
        query = f"""
        SELECT
            COUNT(DISTINCT SPLIT(doc_id, ':')[OFFSET(0)]) as original_documents,
            COUNT(*) as total_chunks,
            AVG(LENGTH(text_content)) as avg_chunk_size,
            MIN(LENGTH(text_content)) as min_chunk_size,
            MAX(LENGTH(text_content)) as max_chunk_size,
            AVG(chunk_index) as avg_chunks_per_doc
        FROM `{self.config.project_id}.{self.config.dataset_name}.document_chunks`
        """

        try:
            result = self.client.execute_query_and_wait(query)
            if result:
                return result[0]
        except Exception as e:
            logger.error(f"Failed to get chunk statistics: {e}")

        return {
            'original_documents': 0,
            'total_chunks': 0,
            'avg_chunk_size': 0,
            'min_chunk_size': 0,
            'max_chunk_size': 0,
            'avg_chunks_per_doc': 0
        }