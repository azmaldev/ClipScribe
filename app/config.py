from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = Field(default="")
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
