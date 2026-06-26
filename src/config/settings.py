from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Optional

class Settings(BaseSettings):
    MODEL_ID: str
    GOOGLE_API_KEY: str
    APP_NAME: str
    USER_ID: str
    SESSION_ID: str
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()


if __name__ == "__main__":
    print(settings.APP_NAME)
    print(settings.MODEL_ID)
    print(settings.GOOGLE_API_KEY)
    print(settings.USER_ID)
    print(settings.SESSION_ID)