"""從 arXiv API 抓當日 AI 論文。cs.AI/cs.CL/cs.LG 涵蓋大多數 AI 論文,
論文自帶 abstract,直接是很好的摘要輸入。"""
import feedparser
import urllib.parse

ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]

def fetch(limit: int = 10) -> list[dict]:
    """回傳 [{title, url, source, abstract, id}],依最新提交排序。"""
    cat_query = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    params = {
        "search_query": cat_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": limit,
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    feed = feedparser.parse(url)
    items: list[dict] = []
    for e in feed.entries:
        items.append({
            "title": e.title.replace("\n", " ").strip(),
            "url": e.link,
            "source": "arXiv",
            "abstract": e.summary.replace("\n", " ").strip(),
            "id": e.id,
        })
    return items
