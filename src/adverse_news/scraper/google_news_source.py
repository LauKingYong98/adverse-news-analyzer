import logging
import random
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import feedparser
import requests
from googlenewsdecoder import new_decoderv1 as decode_google_url

from adverse_news.models import ArticleData, CompanyInput
from adverse_news.scraper.base import NewsSource

logger = logging.getLogger(__name__)

MIN_ALIAS_LENGTH = 3
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0  # seconds, doubles each retry

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_LANG_COUNTRY = {
    "en": "US",
    "zh": "CN",
}


class GoogleNewsSource(NewsSource):
    def __init__(self, max_results: int = 30):
        self.max_results = max_results
        self._session = requests.Session()
        ua = random.choice(_USER_AGENTS)
        self._session.headers.update({
            "User-Agent": ua,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _build_url(self, query: str, language: str, period_months: int) -> str:
        country = _LANG_COUNTRY.get(language, "US")
        today = datetime.now()
        after_date = (today - timedelta(days=period_months * 30)).strftime("%Y-%m-%d")
        before_date = today.strftime("%Y-%m-%d")

        full_query = f"{query} after:{after_date} before:{before_date}"
        params = urlencode({
            "q": full_query,
            "hl": language,
            "gl": country,
            "ceid": f"{country}:{language}",
        })
        return f"{GOOGLE_NEWS_RSS_URL}?{params}"

    @staticmethod
    def _resolve_urls(google_urls: list[str]) -> list[str]:
        resolved = []
        for url in google_urls:
            if not url:
                resolved.append(url)
                continue
            try:
                result = decode_google_url(url)
                if result.get("status"):
                    resolved.append(result["decoded_url"])
                else:
                    logger.debug(f"URL decode failed: {result.get('message', 'unknown')}")
                    resolved.append(url)
            except Exception as e:
                logger.debug(f"URL decode error for {url}: {e}")
                resolved.append(url)
        return resolved

    def search(self, query: str, period_months: int = 12, language: str = "en") -> list[ArticleData]:
        url = self._build_url(query, language, period_months)

        entries = []
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(
                f"Google News RSS: '{query}' (lang={language}, period={period_months}m, "
                f"attempt {attempt}/{MAX_RETRIES})"
            )
            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 429:
                    logger.warning("Google News returned 429 (rate limited)")
                elif resp.status_code != 200:
                    logger.warning(f"Google News returned HTTP {resp.status_code}")

                feed = feedparser.parse(resp.text)
                entries = feed.entries[: self.max_results]

                if entries:
                    break

                delay = BASE_RETRY_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    f"Google News returned 0 results for '{query}', retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            except Exception as e:
                delay = BASE_RETRY_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(f"Google News error for '{query}': {e}, retrying in {delay:.1f}s...")
                time.sleep(delay)

        # Batch-resolve all Google News redirect URLs
        raw_urls = [entry.get("link", "") for entry in entries]
        resolved_urls = self._resolve_urls(raw_urls)

        articles = []
        for entry, resolved_url in zip(entries, resolved_urls):
            # Parse published date (RFC 2822)
            pub_date = None
            published_str = entry.get("published")
            if published_str:
                try:
                    pub_date = parsedate_to_datetime(published_str).replace(tzinfo=None)
                except (ValueError, TypeError):
                    pass

            # Publisher from <source> element
            source_info = entry.get("source", {})
            publisher = getattr(source_info, "title", "") if source_info else ""

            articles.append(
                ArticleData(
                    url=resolved_url,
                    title=entry.get("title", ""),
                    source=publisher,
                    published_date=pub_date,
                    language=language,
                )
            )

        # Random delay between queries to avoid rate-limiting
        time.sleep(random.uniform(2, 5))
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

        logger.info(f"Google News found {len(all_articles)} unique articles for '{company.name}'")
        return all_articles
