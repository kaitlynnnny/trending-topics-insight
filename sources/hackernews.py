"""
Hacker News trending topics — Algolia API.
Fetches top stories by points in recent window.
"""

import aiohttp

HN_API = "https://hn.algolia.com/api/v1/search"


async def fetch_top_stories(min_points=100, window_hours=24, limit=30):
    """Fetch top HN stories."""
    import time
    now = int(time.time())
    from_ts = now - window_hours * 3600

    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{from_ts},points>={min_points}",
        "hitsPerPage": limit,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(HN_API, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

    posts = []
    for hit in data.get("hits", []):
        posts.append({
            "title": hit.get("title", ""),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "score": hit.get("points", 0),
            "num_comments": hit.get("num_comments", 0),
            "source": "hackernews",
            "source_name": "Hacker News",
        })
    return posts
