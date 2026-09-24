from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str | None = None

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)
    #burada deterministik sistem devreye giriyor eğer llm yoksa fallback yapacağız demek oluyor 

settings = Settings()