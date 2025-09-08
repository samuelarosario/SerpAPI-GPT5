from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    webapp_jwt_secret: str = Field("change_me_dev_secret_change_me", alias="WEBAPP_JWT_SECRET")
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
