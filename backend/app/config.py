from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str | None = None
    # Model adı koda gömülmez: hesabında açık olan küçük bir modeli .env'den seç.
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
