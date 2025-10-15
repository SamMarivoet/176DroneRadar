from pydantic import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = 'mongodb://localhost:27017'
    MONGO_DB: str = 'planesdb'
    PORT: int = 8000


class Config:
    env_file = '.env'


settings = Settings()