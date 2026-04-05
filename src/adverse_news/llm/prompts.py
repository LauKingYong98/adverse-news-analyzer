"""Shared prompt templates for all LLM providers."""

ANALYSIS_PROMPT = """\
Classify each article's impact on {company_name}'s fair valuation.

For each article return:
- sentiment: POSITIVE, NEGATIVE, or NEUTRAL
- confidence: 0.0-1.0
- risk_factors: list of risks if NEGATIVE (e.g. "lawsuit", "revenue decline", "regulatory action"). Empty list otherwise.
- summary: 1 sentence on valuation impact

Articles:
{articles_json}

Return ONLY a JSON array with "index", "sentiment", "confidence", "risk_factors", "summary" per article."""
