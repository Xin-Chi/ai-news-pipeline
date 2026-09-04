"""從 arXiv API 抓當日 AI 論文。cs.AI/cs.CL/cs.LG 涵蓋大多數 AI 論文,
論文自帶 abstract,直接是很好的摘要輸入。"""
import calendar
import time
import feedparser
import urllib.parse

ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
MAX_ATTEMPTS = 2
RETRY_DELAY = 3  # 秒;偶爾會收到不完整/損毀的 XML(疑似網路傳輸瞬斷),重試一次通常就好

def fetch(limit: int = 10) -> tuple[list[dict], str | None]:
    """回傳 (items, error)。items 依最新提交排序,error 為 None 代表抓取成功。"""
    cat_query = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    params = {
        "search_query": cat_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": limit,
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                raise ValueError(str(feed.bozo_exception))
            items: list[dict] = []
            for e in feed.entries:
                published = calendar.timegm(e.published_parsed) if getattr(e, "published_parsed", None) else None
                items.append({
                    "title": e.title.replace("\n", " ").strip(),
                    "url": e.link,
                    "source": "arXiv",
                    "abstract": e.summary.replace("\n", " ").strip(),
                    "id": e.id,
                    "published": published,
                })
            return items, None
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_ATTEMPTS - 1:
                print(f"[warn] arXiv 第 {attempt + 1} 次抓取失敗,{RETRY_DELAY} 秒後重試: {last_error}")
                time.sleep(RETRY_DELAY)
    return [], last_error
