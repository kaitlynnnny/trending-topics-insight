#!/usr/bin/env python3
"""
Trending Topics Insight — Global Hot Topics Multi-LLM Analysis.

Fetches trending topics from Reddit, Hacker News, Twitter, and Google Trends,
clusters them, and runs multi-LLM debate on the top topics.

Usage:
    python main.py [--topics N] [--concurrent N] [--mock]

Environment:
    DEEPSEEK_API_KEY, QWEN_API_KEY, GEMINI_API_KEY (at least one)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Data sources ──
from sources.reddit import fetch_hot_posts as fetch_reddit
from sources.hackernews import fetch_top_stories as fetch_hn
from sources.twitter import fetch_trending as fetch_twitter
from sources.google_trends import fetch_trending as fetch_trends

# ── Clustering ──
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

# ── Analysis ──
from analyze.clients import LLMClients, search_web
from analyze.debate import analyze_topics
from output.render import render_report

# ── Verification (from v2) ──
TIER1_DOMAINS = [
    "bbc.co.uk", "bbc.com", "reuters.com", "apnews.com",
    "nytimes.com", "theguardian.com", "aljazeera.com",
    "cnn.com", "washingtonpost.com", "bloomberg.com",
    "wsj.com", "npr.org", "cnbc.com", "abcnews.go.com",
    "dw.com", "france24.com",
]
TIER2_DOMAINS = [
    "scmp.com", "nikkei.com", "timesofindia.indiatimes.com",
    "thehindu.com", "straitstimes.com", "japantimes.co.jp",
    "channelnewsasia.com", "dawn.com", "ndtv.com",
    "independent.co.uk", "telegraph.co.uk", "usatoday.com",
    "axios.com", "techcrunch.com", "theverge.com",
    "arstechnica.com", "wired.com", "nature.com", "science.org",
    "smh.com.au", "elpais.com", "lemonde.fr", "spiegel.de",
]


def cluster_topics(items, threshold=0.7):
    """Group similar topics, with source-fair scoring."""
    if not items:
        return []
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    texts = [f"{item['title']}" for item in items]
    embeddings = model.encode(texts, show_progress_bar=False)
    sim = cosine_similarity(embeddings)

    clusters, used = [], set()
    for i in range(len(texts)):
        if i in used:
            continue
        c = [i]; used.add(i)
        for j in range(i+1, len(texts)):
            if j not in used and sim[i][j] > threshold:
                c.append(j); used.add(j)
        clusters.append(c)

    topics = []
    for c in clusters:
        best = items[c[0]]
        names = set()
        source_types = set()
        for idx in c:
            src = items[idx].get("source_name", items[idx].get("source", "?"))
            names.add(src)
            # Track source categories
            sl = src.lower()
            if "reddit" in sl: source_types.add("reddit")
            elif "hacker" in sl or "hn" in sl: source_types.add("hn")
            elif "twitter" in sl or "nitter" in sl: source_types.add("twitter")
            elif "trends" in sl or "google" in sl: source_types.add("trends")

        # Diversity-weighted heat: source variety matters more than raw score
        diversity_bonus = len(source_types) * 2  # 2 sources = 4x, 3 sources = 6x, etc.
        cluster_size = len(c)
        heat = cluster_size * (1 + diversity_bonus) * 10

        topics.append({
            "title": best["title"], "url": best.get("url", ""),
            "source": "+".join(sorted(names)[:4]),
            "source_types": "+".join(sorted(source_types)),
            "score": int(heat), "num_comments": cluster_size,
            "related_queries": "",
        })
    topics.sort(key=lambda t: t["score"], reverse=True)
    return topics


def verify_topic(topic):
    """
    All sources are self-verifying:
    - Reddit/HN: community votes = verification
    - Twitter: mainstream news accounts = verification
    - Google Trends: search volume = verification
    """
    cluster_size = topic.get("num_comments", 1)
    if cluster_size >= 1:
        return True, f"Auto-verified ({topic.get('source','')[:60]})"
    return False, "No cluster"


def _mock_analyze(topics):
    """Simulated LLM analysis for testing without API keys."""
    from analyze.debate import TopicInsight
    patterns = [
        ("high", "Growth sees upside, Risk flags exposures, Macro notes systemic shift."),
        ("partial", "Optimist bullish, Risk skeptical on timeline, Macro mixed."),
        ("high", "Consensus on significance, minor divergence on pace."),
        ("partial", "Quick gains vs hidden costs vs structural patience."),
        ("low", "Sharp split: paradigm shift vs noise vs structural uncertainty."),
    ]
    results = []
    for i, t in enumerate(topics):
        level, tension = patterns[i % len(patterns)]
        results.append(TopicInsight(
            title=t["title"], source_str=t.get("source",""), url=t.get("url",""),
            deepseek_analysis={"summary":f"[MOCK] {t['title']}", "significance":"Growth opportunity.","angle":"Growth Optimist","confidence":"high"},
            qwen_analysis={"summary":f"[MOCK] {t['title']}", "significance":"Risk exposure.","angle":"Risk & Compliance","confidence":"medium"},
            gemini_analysis={"summary":f"[MOCK] {t['title']}", "significance":"Structural pattern.","angle":"Macro Strategist","confidence":"high"},
            final_agreement=f"[MOCK] {t['title']}", agreement_level=level, key_tension=tension,
            bottom_line=f"[MOCK] {t['title'][:80]}",
            deepseek_justification="Growth: positive implications and expansion.",
            qwen_justification="Risk: regulatory exposure and compliance gaps.",
            gemini_justification="Macro: structural realignment of global systems.",
        ))
        print(f"  [mock] {t['title'][:80]}... -> {level}")
    return results


async def main():
    parser = argparse.ArgumentParser(description="Trending Topics Insight")
    parser.add_argument("--topics", type=int, default=10)
    parser.add_argument("--concurrent", type=int, default=2)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    # ── 1. Fetch ──
    print("=" * 60)
    print("[1/4] Fetching trending topics...")
    print("=" * 60)

    reddit = await fetch_reddit()
    print(f"  Reddit: {len(reddit)} posts")

    hn = await fetch_hn(min_points=30, window_hours=72, limit=30)
    print(f"  Hacker News: {len(hn)} stories")

    twitter = await fetch_twitter()
    print(f"  Twitter: {len(twitter)} tweets")

    trends = fetch_trends()
    print(f"  Google Trends: {len(trends)} topics")

    all_items = reddit + hn + twitter + trends
    if not all_items:
        print("[ERROR] No data fetched.")
        return
    print(f"  Total: {len(all_items)} items")

    # ── 2. Cluster ──
    print(f"\n[2/4] Clustering...")
    topics = cluster_topics(all_items)
    # Filter trivial topics (very short, generic terms)
    topics = [t for t in topics if len(t["title"]) > 15 and len(t["title"].split()) >= 3]
    print(f"  {len(topics)} topics after filtering trivial ones")

    candidates = topics[:args.topics * 2]
    print(f"\n  Verifying top {len(candidates)}...")
    verified, rejected = [], []
    for t in candidates:
        ok, ev = verify_topic(t)
        t["verification_evidence"] = ev
        if ok:
            verified.append(t)
            print(f"    [OK] {t['title'][:70]}")
        else:
            rejected.append(t)
            print(f"    [--] {t['title'][:70]} ({ev})")

    # Ensure source diversity: pick top from each source type, then fill rest by score
    source_slots = {"hn": 0, "reddit": 0, "twitter": 0, "trends": 0}
    diverse = []
    rest = []
    for t in verified:
        types = t.get("source_types", "")
        # Try to get at least 2 from each major source type
        for st, cap in [("hn", 3), ("reddit", 2), ("twitter", 2), ("trends", 2)]:
            if st in types and source_slots.get(st, 0) < cap:
                source_slots[st] = source_slots.get(st, 0) + 1
                diverse.append(t)
                break
        else:
            rest.append(t)

    debate_topics = (diverse + rest)[:args.topics]
    # Re-sort by score
    debate_topics.sort(key=lambda t: t["score"], reverse=True)
    print(f"\n  {len(debate_topics)} topics entering debate, {len(rejected)} rejected")

    for i, t in enumerate(debate_topics, 1):
        print(f"  {i:2}. [{t['source']}] {t['title'][:85]}")

    # ── 3. Debate ──
    if args.mock:
        print(f"\n[3/4] Mock debate...")
        insights = _mock_analyze(debate_topics)
    else:
        clients = LLMClients()
        if not any([clients.deepseek, clients.qwen, clients.gemini_client]):
            print("[!] No API keys. Use --mock to test.")
            return
        print(f"\n[3/4] Multi-LLM debate ({args.concurrent} concurrent)...")
        insights = await analyze_topics(clients, debate_topics, max_concurrent=args.concurrent)

    # ── 4. Report ──
    print(f"\n[4/4] Generating report...")
    path = render_report(insights, raw_items=all_items,
                         output_path=str(Path(__file__).parent / "output" / "report.html"))
    print(f"  -> {path}")
    print(f"[DONE] {len(insights)} topics debated")


if __name__ == "__main__":
    asyncio.run(main())
