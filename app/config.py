from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
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
    
    @field_validator('dev_user_id', mode='before')
    @classmethod
    def parse_dev_user_id(cls, v):
        """Convert empty string to None for dev_user_id"""
        if v == '' or v is None:
            return None
        if isinstance(v, str):
            # Try to parse as int
            try:
                return int(v)
            except ValueError:
                return None
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env that aren't in the model


settings = Settings()

