from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

if not os.getenv("DOCKER_CONTAINER"):
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)


class Settings(BaseSettings):
    app_name: str = "Chrome Extension History Clustering API"
    app_version: str = "0.2.0"
    debug: bool = False
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    cors_origins: List[str] = [
        "chrome-extension://*", 
        "http://localhost:*"
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    log_level: str = "INFO"
    log_json_format: bool = True  # Use JSON logs vs plain text
    
    # Chat logging verbosity controls
    chat_log_full_prompts: bool = False  # Toggle to see full prompts in logs
    chat_log_full_tool_responses: bool = False  # Toggle to see full tool responses
    
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    default_provider: str = "google"
    default_model: str = "gemini-2.0-flash"
    
    clustering_batch_size: int = 20
    clustering_max_tokens: int = 16384
    clustering_temperature: float = 0.2
    clustering_similarity_threshold: float = 0.4
    topic_similarity_threshold: float = 0.82
    current_session_gap_minutes: int = 30
    
    chat_max_tokens: int = 8000
    chat_temperature: float = 0.7
    chat_history_limit: int = 10
    chat_max_tool_iterations: int = 6
    
    search_limit_clusters: int = 6
    search_limit_items_per_cluster: int = 10
    search_overfetch_multiplier: int = 3
    
    embedding_provider: str = "google"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ollama_base_url: str = "http://localhost:11434"
    
    api_timeout: float = 30.0
    ollama_timeout: float = 60.0
    
    database_url: Optional[str] = None
    
    class Config:
        case_sensitive = False


settings = Settings()
