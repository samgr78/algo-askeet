from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str
    API_SECRET_KEY: str

    POLL_REQUEST_LIMIT: int = 20

    @property
    def DATABASE_URL(self) -> str:
        # Format pour SQLAlchemy + aiomysql
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra = 'ignore'
    )

settings = Settings()