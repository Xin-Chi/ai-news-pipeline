"""從 Hacker News API 抓熱門故事,只留下 AI 相關的。

HN 官方 API 免費、無金鑰,靠社群 upvote 排序,等於自帶
「相關性排序」——熱門的自然浮上來,省掉「什麼算重要新聞」的判斷。
"""
import requests

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral", "qwen",
    "openai", "anthropic", "deepmind", "hugging face", "transformer",
    "diffusion", "rag", "fine-tun", "embedding", "neural", "machine learning",
    "deep learning", "agent", "inference", "pytorch", "tensorflow",
]

def _looks_ai(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in AI_KEYWORDS)

def fetch(limit: int = 15, scan: int = 100, timeout: int = 10) -> list[dict]:
    """回傳 [{title, url, source, score, id}]。scan=掃前幾則;limit=通過粗篩最多取幾則。"""
    ids = requests.get(HN_TOP, timeout=timeout).json()[:scan]
    items: list[dict] = []
    for sid in ids:
        story = requests.get(HN_ITEM.format(sid), timeout=timeout).json()
        if not story or story.get("type") != "story":
            continue
        title = story.get("title", "")
        if not _looks_ai(title):
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
    return items
