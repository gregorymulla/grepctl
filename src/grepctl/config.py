"""
Configuration management for BigQuery Semantic Grep.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class Config:
    """Configuration for BigQuery Semantic Grep."""

    # BigQuery settings
    project_id: str = "semgrep-472018"
    dataset_name: str = "grepmm"
    location: str = "US"  # BigQuery dataset location
    vertex_location: str = "us-central1"  # Vertex AI location

    # GCS settings
    gcs_bucket: str = "gcm-data-lake"
    gcs_prefix: str = "multimodal-dataset"
    gcs_connection: str = ""  # BigQuery connection name for GCS

    # Model configurations
    text_model: str = "semgrep-472018.grepmm.text_model"
    embedding_model: str = "semgrep-472018.grepmm.text_embedding_model"

    # Chunking parameters
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 1200

    # Search parameters
    default_top_k: int = 20
    search_multiplier: int = 5  # Retrieve top_k * multiplier candidates
    max_search_count: int = 200
    rerank_threshold: int = 50  # Max candidates to rerank

    # Vector index parameters
    index_type: str = "IVF"
    distance_type: str = "COSINE"
    ivf_min_train_size: int = 10000

    # Processing parameters
    batch_size: int = 100
    max_workers: int = 4
    timeout_seconds: int = 300

    # Modality mappings
    modality_extensions: Dict[str, List[str]] = field(default_factory=lambda: {
        'pdf': ['.pdf'],
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'],
        'text': ['.txt', '.log'],
        'markdown': ['.md', '.markdown'],
        'json': ['.json', '.jsonl'],
        'csv': ['.csv', '.tsv'],
        'documents': ['.doc', '.docx', '.odt', '.rtf']
    })

    # Source type mappings
    source_mappings: Dict[str, str] = field(default_factory=lambda: {
        'pdf': 'pdf',
        'images': 'screenshot',
        'audio': 'recording',
        'video': 'video',
        'text': 'file',
        'markdown': 'markdown',
        'json': 'json',
        'csv': 'csv',
        'documents': 'document'
    })

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def validate(self) -> None:
        """Validate configuration."""
        errors = []

        if not self.project_id:
            # Try to get from environment
            self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
            if not self.project_id:
                errors.append("project_id is required (set GOOGLE_CLOUD_PROJECT env var)")

        if not self.text_model:
            # Set default text model
            if self.project_id and self.location:
                self.text_model = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/gemini-1.5-pro"
            else:
                errors.append("text_model is required")

        if not self.embedding_model:
            # Set default embedding model based on pattern
            if self.project_id and self.dataset_name:
                # Use BigQuery model format if dataset is specified
                self.embedding_model = f"{self.project_id}.{self.dataset_name}.text_embedding_model"
            elif self.project_id and self.location:
                # Fallback to Vertex AI format
                self.embedding_model = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/text-embedding-004"
            else:
                errors.append("embedding_model is required")

        if not self.gcs_connection:
            # Try to construct default connection name
            if self.project_id and self.location:
                self.gcs_connection = f"projects/{self.project_id}/locations/{self.location}/connections/bigquery-gcs"

        if self.chunk_overlap >= self.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary."""
        return cls(**data)

    @classmethod
    def from_yaml(cls, path: Path) -> 'Config':
        """Load config from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def to_yaml(self, path: Path) -> None:
        """Save config to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def load_config(path: Optional[Path] = None) -> Config:
    """Load configuration from file or create default."""
    if path and path.exists():
        config = Config.from_yaml(path)
    else:
        config = Config()

        # Try to load from default locations
        default_paths = [
            Path.home() / '.grepctl' / 'config.yaml',
            Path.cwd() / '.grepctl.yaml',
            Path.cwd() / 'config.yaml'
        ]

        for default_path in default_paths:
            if default_path.exists():
                config = Config.from_yaml(default_path)
                break

    # Override with environment variables
    env_mappings = {
        'GREPCTL_PROJECT': 'project_id',
        'GREPCTL_DATASET': 'dataset_name',
        'GREPCTL_BUCKET': 'gcs_bucket',
        'GREPCTL_CONNECTION': 'gcs_connection',
        'GREPCTL_TEXT_MODEL': 'text_model',
        'GREPCTL_EMBEDDING_MODEL': 'embedding_model',
        'GREPCTL_LOCATION': 'location',
    }

    for env_var, config_attr in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            setattr(config, config_attr, value)

    # Validate configuration
    config.validate()

    return config


def create_default_config(path: Path) -> None:
    """Create a default configuration file."""
    config = Config()

    # Set some sensible defaults
    config.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'your-project-id')
    config.location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')

    # Save to file
    config.to_yaml(path)
    print(f"Created default configuration at {path}")
    print("Please edit this file with your specific settings.")