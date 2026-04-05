import logging
import time
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from adverse_news.models import ArticleData, CompanyInput
from adverse_news.scraper.base import NewsSource

logger = logging.getLogger(__name__)

MIN_ALIAS_LENGTH = 3


class DDGSource(NewsSource):
    def __init__(self, max_results: int = 30, delay: float = 0.5):
        self.max_results = max_results
        self.delay = delay

    def search(self, query: str, period_months: int = 12, language: str = "en") -> list[ArticleData]:
        timelimit = "y" if period_months >= 12 else "m"
        region = "wt-wt" if language == "en" else "cn-zh"

        logger.info(f"DDG news search: '{query}' (lang={language}, timelimit={timelimit})")
        try:
            with DDGS() as ddgs:
                raw = list(
                    ddgs.news(query, region=region, timelimit=timelimit, max_results=self.max_results)
                )
        except Exception as e:
            logger.warning(f"DDG search failed for '{query}': {e}")
            return []

        articles = []
        for item in raw:
            pub_date = None
            if item.get("date"):
                try:
                    pub_date = datetime.fromisoformat(item["date"])
                except (ValueError, TypeError):
                    pass

            articles.append(
                ArticleData(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    published_date=pub_date,
                    full_text=item.get("body", ""),
                    language=language,
                )
            )

        time.sleep(self.delay)
        return articles

    def search_company(
        self,
        company: CompanyInput,
        languages: list[str] | None = None,
    ) -> list[ArticleData]:
        """Search news for a company across all aliases and languages."""
        if languages is None:
            languages = ["en"]

        all_articles: list[ArticleData] = []
        seen_urls: set[str] = set()

        for lang in languages:
            for term in company.all_search_terms:
                if len(term) < MIN_ALIAS_LENGTH:
                    logger.info(f"Skipping alias '{term}' (too short)")
                    continue
                query = f'"{term}"' if " " in term or len(term) < 5 else term
                results = self.search(query, company.search_period_months, lang)
                for article in results:
                    if article.url and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        all_articles.append(article)

        logger.info(f"Found {len(all_articles)} unique articles for '{company.name}'")
        return all_articles
