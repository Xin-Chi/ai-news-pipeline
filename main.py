"""每日 AI 快報 pipeline —— orchestrator。

這是一條 workflow(不是 agent):控制流由這支程式寫死,LLM 只在
「摘要」那一格被呼叫。你是編排者,LLM 是零件。
流程:抓取 → 去重 → 排序取 TopN → 逐篇摘要 → 渲染靜態頁。
用法:python main.py  /  python main.py --mock(不呼叫 LLM 測流程)"""
import os
import sys
from pathlib import Path
from fetchers import hackernews, arxiv
from stages import dedup, summarize, render

TOP_N = 12
ARXIV_QUOTA = 3  # arXiv 論文保底名額,不足就整個讓給 HN

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

def run(mock: bool = False) -> str:
    items = hackernews.fetch(limit=15) + arxiv.fetch(limit=10)
    print(f"[fetch] {len(items)} items")
    items = dedup.deduplicate(items)
    print(f"[dedup] {len(items)} items after dedup")

    # arXiv 沒有 HN 那種按讚分數,直接比分永遠選不上,所以保底留 ARXIV_QUOTA 個
    # 名額給它(不足就整個讓給 HN),其餘名額才由 HN 依分數搶。
    arxiv_picks = [it for it in items if it["source"] == "arXiv"][:ARXIV_QUOTA]
    hn_picks = sorted(
        (it for it in items if it["source"] != "arXiv"),
        key=lambda x: x.get("score", 0), reverse=True,
    )[: TOP_N - len(arxiv_picks)]
    items = hn_picks + arxiv_picks
    items = summarize.summarize_all(items, mock=mock)
    path = render.render(items)
    print(f"[render] wrote {path}")
    return path

if __name__ == "__main__":
    _load_dotenv()
    run(mock="--mock" in sys.argv)
