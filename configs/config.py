from pydantic import SecretStr
from pydantic_settings import BaseSettings
from typing import Optional
import json
import os
from pathlib import Path

def load_secrets_from_json(secrets_file: str = "secrets.json") -> dict:
    """Load secrets from a JSON file."""
    # Try multiple possible locations for the secrets file
    possible_paths = [
        Path(secrets_file),  # Current directory
        Path(__file__).parent.parent / secrets_file,  # Project root
        Path(__file__).parent / secrets_file,  # Config directory
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load secrets from {path}: {e}")
                continue
    
    print(f"Warning: secrets.json not found in any of the expected locations: {[str(p) for p in possible_paths]}")
    print("Falling back to environment variables and default values.")
    return {}

# Load secrets once at module level
_secrets = load_secrets_from_json()

class DatabaseSettings(BaseSettings):
    postgres_connection_string: SecretStr = SecretStr(
        _secrets.get("database", {}).get("postgres_connection_string") or 
        os.getenv("POSTGRES_CONNECTION_STRING") or
        "postgres://c5aad4745edc63bc01070e97e14bbb69badcd888da110a96b7213046edf6b217:sk_peCkTuV4RZCiBbx-HULlS@db.prisma.io:5432/postgres?sslmode=require"
    )

class APIKeys(BaseSettings):
    
    openai_api_key: SecretStr = SecretStr(
        _secrets.get("api_keys", {}).get("openai_api_key") or
        os.getenv("OPENAI_API_KEY") or
        "OPEN_AI_KEY"
    )
    serp_api_key: SecretStr = SecretStr(
        _secrets.get("api_keys", {}).get("serp_api_key") or
        os.getenv("SERP_API_KEY") or
        "SERP_API_KEY"
    )
    firecrawl_api_key: SecretStr = SecretStr(
        _secrets.get("api_keys", {}).get("firecrawl_api_key") or
        os.getenv("FIRECRAWL_API_KEY") or
        "FIRECRAWL_API_KEY"
    )

class Neo4jSettings(BaseSettings):
    uri: str = (_secrets.get("neo4j", {}).get("uri") or 
                os.getenv("NEO4J_URI") or 
                "bolt://localhost:7687")
    username: str = (_secrets.get("neo4j", {}).get("username") or 
                     os.getenv("NEO4J_USERNAME") or 
                     "neo4j")
    password: str = (_secrets.get("neo4j", {}).get("password") or 
                     os.getenv("NEO4J_PASSWORD") or 
                     "password")
    database: str = (_secrets.get("neo4j", {}).get("database") or 
                     os.getenv("NEO4J_DATABASE") or 
                     "neo4j")

class AppConfig(BaseSettings):
    project_name: str = "Claim Radar Application"
    upload_dir: str = "data"
    api_v1_str: str = "/api/v1"
    allowed_origins: list = ["*"]

class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    app_config: AppConfig = AppConfig()
    api_keys: APIKeys = APIKeys()
    # Add other settings as needed
    app_name: str = "Claim Radar Application"
    debug: bool = False
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB in bytes
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        # Allow unspecified env vars to exist without raising validation errors
        "extra": "ignore"
    }

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
