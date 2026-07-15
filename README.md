# Trending Topics Insight

Daily automated pipeline: **Reddit + Hacker News + Google Trends + Twitter → clustering → multi-LLM debate → HTML report**.

## Quick Start

```bash
git clone https://github.com/kaitlynnnny/trending-topics-insight.git
cd trending-topics-insight
pip install -r requirements.txt

# Test without API keys
python main.py --mock --topics 10

# Real run (needs API keys in .env)
python main.py --topics 20 --concurrent 2
```

## API Keys

Copy `.env.example` to `.env` and fill in at least one:

```
DEEPSEEK_API_KEY=sk-...     # platform.deepseek.com
QWEN_API_KEY=sk-...         # dashscope.aliyun.com
GEMINI_API_KEY=...          # aistudio.google.com
```

## How It Works

1. **Fetch** trending topics from Reddit r/all, Hacker News, Google Trends, and Twitter (via Nitter RSS)
2. **Cluster** similar topics with sentence-transformers embeddings
3. **Debate** top topics with 3 LLMs independently analyzing from their own perspectives, then synthesized
4. **Render** a clean HTML report with Excel/Word/PDF export

## Data Sources

| Source | Method | Items |
|--------|--------|-------|
| Reddit | RSS (r/all, r/worldnews, r/technology, r/science, r/news) | ~25-50 |
| Hacker News | Algolia API (past 72h, ≥30 points) | ~30 |
| Google Trends | Official RSS (8 regions) | ~80 |
| Twitter | Nitter RSS (BBCBreaking, Reuters, AP, Bloomberg, CNNbrk) | ~100 |

Twitter is used as a cross-source boost signal — it adds weight to topics also appearing on other platforms but does not generate standalone debate topics.

## File Structure

```
├── main.py              # Pipeline orchestrator
├── sources/             # Data fetchers
│   ├── reddit.py
│   ├── hackernews.py
│   ├── twitter.py
│   └── google_trends.py
├── analyze/             # Debate engine
│   ├── clients.py       # LLM wrappers
│   └── debate.py        # Independent analysis + Synthesizer
├── output/
│   └── render.py        # HTML report generator
└── requirements.txt
```

MIT
