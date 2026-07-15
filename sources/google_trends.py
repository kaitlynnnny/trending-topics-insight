"""
Google Trends — daily trending searches via official RSS feed.
No API key needed.
"""

import feedparser

TREND_REGIONS = [
    ("US", "United States"),
    ("GB", "United Kingdom"),
    ("JP", "Japan"),
    ("KR", "South Korea"),
    ("IN", "India"),
    ("DE", "Germany"),
    ("FR", "France"),
    ("BR", "Brazil"),
]

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"


def fetch_trending():
    topics = []
    for geo, name in TREND_REGIONS:
        url = RSS_URL.format(geo=geo)
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                if title:
                    topics.append({
                        "title": title,
                        "url": entry.get("ht:news_item_url", ""),
                        "score": 35,
                        "num_comments": 0,
                        "source": "google_trends",
                        "source_name": f"Google Trends ({name})",
                    })
        except Exception:
            continue

    seen = set()
    unique = []
    for t in topics:
        k = t["title"].lower().strip()
        if k and k not in seen:
            seen.add(k)
            unique.append(t)
    return unique
