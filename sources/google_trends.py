"""
Google Trends — daily trending searches.
Captures what the world is searching for.
"""

from pytrends.request import TrendReq


def fetch_trending():
    topics = []
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=10)
    except Exception:
        return topics

    regions = ["united_states", "united_kingdom", "japan", "south_korea",
               "india", "germany", "france", "brazil"]
    for region in regions:
        try:
            daily = pytrends.trending_searches(pn=region)
            if daily is not None and not daily.empty:
                for _, row in daily.head(10).iterrows():
                    topics.append({
                        "title": str(row.iloc[0]),
                        "url": "",
                        "score": 35,
                        "num_comments": 0,
                        "source": "google_trends",
                        "source_name": f"Google Trends ({region.replace('_', ' ').title()})",
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
