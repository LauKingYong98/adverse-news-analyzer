# Adverse News Analyzer

Automated adverse news screening tool using LLM for different companies.

### General
Given a company name (and optional aliases), the tool searches for recent news articles, classifies each article's sentiment impact on the company's fair valuation using LLM, extracts risk factors, and generates a professional summary in the front UI or Excel report (optional).

- **This tool is not a substitute for professional judgment** — it automates the initial screening step. All findings should be reviewed and verified by a qualified auditor before inclusion in audit workpapers.
- **No persistent storage** — results are not saved between sessions. Each analysis runs from scratch.
- **Single-threaded LLM calls** — articles are classified in sequential batches, not parallel.

## Features

- **Dual news sources** — Google News RSS (via GNews) + DuckDuckGo search, deduplicated by URL
- **AI sentiment classification** — each article classified as Positive / Negative / Neutral from a fair valuation perspective
- **Risk factor extraction** — specific risks identified for negative articles (e.g. "lawsuit", "regulatory action", "revenue decline")
- **Bilingual support** — English and Chinese news search and analysis
- **Cloud or local AI** — Claude API (Anthropic) for accuracy, or Ollama for free local inference
- **Multiple model choices** — switch between Claude Sonnet/Haiku/Opus or any Ollama model
- **Excel reports** — styled 3-sheet workbook with color-coded sentiment, hyperlinks, and frozen headers
- **Batch processing** — analyze multiple companies from an Excel file
- **Streamlit UI** — browser-based interface with progress tracking and Excel download
- **CLI** — scriptable command-line interface for automation

## Tech Stack

