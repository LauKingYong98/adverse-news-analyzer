import logging
import time
from datetime import datetime

from gnews import GNews

from adverse_news.models import ArticleData, CompanyInput
from adverse_news.scraper.base import NewsSource

logger = logging.getLogger(__name__)

MIN_ALIAS_LENGTH = 3


class GNewsSource(NewsSource):
    def __init__(self, max_results: int = 30, delay: float = 1.0):
        self.max_results = max_results
        self.delay = delay

    def search(self, query: str, period_months: int = 12, language: str = "en") -> list[ArticleData]:
        country = "US" if language == "en" else "CN"
        gn = GNews(
            language=language,
            country=country,
            period=f"{period_months}m",
            max_results=self.max_results,
        )

        logger.info(f"GNews search: '{query}' (lang={language}, period={period_months}m)")
        try:
            raw_results = gn.get_news(query)
        except Exception as e:
            logger.warning(f"GNews search failed for '{query}': {e}")
            return []

        articles = []
        for item in raw_results or []:
            pub_date = None
            if item.get("published date"):
                try:
                    pub_date = datetime.strptime(
                        item["published date"], "%a, %d %b %Y %H:%M:%S %Z"
                    )
                except (ValueError, TypeError):
                    pass

            articles.append(
                ArticleData(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    source=item.get("publisher", {}).get("title", ""),
                    published_date=pub_date,
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
        if languages is None:
            languages = ["en"]

        all_articles: list[ArticleData] = []
        seen_urls: set[str] = set()

        for lang in languages:
            for term in company.all_search_terms:
                if len(term) < MIN_ALIAS_LENGTH:
                    logger.info(f"Skipping alias '{term}' (too short)")
                    continue
                results = self.search(term, company.search_period_months, lang)
                for article in results:
                    if article.url and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        all_articles.append(article)

        logger.info(f"GNews found {len(all_articles)} unique articles for '{company.name}'")
        return all_articles
