from typing import Protocol

from adverse_news.models import ArticleData, SentimentResult


class LLMProvider(Protocol):
    def analyze_articles(
        self,
        company_name: str,
        articles: list[ArticleData],
    ) -> list[SentimentResult]:
        """Classify sentiment and extract risk factors for a batch of articles."""
        ...
