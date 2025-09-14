"""
FastAPI server for grepctl REST API.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ..config import load_config
from ..bigquery.connection import BigQueryClient
from ..search.vector_search import SemanticSearch

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    modalities: Optional[List[str]] = Field(None, description="Filter by modality")
    sources: Optional[List[str]] = Field(None, description="Filter by source type")
    use_rerank: bool = Field(False, description="Use LLM reranking")
    start_date: Optional[str] = Field(None, description="Filter documents after this date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter documents before this date (YYYY-MM-DD)")

class SearchResult(BaseModel):
    doc_id: str
    uri: str
    source: str
    modality: str
    text_content: str
    score: float
    created_at: Optional[str]
    metadata: Optional[Dict[str, Any]]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time: float
    query: str

class SystemStatus(BaseModel):
    dataset_exists: bool
    document_count: int
    index_status: Dict[str, Any]
    modalities: List[str]
    last_updated: Optional[str]

class ThemeConfig(BaseModel):
    branding: Dict[str, Any]
    colors: Dict[str, str]
    features: Dict[str, bool]

# Global variables for caching
_config = None
_client = None
_searcher = None
_theme_config = None

def load_theme_config(theme_path: Optional[str] = None) -> Dict[str, Any]:
    """Load theme configuration from file or use defaults."""
    default_theme = {
        "branding": {
            "companyName": "grepctl",
            "logo": "/static/grepctl_logo.png",
            "favicon": "/favicon.ico",
            "tagline": "Multimodal Semantic Search"
        },
        "colors": {
            "primary": "#1976d2",
            "secondary": "#dc004e",
            "accent": "#9c27b0",
            "background": "#ffffff",
            "surface": "#f5f5f5",
            "text": "#333333",
            "textSecondary": "#666666"
        },
        "darkMode": {
            "enabled": True,
            "colors": {
                "background": "#121212",
                "surface": "#1e1e1e",
                "text": "#ffffff",
                "textSecondary": "#aaaaaa"
            }
        },
        "features": {
            "darkMode": True,
            "exportEnabled": True,
            "advancedFilters": True
        }
    }

    if theme_path and Path(theme_path).exists():
        try:
            import yaml
            with open(theme_path, 'r') as f:
                if theme_path.endswith('.json'):
                    custom_theme = json.load(f)
                else:
                    custom_theme = yaml.safe_load(f)
            # Merge with defaults
            for key in custom_theme:
                if isinstance(custom_theme[key], dict) and key in default_theme:
                    default_theme[key].update(custom_theme[key])
                else:
                    default_theme[key] = custom_theme[key]
        except Exception as e:
            logger.error(f"Failed to load theme config: {e}")

    return default_theme

def create_app(theme_config_path: Optional[str] = None) -> FastAPI:
    """Create and configure FastAPI application."""
    global _config, _client, _searcher, _theme_config

    app = FastAPI(
        title="grepctl API",
        description="REST API for multimodal semantic search in BigQuery",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load configuration
    _config = load_config()
    _client = BigQueryClient(_config)
    _searcher = SemanticSearch(_client, _config)
    _theme_config = load_theme_config(theme_config_path)

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.post("/api/search", response_model=SearchResponse)
    async def search(request: SearchRequest):
        """Perform semantic search across indexed documents."""
        try:
            import time
            start_time = time.time()

            # Perform search
            results = _searcher.search(
                query=request.query,
                top_k=request.top_k,
                source_filter=request.sources,
                modality_filter=request.modalities,
                use_rerank=request.use_rerank,
                start_date=request.start_date,
                end_date=request.end_date
            )

            query_time = time.time() - start_time

            # Convert results to response format
            search_results = []
            for r in results:
                # Convert datetime to string if present
                created_at = r.get('created_at')
                if created_at and hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                elif created_at:
                    created_at = str(created_at)

                search_results.append(SearchResult(
                    doc_id=r.get('doc_id', ''),
                    uri=r.get('uri', ''),
                    source=r.get('source', 'unknown'),
                    modality=r.get('modality', 'unknown'),
                    text_content=r.get('text_content', ''),
                    score=float(r.get('distance', 0.0)),
                    created_at=created_at,
                    metadata=r.get('metadata', {})
                ))

            return SearchResponse(
                results=search_results,
                total=len(search_results),
                query_time=query_time,
                query=request.query
            )

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/status", response_model=SystemStatus)
    async def get_status():
        """Get system status and statistics."""
        try:
            # Check dataset
            dataset_exists = _client.check_dataset_exists(_config.dataset_name)

            # Get document count
            doc_count = _client.get_document_count() if dataset_exists else 0

            # Get index status
            index_status = _client.get_index_status() if dataset_exists else {"exists": False}

            # Get available modalities
            modalities = ["text", "markdown", "pdf", "images", "json", "csv", "audio", "video"]

            return SystemStatus(
                dataset_exists=dataset_exists,
                document_count=doc_count,
                index_status=index_status,
                modalities=modalities,
                last_updated=index_status.get('last_updated')
            )

        except Exception as e:
            logger.error(f"Status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/modalities")
    async def get_modalities():
        """Get available search modalities."""
        return {
            "modalities": [
                {"id": "text", "label": "Text Files", "icon": "📄"},
                {"id": "markdown", "label": "Markdown", "icon": "📝"},
                {"id": "pdf", "label": "PDF Documents", "icon": "📑"},
                {"id": "images", "label": "Images", "icon": "🖼️"},
                {"id": "json", "label": "JSON", "icon": "📊"},
                {"id": "csv", "label": "CSV", "icon": "📈"},
                {"id": "audio", "label": "Audio", "icon": "🎵"},
                {"id": "video", "label": "Video", "icon": "🎬"}
            ]
        }

    @app.get("/api/config")
    async def get_config():
        """Get UI configuration and theme."""
        return _theme_config

    @app.post("/api/config")
    async def update_config(config: ThemeConfig):
        """Update UI configuration (admin only)."""
        global _theme_config
        try:
            _theme_config.update(config.dict())
            return {"status": "success", "message": "Configuration updated"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Serve static files if web directory exists
    web_dir = Path(__file__).parent.parent.parent.parent / "web" / "dist"
    if web_dir.exists():
        # Mount assets directory for static files
        if (web_dir / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(web_dir / "assets")), name="assets")

        # Serve logo directly
        @app.get("/grepctl_logo.png")
        async def serve_logo():
            """Serve the logo file."""
            logo_file = web_dir / "assets" / "grepctl_logo.png"
            if logo_file.exists():
                return FileResponse(str(logo_file), media_type="image/png")
            # Fallback to public directory
            logo_file = web_dir.parent / "public" / "grepctl_logo.png"
            if logo_file.exists():
                return FileResponse(str(logo_file), media_type="image/png")
            raise HTTPException(status_code=404, detail="Logo not found")

        @app.get("/")
        async def serve_spa():
            """Serve the React SPA."""
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"message": "Web UI not built. Run 'npm run build' in the web directory."}

        # Catch-all route for SPA routing
        @app.get("/{full_path:path}")
        async def serve_spa_routes(full_path: str):
            """Handle SPA routes."""
            # Check if it's an API route
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API endpoint not found")

            # Serve index.html for all other routes (SPA routing)
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"message": "Web UI not built"}

    return app

# Create default app instance
app = create_app()