from pydantic import SecretStr
from pydantic_settings import BaseSettings
from typing import Optional

class DatabaseSettings(BaseSettings):
    postgres_connection_string: SecretStr = SecretStr(
        "postgres://c5aad4745edc63bc01070e97e14bbb69badcd888da110a96b7213046edf6b217:sk_peCkTuV4RZCiBbx-HULlS@db.prisma.io:5432/postgres?sslmode=require"
    )

class Neo4jSettings(BaseSettings):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

class AppConfig(BaseSettings):
    project_name: str = "Claim Radar Application"
    upload_dir: str = "data"
    api_v1_str: str = "/api/v1"
    allowed_origins: list = ["*"]

class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    app_config: AppConfig = AppConfig()
    
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
