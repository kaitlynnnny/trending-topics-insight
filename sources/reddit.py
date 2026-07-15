"""
Reddit trending topics — public .json API.
Fetches hot posts from popular subreddits.
"""

import aiohttp
import asyncio
import os
from typing import Optional

SUBREDDITS = ["all", "worldnews", "technology", "science", "news"]
REDDIT_BASE = "https://www.reddit.com"
OLD_REDDIT = "https://old.reddit.com"
LIMIT_PER_SUB = 25
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15",
]


def _get_headers():
    import random
    return {"User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json"}


async def _fetch_subreddit(session, subreddit, base_url):
    url = f"{base_url}/r/{subreddit}/hot.json?limit={LIMIT_PER_SUB}&raw_json=1"
    try:
        async with session.get(url, headers=_get_headers(), timeout=15) as resp:
            if resp.status != 200:
                print(f"  [Reddit {resp.status}] {subreddit}")
                return []
            data = await resp.json(content_type=None)
    except Exception as e:
        print(f"  [Reddit error] {subreddit}: {e}")
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title", "")
        if not title or post.get("stickied"):
            continue
        posts.append({
            "title": title,
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "subreddit": post.get("subreddit", subreddit),
            "source": "reddit",
            "source_name": f"Reddit r/{post.get('subreddit', subreddit)}",
        })
    return posts


async def fetch_hot_posts(subreddits=None):
    if subreddits is None:
        subreddits = SUBREDDITS

    all_posts = []
    for base in (REDDIT_BASE, OLD_REDDIT):
        if all_posts:
            break
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [_fetch_subreddit(session, sub, base) for sub in subreddits]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_posts.extend(result)
        except Exception:
            continue

    # Dedup + sort by hotness
    all_posts.sort(key=lambda p: p["score"], reverse=True)
    seen = set()
    unique = []
    for p in all_posts:
        key = p["title"].lower()[:60].strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique
