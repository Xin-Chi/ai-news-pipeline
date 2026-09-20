"""每日 AI 快報 pipeline —— orchestrator。

這是一條 workflow(不是 agent):控制流由這支程式寫死,LLM 只在
「摘要」那一格被呼叫。你是編排者,LLM 是零件。
流程:抓取 → 24 小時過濾 → 去重 → 依來源保底+優先順序選稿 → 抓原文全文
     → 逐篇摘要 → 渲染靜態頁 → 寄通知信。
用法:python main.py  /  python main.py --mock(不呼叫 LLM 測流程)"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from fetchers import hackernews, rss_source
from stages import dedup, fulltext, summarize, render, notify, verify

TOP_N = 25
RECENCY_WINDOW = 24 * 3600  # 只留過去 24 小時內發布的,不是「今天」而是「這一天以來」

# 依優先順序:(顯示名稱, 名額上限, 是否保底 1 篇, 抓取函式)
# 順序同時也是版面上的顯示順序與篩選按鈕的排列順序(見 render.py 的 SOURCE_ROWS)。
#
# 排序依據不只是主題分類,也對應「摘要含金量」:前面的來源有實質內文可以濃縮,
# 愈後面愈薄。HN 擺最後是因為它沒有內文可抓(見 fulltext.py),產出的摘要實際上
# 只是標題翻譯,排前面會讓品質最薄的卡片最先被看到。
#
# 保底的用意是避免排前面的來源當天發太多、把後面的擠到 0 篇。但天天都有大量
# 新文章的來源(HN、Ars Technica、TechCrunch)不需要這層保護——它們本來就搶得到,
# 保底名額留給發文頻率低、不保護就會消失的來源。
SOURCES = [
    # 大廠 blog
    ("OpenAI Blog", 5, True, lambda: rss_source.fetch(
        "https://openai.com/news/rss.xml", "OpenAI Blog", limit=5)),
    ("Anthropic Blog", 5, True, lambda: rss_source.fetch(
        "https://tim-hilde.github.io/anthropic-rss/rss.xml", "Anthropic Blog", limit=5)),
    ("Google DeepMind", 5, True, lambda: rss_source.fetch(
        "https://deepmind.google/blog/feed/basic/", "Google DeepMind", limit=5)),
    # 模型與硬體
    ("Qwen", 2, True, lambda: rss_source.fetch(
        "https://qwenlm.github.io/blog/index.xml", "Qwen", limit=2)),
    ("Hugging Face", 2, True, lambda: rss_source.fetch(
        "https://huggingface.co/blog/feed.xml", "Hugging Face", limit=2)),
    # NVIDIA blog 同時有遊戲、車用、醫療內容(實測首篇是 GeForce NOW 遊戲),必須過濾
    ("NVIDIA", 2, True, lambda: rss_source.fetch(
        "https://blogs.nvidia.com/feed/", "NVIDIA", limit=2, ai_only=True)),
    # 中文媒體(都要加關鍵字過濾,它們不是純 AI 站)
    ("iThome", 2, True, lambda: rss_source.fetch(
        "https://www.ithome.com.tw/taxonomy/term/3338/all/feed", "iThome", limit=2, ai_only=True)),
    ("TechNews", 2, True, lambda: rss_source.fetch(
        "https://technews.tw/tag/ai/feed/", "TechNews", limit=2, ai_only=True)),
    ("INSIDE", 2, True, lambda: rss_source.fetch(
        "https://www.inside.com.tw/feed/rss/", "INSIDE", limit=2, ai_only=True)),
    # 社群與外媒
    ("Hacker News", 5, True, lambda: hackernews.fetch(limit=15)),
    ("Ars Technica", 3, False, lambda: rss_source.fetch(
        "https://arstechnica.com/ai/feed/", "Ars Technica", limit=3)),
    ("TechCrunch", 3, False, lambda: rss_source.fetch(
        "https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch", limit=3)),
]


def _load_announcement() -> str:
    """讀專案根目錄的 announcement.txt 當作偶爾寫給讀者的公告,
    檔案不存在或整篇是空白就回傳空字串(頁面上不會顯示任何東西)。"""
    path = Path(__file__).parent / "announcement.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


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
    for label, _cap, _floor, fetch_fn in SOURCES:
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
    """保底 + 優先順序遞補:標記要保底的來源先各拿 1 篇,
    剩下名額再依 SOURCES 的順序、依各自上限去搶,湊到 TOP_N 就停。"""
    picked = {
        label: by_source[label][:1] if has_floor else []
        for label, _cap, has_floor, _fn in SOURCES
    }
    budget = TOP_N - sum(len(v) for v in picked.values())

    for label, cap, _has_floor, _fn in SOURCES:
        if budget <= 0:
            break
        items = by_source[label]
        already = len(picked[label])
        room = min(cap - already, len(items) - already, budget)
        if room > 0:
            picked[label] = items[: already + room]
            budget -= room

    return [it for label, _cap, _floor, _fn in SOURCES for it in picked[label]]


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

    # 選完才抓全文:只對真正會上榜的那幾篇發請求,不浪費在被淘汰的項目上。
    items = fulltext.enrich(items)

    items = summarize.summarize_all(items, mock=mock)
    announcement = _load_announcement()
    path = render.render(items, broken_sources=broken, announcement=announcement)
    print(f"[render] wrote {path}")

    recommendation = None if mock else summarize.recommend(items)

    # grounding 檢查:只觀測、不介入。整段包起來是因為網頁已經產生好了,
    # 檢查本身出問題不該讓整條 pipeline 失敗——跟 notify 同樣的處理原則。
    verification = None
    if not mock:
        try:
            verification = verify.run(items, datetime.now(render.TW).strftime("%Y-%m-%d %H:%M"))
            history = verify.append_history(verification)
            print(f"[verify] wrote {render.render_verify(history, verify.RETENTION_DAYS)}")
        except Exception as e:
            print(f"[warn] grounding 檢查失敗,略過: {e}")
            verification = None

    notify.send_daily_summary(
        items,
        datetime.now(render.TW).strftime("%Y-%m-%d %H:%M"),
        broken_sources=broken,
        recommendation=recommendation,
        verification=verification,
        dry_run=mock,
    )
    return path


if __name__ == "__main__":
    _load_dotenv()
    run(mock="--mock" in sys.argv)
