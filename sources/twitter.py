"""
Twitter/X trending — via Nitter RSS (free, no API key).
Captures what's being discussed on Twitter in real-time.
"""

import feedparser
import aiohttp
import asyncio

# Twitter accounts that break/discuss trending topics
NITTER_ACCOUNTS = [
    ("https://nitter.net/BBCBreaking/rss", "Twitter @BBCBreaking"),
    ("https://nitter.net/Reuters/rss", "Twitter @Reuters"),
    ("https://nitter.net/AP/rss", "Twitter @AP"),
    ("https://nitter.net/Bloomberg/rss", "Twitter @Bloomberg"),
    ("https://nitter.net/CNNbrk/rss", "Twitter @CNNbrk"),
]


async def _fetch_nitter(session, url, source_name):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                return []
            xml = await resp.text()
    except Exception:
        return []

    feed = feedparser.parse(xml)
    posts = []
    for entry in feed.entries[:30]:
        title = entry.get("title", "")
        if not title:
            continue
        posts.append({
            "title": title,
            "url": entry.get("link", ""),
            "score": 0,
            "num_comments": 0,
            "source": "twitter",
            "source_name": source_name,
        })
    return posts


async def fetch_trending():
    all_posts = []
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_nitter(session, url, name) for url, name in NITTER_ACCOUNTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_posts.extend(result)
    return all_posts
