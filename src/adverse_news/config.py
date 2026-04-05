from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    search_period_months: int = 12
    max_articles_per_query: int = 30
    languages: list[str] = ["en", "zh"]
    article_text_limit: int = 500
    batch_size: int = 10
    max_parse_workers: int = 8

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
