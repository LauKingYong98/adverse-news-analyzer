from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class CompanyInput(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    search_period_months: int = 12

    @property
    def all_search_terms(self) -> list[str]:
        terms = [self.name]
        for alias in self.aliases:
            if alias not in terms:
                terms.append(alias)
        return terms


class ArticleData(BaseModel):
    url: str
    title: str
    source: str = ""
    published_date: datetime | None = None
    full_text: str = ""
    language: str = "en"

    @field_validator("published_date", mode="before")
    @classmethod
    def normalize_datetime(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        return v


class SentimentResult(BaseModel):
    article: ArticleData
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    risk_factors: list[str] = Field(default_factory=list)
    summary: str = ""


class AnalysisReport(BaseModel):
    company: CompanyInput
    total_articles_found: int = 0
    results: list[SentimentResult] = Field(default_factory=list)
    run_timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def all_results(self) -> list[SentimentResult]:
        return self.results

    @property
    def negative_results(self) -> list[SentimentResult]:
        return [r for r in self.results if r.sentiment == Sentiment.NEGATIVE]

    @property
    def positive_results(self) -> list[SentimentResult]:
        return [r for r in self.results if r.sentiment == Sentiment.POSITIVE]

    @property
    def neutral_results(self) -> list[SentimentResult]:
        return [r for r in self.results if r.sentiment == Sentiment.NEUTRAL]

    @property
    def top_risk_factors(self) -> list[str]:
        factors: dict[str, int] = {}
        for r in self.negative_results:
            for f in r.risk_factors:
                factors[f] = factors.get(f, 0) + 1
        return sorted(factors, key=factors.get, reverse=True)[:10]
