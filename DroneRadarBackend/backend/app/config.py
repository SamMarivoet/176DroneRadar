from pydantic import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = 'mongodb://localhost:27017'
    MONGO_DB: str = 'planesdb'
    PORT: int = 8000

    # User credentials
    ADMIN_PASSWORD: str = "pass"
    AIRPLANEFEED_PASSWORD: str = "pass"
    OPERATOR_PASSWORD: str = "pass"
    AUTHORITY_PASSWORD: str = "pass"
    ANALYST_PASSWORD: str = "pass"
    

    class Config:
        env_file = '.env'


settings = Settings()