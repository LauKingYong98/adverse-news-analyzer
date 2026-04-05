import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from adverse_news.models import ArticleData

logger = logging.getLogger(__name__)


def parse_article(article: ArticleData, text_limit: int = 500) -> ArticleData:
    """Download and parse the full text of an article using newspaper4k."""
    try:
        from newspaper import Article

        a = Article(article.url)
        a.download()
        a.parse()

        article.full_text = (a.text or "")[:text_limit]
        if a.title and not article.title:
            article.title = a.title
        if a.publish_date and not article.published_date:
            article.published_date = a.publish_date

    except Exception as e:
        logger.warning(f"Failed to parse {article.url}: {e}")

    return article


def parse_articles(
    articles: list[ArticleData],
    text_limit: int = 500,
    max_workers: int = 8,
) -> list[ArticleData]:
    """Parse full text for articles in parallel. Skips failures gracefully."""
    total = len(articles)
    logger.info(f"Parsing {total} articles with {max_workers} workers...")

    parsed = [None] * total
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(parse_article, article, text_limit): i
            for i, article in enumerate(articles)
        }
        done = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            parsed[idx] = future.result()
            done += 1
            if done % 10 == 0 or done == total:
                logger.info(f"Parsed {done}/{total} articles")

    successful = sum(1 for a in parsed if a and a.full_text)
    logger.info(f"Successfully parsed {successful}/{total} articles")
    return [a for a in parsed if a is not None]
