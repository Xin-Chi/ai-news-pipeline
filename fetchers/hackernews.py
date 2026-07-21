"""從 Hacker News API 抓熱門故事,只留下 AI 相關的。

HN 官方 API 免費、無金鑰,靠社群 upvote 排序,等於自帶
「相關性排序」——熱門的自然浮上來,省掉「什麼算重要新聞」的判斷。
"""
import requests
from fetchers.keywords import looks_ai

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

def fetch(limit: int = 15, scan: int = 100, timeout: int = 10) -> tuple[list[dict], str | None]:
    """回傳 (items, error)。items 是 [{title, url, source, score, id}];
    error 為 None 代表抓取成功(scan=掃前幾則;limit=通過粗篩最多取幾則),
    不為 None 代表 API 本身連不上,不會讓整個 pipeline 掛掉。"""
    try:
        ids = requests.get(HN_TOP, timeout=timeout).json()[:scan]
        items: list[dict] = []
        for sid in ids:
            story = requests.get(HN_ITEM.format(sid), timeout=timeout).json()
            if not story or story.get("type") != "story":
                continue
            title = story.get("title", "")
            if not looks_ai(title):
                continue
            items.append({
                "title": title,
                "url": story.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "source": "Hacker News",
                "score": story.get("score", 0),
                "id": f"hn-{sid}",
            })
            if len(items) >= limit:
                break
        return items, None
    except Exception as e:
        return [], str(e)
