from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    nomba_client_id: str
    nomba_private_key: str
    nomba_account_id: str
    nomba_subaccount_id: str
    nomba_base_url: str = "https://api.nomba.com/v1"
    secret_key: str
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
