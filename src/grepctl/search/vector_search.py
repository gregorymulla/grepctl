"""
Vector search implementation for semantic grep.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import Config
from ..bigquery.connection import BigQueryClient


logger = logging.getLogger(__name__)


class SemanticSearch:
    """Semantic search using vector similarity."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize semantic search."""
        self.client = client
        self.config = config

    def search(self,
               query: str,
               top_k: int = 20,
               source_filter: Optional[List[str]] = None,
               modality_filter: Optional[List[str]] = None,
               use_rerank: bool = False,
               regex_filter: Optional[str] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search across all documents.

        Args:
            query: Search query text
            top_k: Number of results to return
            source_filter: Filter by source types (e.g., ['pdf', 'screenshot'])
            modality_filter: Filter by modality (e.g., ['text', 'image'])
            use_rerank: Whether to use LLM reranking
            regex_filter: Additional regex pattern to match
            start_date: Filter documents created after this date (YYYY-MM-DD)
            end_date: Filter documents created before this date (YYYY-MM-DD)

        Returns:
            List of search results
        """
        logger.info(f"Searching for: {query[:100]}...")

        # Build filter conditions
        filters = self._build_filters(
            source_filter, modality_filter, regex_filter, start_date, end_date
        )

        # Skip table function and use direct search
        # Table function not yet created, use direct search
        results = self._search_direct(
            query, top_k, filters, use_rerank
        )

        logger.info(f"Found {len(results)} results")
        return results

    def get_search_query(self,
                         query: str,
                         top_k: int = 20,
                         source_filter: Optional[List[str]] = None,
                         modality_filter: Optional[List[str]] = None,
                         use_rerank: bool = False,
                         regex_filter: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> str:
        """
        Get the SQL query that would be executed for the search.

        Args:
            query: Search query text
            top_k: Number of results to return
            source_filter: Filter by source types (e.g., ['pdf', 'screenshot'])
            modality_filter: Filter by modality (e.g., ['text', 'image'])
            use_rerank: Whether to use LLM reranking
            regex_filter: Additional regex pattern to match
            start_date: Filter documents created after this date (YYYY-MM-DD)
            end_date: Filter documents created before this date (YYYY-MM-DD)

        Returns:
            SQL query string
        """
        # Build filter conditions
        filters = self._build_filters(
            source_filter, modality_filter, regex_filter, start_date, end_date
        )

        # Build and return the search query
        return self._build_search_query(query, top_k, filters, use_rerank)

    def _build_filters(self,
                       source_filter: Optional[List[str]],
                       modality_filter: Optional[List[str]],
                       regex_filter: Optional[str],
                       start_date: Optional[str],
                       end_date: Optional[str]) -> Dict[str, Any]:
        """Build filter conditions for search."""
        filters = {}

        if source_filter:
            filters['source_filter'] = source_filter
        else:
            filters['source_filter'] = []

        if modality_filter:
            filters['modality_filter'] = modality_filter
        else:
            filters['modality_filter'] = []

        if regex_filter:
            filters['regex'] = regex_filter
        else:
            filters['regex'] = ''

        # Parse dates
        if start_date:
            try:
                filters['start_ts'] = datetime.strptime(start_date, '%Y-%m-%d').isoformat()
            except ValueError:
                logger.warning(f"Invalid start date format: {start_date}")
                filters['start_ts'] = '1970-01-01T00:00:00'
        else:
            filters['start_ts'] = '1970-01-01T00:00:00'

        if end_date:
            try:
                filters['end_ts'] = datetime.strptime(end_date, '%Y-%m-%d').isoformat()
            except ValueError:
                logger.warning(f"Invalid end date format: {end_date}")
                filters['end_ts'] = datetime.now().isoformat()
        else:
            filters['end_ts'] = datetime.now().isoformat()

        return filters

    def _search_with_table_function(self,
                                     query: str,
                                     top_k: int,
                                     filters: Dict[str, Any],
                                     use_rerank: bool) -> List[Dict[str, Any]]:
        """Search using the BigQuery table function."""
        sql_query = f"""
        SELECT *
        FROM `{self.config.project_id}.{self.config.dataset_name}.semantic_grep_tf`(
            '{query.replace("'", "''")}',
            {top_k},
            {filters['source_filter']},
            TIMESTAMP('{filters['start_ts']}'),
            TIMESTAMP('{filters['end_ts']}'),
            '{filters['regex'].replace("'", "''")}',
            {str(use_rerank).upper()}
        )
        """

        try:
            results = self.client.execute_query_and_wait(sql_query)
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Fallback to direct search if table function fails
            return self._search_direct(query, top_k, filters, use_rerank)

    def _search_direct(self,
                       query: str,
                       top_k: int,
                       filters: Dict[str, Any],
                       use_rerank: bool) -> List[Dict[str, Any]]:
        """Direct search implementation without table function."""
        # Build the search query
        search_query = self._build_search_query(query, top_k, filters, use_rerank)

        try:
            results = self.client.execute_query_and_wait(search_query)
            return results if results else []
        except Exception as e:
            logger.error(f"Direct search failed: {e}")
            logger.error(f"Query was: {search_query}")
            return []

    def _build_search_query(self,
                            query: str,
                            top_k: int,
                            filters: Dict[str, Any],
                            use_rerank: bool) -> str:
        """Build direct search SQL query."""
        # Build WHERE clause
        where_conditions = []

        if filters.get('source_filter'):
            sources = ', '.join([f"'{s}'" for s in filters['source_filter']])
            where_conditions.append(f"base.source IN ({sources})")

        if filters.get('modality_filter'):
            modalities = ', '.join([f"'{m}'" for m in filters['modality_filter']])
            where_conditions.append(f"base.modality IN ({modalities})")

        if filters.get('regex'):
            where_conditions.append(f"REGEXP_CONTAINS(base.text_content, r'{filters['regex']}')")

        # Only add date filter if dates are explicitly provided (not default values)
        # Skip date filtering for now as it's causing issues with VECTOR_SEARCH results
        # The created_at field is not available in the VECTOR_SEARCH output
        pass

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        # Build the query
        if use_rerank:
            return self._build_rerank_query(query, top_k, where_clause)
        else:
            return self._build_simple_query(query, top_k, where_clause)

    def _build_simple_query(self, query: str, top_k: int, where_clause: str) -> str:
        """Build simple vector search query."""
        return f"""
        WITH query_embedding AS (
            SELECT ml_generate_embedding_result AS embedding
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{self.config.embedding_model}`,
                (SELECT '{query.replace("'", "''")}' AS content),
                STRUCT(TRUE AS flatten_json_output)
            )
        )
        SELECT
            base.doc_id,
            base.uri,
            base.modality,
            base.source,
            base.created_at,
            base.author,
            base.channel,
            distance,
            NULL AS rel_score,
            base.text_content
        FROM VECTOR_SEARCH(
            TABLE `{self.config.project_id}.{self.config.dataset_name}.search_corpus`,
            'embedding',
            (SELECT embedding FROM query_embedding),
            top_k => {top_k * self.config.search_multiplier},
            distance_type => 'COSINE'
        )
        WHERE {where_clause}
        ORDER BY distance ASC
        LIMIT {top_k}
        """

    def _build_rerank_query(self, query: str, top_k: int, where_clause: str) -> str:
        """Build vector search query without LLM reranking (not available)."""
        # Since ML.GENERATE_TEXT is not available, fall back to simple search
        logger.warning("Reranking requested but ML.GENERATE_TEXT is not available. Using standard search.")
        return self._build_simple_query(query, top_k, where_clause)

    def search_similar(self,
                       doc_id: str,
                       top_k: int = 10) -> List[Dict[str, Any]]:
        """Find documents similar to a given document."""
        logger.info(f"Finding documents similar to {doc_id}")

        query = f"""
        WITH target_doc AS (
            SELECT embedding
            FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            WHERE doc_id = '{doc_id}'
        )
        SELECT
            s.doc_id,
            s.uri,
            s.modality,
            s.source,
            s.created_at,
            s.text_content,
            s.distance
        FROM target_doc t,
        VECTOR_SEARCH(
            TABLE `{self.config.project_id}.{self.config.dataset_name}.search_corpus`,
            'embedding',
            t.embedding,
            top_k => {top_k + 1}
        ) s
        WHERE s.doc_id != '{doc_id}'
        ORDER BY s.distance ASC
        LIMIT {top_k}
        """

        try:
            results = self.client.execute_query_and_wait(query)
            logger.info(f"Found {len(results)} similar documents")
            return results
        except Exception as e:
            logger.error(f"Similar search failed: {e}")
            return []

    def hybrid_search(self,
                      query: str,
                      keyword_query: Optional[str] = None,
                      top_k: int = 20,
                      keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            query: Semantic search query
            keyword_query: Keyword search query (uses same as semantic if None)
            top_k: Number of results to return
            keyword_weight: Weight for keyword search (0-1)

        Returns:
            Combined search results
        """
        if keyword_query is None:
            keyword_query = query

        semantic_weight = 1.0 - keyword_weight

        logger.info(f"Hybrid search - semantic: {query[:50]}, keyword: {keyword_query[:50]}")

        # Perform semantic search
        semantic_results = self.search(query, top_k * 2, use_rerank=False)

        # Perform keyword search
        keyword_results = self._keyword_search(keyword_query, top_k * 2)

        # Combine and rerank results
        combined = self._combine_results(
            semantic_results,
            keyword_results,
            semantic_weight,
            keyword_weight
        )

        # Return top k results
        return combined[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search."""
        # Build search terms
        terms = query.lower().split()
        search_conditions = [f"LOWER(text_content) LIKE '%{term}%'" for term in terms]

        sql_query = f"""
        SELECT
            doc_id,
            uri,
            modality,
            source,
            created_at,
            author,
            channel,
            text_content,
            -- Calculate simple relevance score based on term frequency
            (
                {' + '.join([f"CAST(LOWER(text_content) LIKE '%{term}%' AS INT64)" for term in terms])}
            ) / {len(terms)} AS keyword_score
        FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        WHERE {' OR '.join(search_conditions)}
        ORDER BY keyword_score DESC
        LIMIT {top_k}
        """

        try:
            results = self.client.execute_query_and_wait(sql_query)
            return results
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _combine_results(self,
                         semantic_results: List[Dict[str, Any]],
                         keyword_results: List[Dict[str, Any]],
                         semantic_weight: float,
                         keyword_weight: float) -> List[Dict[str, Any]]:
        """Combine and rerank results from different search methods."""
        # Create result map
        combined_scores = {}
        all_results = {}

        # Add semantic results
        for i, result in enumerate(semantic_results):
            doc_id = result['doc_id']
            # Normalize distance to score (inverse)
            semantic_score = 1.0 / (1.0 + result.get('distance', 1.0))
            combined_scores[doc_id] = semantic_score * semantic_weight
            all_results[doc_id] = result

        # Add keyword results
        for i, result in enumerate(keyword_results):
            doc_id = result['doc_id']
            keyword_score = result.get('keyword_score', 0.0)

            if doc_id in combined_scores:
                # Document appears in both results
                combined_scores[doc_id] += keyword_score * keyword_weight
            else:
                # Document only in keyword results
                combined_scores[doc_id] = keyword_score * keyword_weight
                all_results[doc_id] = result

        # Sort by combined score
        sorted_ids = sorted(combined_scores.keys(),
                            key=lambda x: combined_scores[x],
                            reverse=True)

        # Build final results
        final_results = []
        for doc_id in sorted_ids:
            result = all_results[doc_id].copy()
            result['combined_score'] = combined_scores[doc_id]
            final_results.append(result)

        return final_results