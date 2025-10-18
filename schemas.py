from pydantic import BaseModel, SecretStr
from datetime import datetime
from typing import List, Optional
from enum import Enum

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ContentType(str, Enum):
    PDF = "application/pdf"

class AgentResponse(BaseModel):
    id: str
    success:bool
    message: str = "Processed successfully"
   
    
    class Config:
        from_attributes = True


### Secrets

class APIKeys(BaseModel):
    theagentic: SecretStr
    openai: SecretStr
    logfire: SecretStr

class Database(BaseModel):
    postgres_connection_string: SecretStr

class SwaggerDocs(BaseModel):
    username: str
    password: SecretStr

class Services(BaseModel):
    agentic_url: str

class AppConfig(BaseModel):
    api_v1_str: str
    project_name: str
    upload_dir: str
    max_file_size: int
    model: str
    openai_model: str
    logfire_env: str
    allowed_origins: List[str]

class S3(BaseModel):
    origin: str
    key_id: SecretStr
    key: SecretStr

class Settings(BaseModel):
    api_keys: APIKeys
    database: Database
    swagger_docs: SwaggerDocs
    services: Services
    app_config: AppConfig
    s3: S3