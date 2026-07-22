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
  :root {{
    --bg:#0b0e14; --card:#151a24; --line:#242b3a;
    --text:#e8ecf4; --muted:#8a93a6; --accent:#7c9eff;
    --openai:#6ee7c9; --openai-bg:rgba(110,231,201,0.14);
    --anthropic:#e8916f; --anthropic-bg:rgba(232,145,111,0.14);
    --deepmind:#7c9eff; --deepmind-bg:rgba(124,158,255,0.14);
    --ithome:#f0c93a; --ithome-bg:rgba(240,201,58,0.14);
    --technews:#5ec8e0; --technews-bg:rgba(94,200,224,0.14);
    --inside:#ff8fd1; --inside-bg:rgba(255,143,209,0.14);
    --hn:#ffb56b; --hn-bg:rgba(255,181,107,0.14);
    --hf:#ffd21e; --hf-bg:rgba(255,210,30,0.14);
    --arxiv:#ff8a8a; --arxiv-bg:rgba(255,138,138,0.14);
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; color:var(--text);
    font-family:"Segoe UI",-apple-system,"Noto Sans TC",sans-serif; line-height:1.65;
    background:
      radial-gradient(900px circle at 15% -10%, rgba(124,158,255,0.14), transparent 55%),
      radial-gradient(700px circle at 100% 0%, rgba(255,138,138,0.10), transparent 50%),
      var(--bg);
  }}
  .wrap {{ max-width:680px; margin:0 auto; padding:48px 20px 72px; }}
  header {{ margin-bottom:20px; }}
  .title-row {{ display:flex; align-items:flex-end; justify-content:space-between; gap:10px; }}
  header h1 {{ font-size:28px; margin:0 0 6px; letter-spacing:-0.01em; }}
  header p {{ color:var(--muted); margin:0; font-size:14px; }}
  .hits-badge {{ height:14px; opacity:.7; }}
  .source-alert {{ color:#ff6b6b; font-size:12.5px; margin:10px 0 0; }}
  .filter-bar {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:10px 12px; margin:20px 0 28px; }}
  .filter-bar label {{
    display:flex; align-items:center; justify-content:center; white-space:nowrap; line-height:1;
    font-size:12.5px; font-weight:600; color:var(--muted); cursor:pointer;
    background:rgba(124,158,255,0.07); border:1px solid rgba(124,158,255,0.2);
    padding:9px 10px; border-radius:999px; user-select:none;
    transition: background .15s ease, color .15s ease, border-color .15s ease;
  }}
  .filter-bar input {{ display:none; }}
  .filter-bar label.active {{ background:var(--accent); color:#0b0e14; border-color:var(--accent); }}
  .filter-bar label.disabled {{ opacity:.35; cursor:not-allowed; }}
  @media (max-width: 480px) {{ .filter-bar label {{ font-size:11px; padding:8px 6px; }} }}
  .item {{
    background:var(--card); border:1px solid var(--line);
    border-radius:16px; padding:18px 20px; margin-bottom:14px;
    transition: transform .15s ease, box-shadow .15s ease;
  }}
  .item:hover {{ transform:translateY(-2px); box-shadow:0 10px 26px rgba(0,0,0,0.32); }}
  .item-head {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:9px; }}
  .tag {{
    display:inline-block; font-size:11.5px; font-weight:700;
    padding:3px 10px; border-radius:999px;
  }}
  .item-time {{ font-size:11.5px; color:var(--muted); white-space:nowrap; }}
  .item.openai .tag {{ color:var(--openai); background:var(--openai-bg); }}
  .item.anthropic .tag {{ color:var(--anthropic); background:var(--anthropic-bg); }}
  .item.deepmind .tag {{ color:var(--deepmind); background:var(--deepmind-bg); }}
  .item.ithome .tag {{ color:var(--ithome); background:var(--ithome-bg); }}
  .item.technews .tag {{ color:var(--technews); background:var(--technews-bg); }}
  .item.inside .tag {{ color:var(--inside); background:var(--inside-bg); }}
  .item.hn .tag {{ color:var(--hn); background:var(--hn-bg); }}
  .item.hf .tag {{ color:var(--hf); background:var(--hf-bg); }}
  .item.arxiv .tag {{ color:var(--arxiv); background:var(--arxiv-bg); }}
  .item h2 {{ font-size:16.5px; margin:0 0 8px; font-weight:600; }}
  .item h2 a {{ color:var(--text); text-decoration:none; }}
  .item h2 a:hover {{ color:var(--accent); }}
  .item p {{ margin:0; color:var(--muted); font-size:14px; }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:36px; opacity:.7; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="title-row">
      <h1>🗞️ 每日 AI 快報</h1>
      <img class="hits-badge" src="https://hits.sh/xin-chi.github.io/ai-news-pipeline/{hits_key}.svg?style=flat-square&label=%F0%9F%91%80&color=242b3a&labelColor=151a24" alt="瀏覽次數" onerror="this.style.display='none'">
    </div>
    <p>蒐集當日來自三大 AI 科技報導、社群討論、中文科技新聞與 AI 學術文獻的最新動態,自動摘要每日更新</p>
    <p>{date} · 共 {count} 則</p>
    {broken_notice}
  </header>
  <div class="filter-bar" id="filterBar">{filter_checkboxes}</div>
  {cards}
  <footer>由自動化 pipeline 每日生成 · 摘要僅依原文,連結直達原始出處</footer>
</div>
<script>
  var boxes = document.querySelectorAll('#filterBar input[type=checkbox]');
  function applyFilter() {{
    var checked = [];
    boxes.forEach(function(b) {{
      b.closest('label').classList.toggle('active', b.checked);
      if (b.checked) checked.push(b.value);
    }});
    document.querySelectorAll('.item').forEach(function(it) {{
      var show = checked.length === 0 || checked.some(function(s) {{ return it.classList.contains(s); }});
      it.style.display = show ? '' : 'none';
    }});
  }}
  boxes.forEach(function(b) {{ b.addEventListener('change', applyFilter); }});
</script>
</body>
</html>"""

CARD = """<article class="item {slug}">
  <div class="item-head">
    <span class="tag">{source}</span>
    <span class="item-time">{time}</span>
  </div>
  <h2><a href="{url}" target="_blank" rel="noopener">{title}</a></h2>
  <p>{summary}</p>
</article>"""

# 順序等於預設顯示順序,也是 main.py 選稿時的優先順序。分成三行給篩選列用。
SOURCE_ROWS = [
    [("OpenAI Blog", "openai"), ("Anthropic Blog", "anthropic"), ("Google DeepMind", "deepmind")],
    [("iThome", "ithome"), ("TechNews", "technews"), ("INSIDE", "inside")],
    [("Hacker News", "hn"), ("Hugging Face", "hf"), ("arXiv", "arxiv")],
]
SOURCE_SLUG = [pair for row in SOURCE_ROWS for pair in row]
SOURCE_SLUG_MAP = dict(SOURCE_SLUG)


def render(items: list, broken_sources: list | None = None) -> str:
    now_dt = datetime.now(TW)
    now = now_dt.strftime("%Y-%m-%d %H:%M")
    hits_key = now_dt.strftime("%Y-%m-%d")  # 用日期當計數器 key,換一天等於自動歸零
    cards = "\n".join(
        CARD.format(
            slug=SOURCE_SLUG_MAP.get(it["source"], ""),
            source=html.escape(it["source"]),
            url=html.escape(it["url"], quote=True),
            title=html.escape(it["title"]),
            summary=html.escape(it.get("summary", "")),
            time=datetime.fromtimestamp(it["published"], TW).strftime("%m/%d %H:%M") if it.get("published") else "",
        ) for it in items
    )
    active_slugs = {SOURCE_SLUG_MAP.get(it["source"], "") for it in items}
    filter_checkboxes = "\n".join(
        f'<label{" class=\"disabled\" title=\"過去 24 小時內沒有新內容\"" if slug not in active_slugs else ""}>'
        f'<input type="checkbox" value="{slug}"{" disabled" if slug not in active_slugs else ""}> '
        f'{html.escape(name)}</label>'
        for name, slug in SOURCE_SLUG
    )
    broken_notice = ""
    if broken_sources:
        names = "、".join(html.escape(s) for s in broken_sources)
        broken_notice = f'<p class="source-alert">⚠️ {names} 來源目前抓取異常,暫時沒有更新</p>'

    DOCS.mkdir(exist_ok=True)
    page = PAGE.format(
        date=now, count=len(items), cards=cards, hits_key=hits_key,
        filter_checkboxes=filter_checkboxes, broken_notice=broken_notice,
    )
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    return str(DOCS / "index.html")
