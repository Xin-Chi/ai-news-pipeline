"""每日 AI 快報 pipeline —— orchestrator。

這是一條 workflow(不是 agent):控制流由這支程式寫死,LLM 只在
「摘要」那一格被呼叫。你是編排者,LLM 是零件。
流程:抓取 → 去重 → 依來源保底+優先順序選稿 → 逐篇摘要 → 渲染靜態頁。
用法:python main.py  /  python main.py --mock(不呼叫 LLM 測流程)"""
import os
import sys
import time
from pathlib import Path
from fetchers import hackernews, arxiv, rss_source
from stages import dedup, summarize, render

TOP_N = 20
FLOOR_PER_SOURCE = 1  # 每個來源保底名額,避免排前面的來源當天發太多把後面擠到 0 篇
RECENCY_WINDOW = 24 * 3600  # 只留過去 24 小時內發布的,不是「今天」而是「這一天以來」

# 依優先順序:(顯示名稱, 保底後的名額上限, 抓取函式)
# 官方 blog 用 RSS,沒有 HN 那種讚數可比,依發文時間新舊排序(rss_source 已處理)。
SOURCES = [
    ("OpenAI Blog", 5, lambda: rss_source.fetch("https://openai.com/news/rss.xml", "OpenAI Blog", limit=5)),
    ("Anthropic Blog", 5, lambda: rss_source.fetch("https://tim-hilde.github.io/anthropic-rss/rss.xml", "Anthropic Blog", limit=5)),
    ("Google DeepMind", 5, lambda: rss_source.fetch("https://deepmind.google/blog/feed/basic/", "Google DeepMind", limit=5)),
    ("iThome", 2, lambda: rss_source.fetch(
        "https://www.ithome.com.tw/taxonomy/term/3338/all/feed", "iThome", limit=2, ai_only=True)),
    ("TechNews", 2, lambda: rss_source.fetch(
        "https://technews.tw/tag/ai/feed/", "TechNews", limit=2, ai_only=True)),
    ("INSIDE", 2, lambda: rss_source.fetch(
        "https://www.inside.com.tw/feed/rss/", "INSIDE", limit=2, ai_only=True)),
    ("Hacker News", 5, lambda: hackernews.fetch(limit=15)),
    ("Hugging Face", 2, lambda: rss_source.fetch("https://huggingface.co/blog/feed.xml", "Hugging Face", limit=2)),
    ("arXiv", 2, lambda: arxiv.fetch(limit=10)),
]


def _load_dotenv() -> None:
    """從專案根目錄的 .env 讀 KEY=VALUE,設進 os.environ(不覆蓋既有的)。"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _fetch_all() -> tuple[dict, list[str]]:
    """回傳 {來源名稱: items} 以及抓取失敗(不是「今天沒發文」,是抓取本身出錯)的來源清單。"""
    by_source, broken = {}, []
    for label, _cap, fetch_fn in SOURCES:
        items, error = fetch_fn()
        by_source[label] = items
        if error:
            broken.append(label)
            print(f"[warn] {label} 抓取失敗: {error}")
    return by_source, broken


def _filter_recent(by_source: dict) -> dict:
    """只留過去 24 小時內發布的文章。沒有 published 時間的(理論上不該發生,
    但防禦性處理)一律當作過舊排除,不冒險把不確定日期的東西當新聞。"""
    cutoff = time.time() - RECENCY_WINDOW
    return {
        label: [it for it in items if it.get("published") and it["published"] >= cutoff]
        for label, items in by_source.items()
    }


def _select(by_source: dict) -> list[dict]:
    """保底 + 優先順序遞補:每個來源先保底 FLOOR_PER_SOURCE 篇,
    剩下名額依 SOURCES 的順序、依各自上限去搶,湊到 TOP_N 就停。"""
    picked = {label: items[:min(FLOOR_PER_SOURCE, cap)] for label, cap, _ in SOURCES for items in [by_source[label]]}
    budget = TOP_N - sum(len(v) for v in picked.values())

    for label, cap, _ in SOURCES:
        if budget <= 0:
            break
        items = by_source[label]
        already = len(picked[label])
        room = min(cap - already, len(items) - already, budget)
        if room > 0:
            picked[label] = items[: already + room]
            budget -= room

    return [it for label, _cap, _fn in SOURCES for it in picked[label]]


def run(mock: bool = False) -> str:
    by_source, broken = _fetch_all()
    total_fetched = sum(len(v) for v in by_source.values())
    print(f"[fetch] {total_fetched} items from {len(SOURCES)} sources")

    by_source = _filter_recent(by_source)
    print(f"[recency] {sum(len(v) for v in by_source.values())} items within {RECENCY_WINDOW // 3600}h")

    # 去重要看跨來源的重複(例如同一則新聞被兩個中文站都報),所以先攤平去重,
    # 再依原本的來源分組還原,交給 _select 做保底+優先順序選稿。
    flat = [it for items in by_source.values() for it in items]
    flat = dedup.deduplicate(flat)
    kept_ids = {it["id"] for it in flat}
    by_source = {label: [it for it in items if it["id"] in kept_ids] for label, items in by_source.items()}
    print(f"[dedup] {len(flat)} items after dedup")

    items = _select(by_source)
    print(f"[select] {len(items)} items chosen (target {TOP_N})")

    items = summarize.summarize_all(items, mock=mock)
    path = render.render(items, broken_sources=broken)
    print(f"[render] wrote {path}")
    return path


if __name__ == "__main__":
    _load_dotenv()
    run(mock="--mock" in sys.argv)
