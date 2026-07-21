"""渲染成靜態 HTML 寫到 docs/index.html。GitHub Pages 從 /docs serve,
每天 Action 跑完 commit,頁面自動更新。"""
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

TW = timezone(timedelta(hours=8))
DOCS = Path(__file__).resolve().parent.parent / "docs"

PAGE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日 AI 快報 · {date}</title>
<style>
  :root {{ --bg:#0d1117; --card:#161b22; --line:#30363d;
           --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff;
           --hn:#ffa657; --arxiv:#ff7b72; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
          font-family:-apple-system,"Noto Sans TC",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:720px; margin:0 auto; padding:32px 20px 64px; }}
  header h1 {{ font-size:26px; margin:0 0 4px; }}
  header p {{ color:var(--muted); margin:0 0 28px; font-size:14px; }}
  .item {{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--line);
           border-radius:12px; padding:16px 18px; margin-bottom:14px; }}
  .item.hn {{ border-left-color:var(--hn); }}
  .item.arxiv {{ border-left-color:var(--arxiv); }}
  .item .tag {{ font-size:12px; color:var(--accent); font-weight:600; }}
  .item.hn .tag {{ color:var(--hn); }}
  .item.arxiv .tag {{ color:var(--arxiv); }}
  .item h2 {{ font-size:16px; margin:6px 0 8px; }}
  .item h2 a {{ color:var(--text); text-decoration:none; }}
  .item h2 a:hover {{ text-decoration:underline; }}
  .item p {{ margin:0; color:var(--muted); font-size:14px; }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:32px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🗞️ 每日 AI 快報</h1>
    <p>{date} · 共 {count} 則 · 來源:Hacker News、arXiv · 自動生成</p>
  </header>
  {cards}
  <footer>由自動化 pipeline 每日排程生成 · 摘要僅依原文,連結直達原始出處</footer>
</div>
</body>
</html>"""

CARD = """<article class="item {slug}">
  <span class="tag">{source}</span>
  <h2><a href="{url}" target="_blank" rel="noopener">{title}</a></h2>
  <p>{summary}</p>
</article>"""

SOURCE_SLUG = {"Hacker News": "hn", "arXiv": "arxiv"}

def render(items: list) -> str:
    now = datetime.now(TW).strftime("%Y-%m-%d %H:%M")
    cards = "\n".join(
        CARD.format(
            slug=SOURCE_SLUG.get(it["source"], ""),
            source=html.escape(it["source"]),
            url=html.escape(it["url"], quote=True),
            title=html.escape(it["title"]),
            summary=html.escape(it.get("summary", "")),
        ) for it in items
    )
    DOCS.mkdir(exist_ok=True)
    page = PAGE.format(date=now, count=len(items), cards=cards)
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    return str(DOCS / "index.html")