| Layer | Package | Role | API Key Required? |
|-------|---------|------|:-:|
| News Discovery | [`gnews`](https://github.com/ranahaani/GNews) | Google News RSS feed wrapper. Returns article titles, URLs, dates, publishers | No |
| News Discovery | [`ddgs`](https://github.com/deedy5/duckduckgo_search) | DuckDuckGo news search. Returns titles, URLs, short body snippets | No |
| Article Extraction | [`newspaper4k`](https://github.com/AndyTheFactory/newspaper4k) | Downloads article URLs and extracts clean text from HTML pages | No |
| Chinese Tokenization | [`jieba`](https://github.com/fxsjy/jieba) | Chinese text segmentation for newspaper4k article parsing | No |
| LLM (Cloud) | [`anthropic`](https://docs.anthropic.com/) | Claude API for sentiment classification + risk factor extraction | Yes |
| LLM (Local) | [`ollama`](https://ollama.com/) | Run open-source models locally (llama3, qwen, gemma, etc.) | No |
| Data Modeling | [`pydantic`](https://docs.pydantic.dev/) | Type-safe data structures and validation throughout the pipeline | No |
| Configuration | [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Loads settings from `.env` file | No |
| Excel Output | [`openpyxl`](https://openpyxl.readthedocs.io/) | Generates styled multi-sheet Excel reports | No |
| Web UI | [`streamlit`](https://streamlit.io/) | Browser-based interface with upload, progress bars, and download | No |

## Architecture / Data Flow

```
User Input
(company name, aliases, search period)
        |
        v
+-------------------------------+
|  Step 1: News Discovery       |
|                               |
|  GNews ----+                  |
|            +--> Deduplicate   |
|  DDG ------+    by URL        |
|                               |
|  Searches each alias in each  |
|  language (en, zh)            |
+-------------------------------+
        |
        v
+-------------------------------+
|  Step 2: Article Parsing      |
|  (newspaper4k, 8x parallel)  |
|                               |
|  For each URL:                |
|  HTTP GET -> HTML -> extract  |
|  clean text, title, date      |
|  Truncate to 500 chars        |
|                               |
|  Falls back to DDG snippet    |
|  if parsing fails (403, etc.) |
+-------------------------------+
        |
        v
+-------------------------------+
|  Step 3: LLM Classification   |
|  (Claude API or Ollama)       |
|                               |
|  Batch 10 articles per call   |
|  For each article returns:    |
|  - Sentiment (POS/NEG/NEU)    |
|  - Confidence (0.0 - 1.0)     |
|  - Risk factors (if negative) |
|  - 1-sentence summary         |
+-------------------------------+
        |
        v
+-------------------------------+
|  Output: Excel Report         |
|                               |
|  Sheet 1: Summary             |
|    Company info, counts,      |
|    top risk factors            |
|                               |
|  Sheet 2: All Articles        |
|    Date, Source, Title, URL,  |
|    Sentiment, Summary, Risks  |
|                               |
|  Sheet 3: Negative Events     |
|    Filtered to negatives only |
|    sorted chronologically     |
+-------------------------------+
```

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) [Ollama](https://ollama.com/) installed for local AI models

### Installation

```bash
git clone <repo-url>
cd adverse-news-analyzer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core + UI + local AI support
pip install -e ".[all]"
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key (only needed for Claude models)
```

### Run (CLI)

```bash
# Single company with Claude API
python -m adverse_news.cli -c "ByteDance" -a "TikTok,Douyin" -m 12 -o bytedance_report.xlsx

# Single company with local Ollama model
python -m adverse_news.cli -c "ByteDance" --model llama3.1 -o bytedance_report.xlsx

# Batch from Excel file
python -m adverse_news.cli -i companies.xlsx -o ./reports/ -v
```

### Run (Streamlit UI)

```bash
streamlit run src/adverse_news/app.py
```

Then open http://localhost:8501 in your browser.

## Usage

### CLI Options

```
python -m adverse_news.cli [OPTIONS]

Required (one of):
  -c, --company TEXT        Company name to analyze
  -i, --input-excel FILE    Excel file with company list (batch mode)

Optional:
  -a, --aliases TEXT         Comma-separated aliases/short forms
  -m, --months INT           Search period in months (default: 12)
  -o, --output PATH          Output file or directory
      --model TEXT           LLM model (default: claude-sonnet-4-6)
      --api-key TEXT         Anthropic API key (or set ANTHROPIC_API_KEY in .env)
  -v, --verbose              Enable debug logging
```

### Batch Excel Input Format

| Column A (Company Name) | Column B (Aliases) |
|---|---|
| ByteDance | TikTok, Douyin |
| WeWork | WeWork Inc |
| Theranos | Theranos Inc |

- Row 1 is treated as a header (skipped)
- Column A: company name (required)
- Column B: comma-separated aliases (optional)

### Streamlit UI

The web interface provides two tabs:

- **Single Company** — type a company name and aliases, click Analyze, view color-coded results, download Excel
- **Batch (Excel Upload)** — upload an Excel file, analyze all companies, view summary table, download individual reports

The sidebar lets you:
- Switch between Claude (API) and Ollama (Local)
- Choose a specific model
- Set the search period (3-18 months)
- Select search languages (English, Chinese)

## Configuration

All settings can be configured via `.env` file or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (none) | Required for Claude models |
| `LLM_MODEL` | `claude-sonnet-4-6` | Default LLM model |
| `SEARCH_PERIOD_MONTHS` | `12` | Default search period |
| `MAX_ARTICLES_PER_QUERY` | `30` | Max articles per search query per source |
| `ARTICLE_TEXT_LIMIT` | `500` | Max chars of article text sent to LLM |
| `BATCH_SIZE` | `10` | Articles per LLM API call |
| `LANGUAGES` | `["en", "zh"]` | Languages to search |
| `MAX_PARSE_WORKERS` | `8` | Parallel threads for article parsing |

## LLM Provider Options

### Claude API (Cloud)

Best for accuracy and speed. Requires an Anthropic API key.

| Model | Speed | Cost per Company | Use Case |
|-------|-------|-----------------|----------|
| `claude-sonnet-4-6` | Fast (~30s) | ~$0.05-0.10 | Recommended default |
| `claude-haiku-4-5-20251001` | Fastest (~15s) | ~$0.01-0.02 | Budget option |
| `claude-opus-4-6` | Slower (~60s) | ~$0.50+ | Maximum accuracy |

### Ollama (Local)

Free, runs entirely on your machine. No data leaves your network. Requires [Ollama](https://ollama.com/) installed.

```bash
# Install Ollama, then pull a model:
ollama pull llama3.1
ollama pull qwen2.5
ollama pull gemma4:12b

# Use via CLI
python -m adverse_news.cli -c "ByteDance" --model llama3.1

# The Streamlit UI auto-detects installed Ollama models
```

**Speed note**: Local models are significantly slower than Claude API. A 30B+ parameter model may take 8-10 minutes for 25 articles. Smaller models (7B-12B) are faster but less accurate.

## How Article Scraping Works

The scraping happens in two distinct steps:

### Step 1: News Discovery (GNews + DDG)

These tools **do not scrape websites**. They query search indexes:

- **GNews** reads Google's public RSS feed — returns titles, URLs, dates, and publisher names
- **DDG** queries DuckDuckGo's search API — returns titles, URLs, and short body snippets

Both are queried for each alias in each language. Results are merged and deduplicated by URL.

### Step 2: Article Text Extraction (newspaper4k)

For each URL from Step 1, [newspaper4k](https://github.com/AndyTheFactory/newspaper4k) (the actively maintained fork of newspaper3k):

1. Downloads the HTML page via HTTP GET
2. Uses heuristics to identify the article body (strips ads, navigation, sidebars, footers)
3. Extracts: clean text, title, publish date, authors
4. Text is truncated to 500 characters before being sent to the LLM

If newspaper4k fails (403, timeout, paywall), the title alone is used for sentiment classification — this is usually sufficient for screening purposes.

Articles are parsed in parallel (8 threads by default) for speed.

## Limitations

### News Discovery
- **GNews may return 0 results** — Google can rate-limit or block RSS requests, especially with repeated queries from the same IP. The tool retries up to 3 times with exponential backoff (2s/4s/8s), but persistent rate-limiting from Google may require waiting or switching networks.
- **Google News RSS is the sole source** — the tool relies entirely on Google News RSS via GNews. If Google blocks your IP, no articles will be found. Adding alternative sources (NewsAPI.org, Brave Search) is a planned future improvement.
- **Result quantity** — each search query returns up to 30 articles. For popular companies with multiple aliases, a configurable cap (default 50) keeps the newest articles and drops older ones.
- **Short aliases are skipped** — aliases shorter than 3 characters (e.g., "WE") are excluded because they return too many irrelevant results.

### Article Parsing
- **Cloudflare-protected sites** return 403 (e.g., The Information, Seeking Alpha, Bloomberg, Reuters). These articles will only have the title available for analysis.
- **Paywalled sites** may return incomplete text or nothing at all.
- **JavaScript-rendered pages** cannot be parsed — newspaper4k does not execute JavaScript.
- **Typical success rate is 60-80%** — the remaining articles fall back to title-based classification.

### AI Classification
- **Sentiment accuracy depends on model quality** — Claude Sonnet provides the best results. Smaller local models may misclassify nuanced articles.
- **Batch classification** — articles are analyzed in batches of 10. The LLM sees limited context (500 chars) per article, which may miss nuance in long-form investigative pieces.
- **Language mixing** — Chinese articles are classified correctly by Claude but local models may struggle with bilingual content.
- **LLM hallucination** — risk factors and summaries are AI-generated and should be verified against the source article.

### Performance
- **Local LLM inference is slow** — a 30B+ parameter Ollama model takes ~3 minutes per batch of 10 articles. A full analysis of 30 articles may take 8-10 minutes.
- **No async/streaming** — the pipeline runs synchronously. The Streamlit UI may appear unresponsive during long LLM calls.

## Project Structure

```
adverse-news-analyzer/
├── pyproject.toml              # Dependencies and project metadata
├── .env.example                # Environment variable template
├── .gitignore
├── README.md
├── src/adverse_news/
│   ├── __init__.py
│   ├── config.py               # Settings (pydantic-settings, .env)
│   ├── models.py               # Data models: CompanyInput, ArticleData, SentimentResult, AnalysisReport
│   ├── analyzer.py             # Orchestrator: search -> parse -> classify -> report
│   ├── scraper/
│   │   ├── base.py             # Abstract NewsSource interface
│   │   ├── gnews_source.py     # Google News RSS via GNews library
│   │   ├── ddg_source.py       # DuckDuckGo news search via ddgs library
│   │   └── article_parser.py   # Full-text extraction via newspaper4k (parallel)
│   ├── llm/
│   │   ├── base.py             # LLMProvider Protocol (interface)
│   │   ├── prompts.py          # Shared prompt templates
│   │   ├── claude_provider.py  # Anthropic Claude API implementation
│   │   └── ollama_provider.py  # Ollama local model implementation
│   ├── report/
│   │   └── excel_writer.py     # Styled 3-sheet Excel report generation
│   ├── cli.py                  # Command-line interface (single + batch)
│   └── app.py                  # Streamlit web UI
└── tests/
```

## Future Improvements

- **`cloudscraper`** — drop-in replacement for `requests` that bypasses basic Cloudflare protection, improving article parsing success rate
- **Firecrawl / Playwright** — hosted or browser-based scraping for JavaScript-rendered and paywalled sites
- **FinBERT** — HuggingFace financial sentiment model as an additional local option (no Ollama required, purpose-built for financial text)
- **Async pipeline** — use `asyncio` + `aiohttp` for concurrent article downloading and LLM calls
- **Result caching** — cache scraped articles and LLM results to avoid redundant API calls when re-analyzing
- **Deduplication by content similarity** — detect near-duplicate articles (same event, different sources) using title similarity scoring
- **Additional news sources** — NewsAPI.org, Brave Search API, Tavily for broader coverage
- **PDF report option** — generate PDF reports alongside Excel for direct workpaper attachment

## License

MIT
