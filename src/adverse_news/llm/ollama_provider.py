import json
import logging

import ollama

from adverse_news.config import settings
from adverse_news.llm.prompts import ANALYSIS_PROMPT
from adverse_news.models import ArticleData, Sentiment, SentimentResult

logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def _chat(self, prompt: str) -> str:
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        return response["message"]["content"]

    def _parse_json(self, raw: str) -> list:
        """Extract JSON array from response, handling markdown fences."""
        raw = raw.strip()
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    raw = part
                    break
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start : end + 1]
        return json.loads(raw)

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

        logger.info(f"Sending {len(articles)} articles to Ollama ({self.model})")
        try:
            raw = self._chat(prompt)
            parsed = self._parse_json(raw)
        except Exception as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            return self._fallback_results(articles)

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
