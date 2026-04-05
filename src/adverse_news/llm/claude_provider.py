import json
import logging

import anthropic

from adverse_news.config import settings
from adverse_news.llm.prompts import ANALYSIS_PROMPT
from adverse_news.models import ArticleData, Sentiment, SentimentResult

logger = logging.getLogger(__name__)


class ClaudeProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.llm_model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_articles(
        self,
        company_name: str,
        articles: list[ArticleData],
    ) -> list[SentimentResult]:
        if not articles:
            return []

        articles_data = []
        for i, a in enumerate(articles):
            text = a.full_text or a.title
            articles_data.append({
                "index": i,
                "title": a.title,
                "source": a.source,
                "date": a.published_date.isoformat() if a.published_date else "unknown",
                "text": text[:settings.article_text_limit],
            })

        prompt = ANALYSIS_PROMPT.format(
            company_name=company_name,
            articles_json=json.dumps(articles_data, ensure_ascii=False, indent=2),
        )

        logger.info(f"Sending {len(articles)} articles to Claude ({self.model})")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            parsed = json.loads(raw)
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return self._fallback_results(articles)
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_results(articles)

        return self._parse_results(parsed, articles)

    def _parse_results(self, parsed: list, articles: list[ArticleData]) -> list[SentimentResult]:
        results = []
        for item in parsed:
            idx = item.get("index", 0)
            if idx >= len(articles):
                continue
            sentiment_str = item.get("sentiment", "NEUTRAL").upper()
            if sentiment_str not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                sentiment_str = "NEUTRAL"
            results.append(
                SentimentResult(
                    article=articles[idx],
                    sentiment=Sentiment(sentiment_str),
                    confidence=float(item.get("confidence", 0.5)),
                    risk_factors=item.get("risk_factors", []),
                    summary=item.get("summary", ""),
                )
            )
        return results

    def _fallback_results(self, articles: list[ArticleData]) -> list[SentimentResult]:
        return [
            SentimentResult(
                article=a,
                sentiment=Sentiment.NEUTRAL,
                confidence=0.0,
                summary="Analysis failed — manual review required",
            )
            for a in articles
        ]
