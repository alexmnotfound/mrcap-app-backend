from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Database
    postgres_host: str = Field(..., env="POSTGRES_HOST")
    postgres_port: int = Field(..., env="POSTGRES_PORT")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    
    # Server
    port: int = Field(default=8000, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    
    # Firebase (optional for now)
    firebase_credentials_path: Optional[str] = Field(default=None, env="FIREBASE_CREDENTIALS_PATH")
    
    # Development mode - bypasses auth when True (⚠️ DO NOT USE IN PRODUCTION)
    dev_mode: bool = Field(default=False, env="DEV_MODE")
    dev_user_id: Optional[int] = Field(default=None, env="DEV_USER_ID")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env that aren't in the model


settings = Settings()

