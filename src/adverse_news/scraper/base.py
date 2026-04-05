from abc import ABC, abstractmethod

from adverse_news.models import ArticleData


class NewsSource(ABC):
    @abstractmethod
    def search(self, query: str, period_months: int = 12, language: str = "en") -> list[ArticleData]:
        ...
