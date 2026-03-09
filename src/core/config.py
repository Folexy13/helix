"""
Configuration settings for Helix using Pydantic Settings.

Loads configuration from environment variables and .env files.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = Field(default="Helix", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False, description="Debug mode")
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    
    # Amazon Bedrock Configuration
    bedrock_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom Bedrock endpoint URL (optional)"
    )
    
    # Nova Model IDs
    nova_lite_model_id: str = Field(
        default="amazon.nova-lite-v2:0",
        description="Nova 2 Lite model ID for reasoning"
    )
    nova_sonic_model_id: str = Field(
        default="amazon.nova-sonic-v2:0",
        description="Nova 2 Sonic model ID for voice"
    )
    nova_embeddings_model_id: str = Field(
        default="amazon.nova-embed-multimodal-v1:0",
        description="Nova Multimodal Embeddings model ID"
    )
    
    # GitHub Configuration
    github_token: Optional[str] = Field(default=None, description="GitHub personal access token")
    github_owner: Optional[str] = Field(default=None, description="GitHub repository owner")
    github_repo: Optional[str] = Field(default=None, description="GitHub repository name")
    
    # GitHub OAuth Configuration
    github_client_id: Optional[str] = Field(default=None, description="GitHub OAuth App Client ID")
    github_client_secret: Optional[str] = Field(default=None, description="GitHub OAuth App Client Secret")
    
    # Application URL (for OAuth callbacks)
    app_url: str = Field(default="http://localhost:8000", description="Application base URL")
    
    # Voice Configuration
    voice_sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    voice_channels: int = Field(default=1, description="Number of audio channels")
    voice_connection_timeout: int = Field(default=480, description="Voice connection timeout in seconds (8 min)")
    
    # Session Configuration
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    max_conversation_history: int = Field(default=100, description="Max messages in conversation history")
    
    # Inference Configuration
    default_temperature: float = Field(default=0.7, description="Default temperature for inference")
    default_top_p: float = Field(default=0.9, description="Default top_p for inference")
    default_max_tokens: int = Field(default=10000, description="Default max tokens for inference")
    
    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    # RAG Configuration
    embedding_dimension: int = Field(default=1024, description="Embedding vector dimension")
    chunk_size: int = Field(default=1000, description="Text chunk size for RAG")
    chunk_overlap: int = Field(default=200, description="Chunk overlap for RAG")
    top_k_results: int = Field(default=5, description="Number of top results for RAG retrieval")
    
    # Redis Configuration
    # Local development: redis://localhost:6379/0
    # Production: Set REDIS_URL to your cloud Redis instance
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL. If not set, uses in-memory storage."
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password (if required)"
    )
    redis_ssl: bool = Field(
        default=False,
        description="Use SSL for Redis connection (recommended for production)"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
