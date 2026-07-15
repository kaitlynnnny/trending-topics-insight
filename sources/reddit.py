"""
Reddit trending topics via RSS feeds.
NOT the JSON API — RSS is less aggressively blocked.
"""

import asyncio
import aiohttp
import feedparser

SUBREDDITS = ["all", "worldnews", "technology", "science", "news"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


async def _fetch_rss(session, subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/.rss?limit=25"
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            print(f"  [Reddit {resp.status}] r/{subreddit}")
            if resp.status != 200:
                return []
            xml = await resp.text()
            feed = feedparser.parse(xml)
    except Exception as e:
        print(f"  [Reddit error] r/{subreddit}: {e}")
        return []

    posts = []
    for entry in feed.entries[:25]:
        title = entry.get("title", "")
        if not title:
            continue
        posts.append({
            "title": title,
            "url": entry.get("link", ""),
            "score": 0,
            "num_comments": 0,
            "source": "reddit",
            "source_name": f"Reddit r/{subreddit}",
        })
    return posts


async def fetch_hot_posts(subreddits=None):
    if subreddits is None:
        subreddits = SUBREDDITS

    all_posts = []
    try:
        jar = aiohttp.CookieJar()
        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            for i, sub in enumerate(subreddits):
                if i > 0:
                    await asyncio.sleep(2)  # avoid 429 rate limit
                posts = await _fetch_rss(session, sub)
                if not posts:
                    await asyncio.sleep(3)
                    posts = await _fetch_rss(session, sub)  # retry once
                all_posts.extend(posts)
    except Exception:
        pass

    seen = set()
    unique = []
    for p in all_posts:
        key = p["title"].lower()[:60].strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique
