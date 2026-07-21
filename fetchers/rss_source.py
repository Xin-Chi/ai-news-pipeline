"""通用 RSS/Atom 抓取器,給沒有專屬 API 的來源共用(官方 blog、中文新聞站)。
回傳格式跟其他 fetcher 一致:(items, error)。抓取失敗(網路、feed 格式壞掉)
不會丟例外,error 帶回原因,讓 main.py 決定要不要在頁面上顯示「來源異常」。
"""
import re
import feedparser
import requests
from fetchers.keywords import looks_ai

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").replace("\xa0", " ").strip()


def fetch(
    feed_url: str, source: str, limit: int = 10, timeout: int = 15, ai_only: bool = False
) -> tuple[list[dict], str | None]:
    """回傳 (items, error)。items 是 [{title, url, source, abstract, id}]。
    ai_only=True 時,標題+摘要都不含 AI 關鍵字的文章會被濾掉——給沒有 AI 專屬
    分類、內容包山包海的綜合新聞站(例如 INSIDE)用,避免抓到不相干的新聞。"""
    try:
        resp = requests.get(feed_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            raise ValueError(str(feed.bozo_exception))
    except Exception as e:
        return [], str(e)

    items: list[dict] = []
    for e in feed.entries:
        title = _strip_html(getattr(e, "title", ""))
        abstract = _strip_html(getattr(e, "summary", ""))
        if ai_only and not looks_ai(f"{title} {abstract}"):
            continue
        items.append({
            "title": title,
            "url": getattr(e, "link", ""),
            "source": source,
            "abstract": abstract,
            "id": getattr(e, "id", getattr(e, "link", "")),
        })
        if len(items) >= limit:
            break
    return items, None
