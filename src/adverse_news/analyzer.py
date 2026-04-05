import logging

from adverse_news.config import settings
from adverse_news.llm.base import LLMProvider
from adverse_news.llm.claude_provider import ClaudeProvider
from adverse_news.llm.ollama_provider import OllamaProvider
from adverse_news.models import AnalysisReport, CompanyInput, SentimentResult
from adverse_news.scraper.article_parser import parse_articles
from adverse_news.scraper.gnews_source import GNewsSource

logger = logging.getLogger(__name__)


def create_llm_provider(
    model: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    """Create LLM provider. Models starting with 'claude-' use API, others use Ollama."""
    model = model or settings.llm_model
    if model.startswith("claude-"):
        return ClaudeProvider(api_key=api_key, model=model)
    else:
        return OllamaProvider(model=model)


def analyze_company(
    company: CompanyInput,
    api_key: str | None = None,
    model: str | None = None,
    max_articles: int | None = None,
    progress_callback=None,
) -> AnalysisReport:
    """Run adverse news analysis pipeline: scrape -> parse -> classify -> report."""

    max_articles = max_articles or settings.max_articles_total

    def _progress(step: str, detail: str = ""):
        logger.info(f"{step}: {detail}")
        if progress_callback:
            progress_callback(step, detail)

    llm = create_llm_provider(model=model, api_key=api_key)
    gnews = GNewsSource(max_results=settings.max_articles_per_query)

    # Step 1: Search news via GNews
    _progress("Searching news", f"'{company.name}' via Google News ({len(settings.languages)} language(s))...")
    articles = gnews.search_company(company, languages=settings.languages)

    if not articles:
        _progress("Complete", "No articles found.")
        return AnalysisReport(company=company)

    # Sort by date (newest first) and cap at max_articles
    articles.sort(key=lambda a: a.published_date or __import__('datetime').datetime.min, reverse=True)
    if len(articles) > max_articles:
        logger.info(f"Capping articles from {len(articles)} to {max_articles} (newest first)")
        articles = articles[:max_articles]

    _progress("Searching news", f"Found {len(articles)} articles (capped at {max_articles})")

    # Step 2: Parse full text (parallel)
    _progress("Parsing articles", f"Extracting text from {len(articles)} articles...")
    articles = parse_articles(
        articles,
        text_limit=settings.article_text_limit,
        max_workers=settings.max_parse_workers,
    )
    articles = [a for a in articles if a.full_text or a.title]
    _progress("Parsing articles", f"{len(articles)} articles ready")

    # Step 3: LLM sentiment classification (in batches)
    _progress("Classifying sentiment", f"Analyzing {len(articles)} articles...")
    all_results: list[SentimentResult] = []
    total_batches = (len(articles) + settings.batch_size - 1) // settings.batch_size
    for i in range(0, len(articles), settings.batch_size):
        batch = articles[i : i + settings.batch_size]
        batch_num = i // settings.batch_size + 1
        _progress("Classifying sentiment", f"Batch {batch_num}/{total_batches}")
        results = llm.analyze_articles(company.name, batch)
        all_results.extend(results)

    # Compile report
    report = AnalysisReport(
        company=company,
        total_articles_found=len(articles),
        results=all_results,
    )

    pos = len(report.positive_results)
    neg = len(report.negative_results)
    neu = len(report.neutral_results)
    _progress("Complete", f"{pos} positive, {neg} negative, {neu} neutral")
    return report
