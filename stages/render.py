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
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20viewBox%3D%270%200%20100%20100%27%3E%3Ctext%20y%3D%27.9em%27%20font-size%3D%2790%27%3E%E2%98%95%3C/text%3E%3C/svg%3E">
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
    --qwen:#a78bfa; --qwen-bg:rgba(167,139,250,0.14);
    --nvidia:#76b900; --nvidia-bg:rgba(118,185,0,0.16);
    --ars:#ff8a8a; --ars-bg:rgba(255,138,138,0.14);
    --techcrunch:#5eead4; --techcrunch-bg:rgba(94,234,212,0.14);
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
  .version {{
    font-size:13px; font-weight:600; color:var(--muted);
    margin-left:6px; vertical-align:baseline; letter-spacing:0;
  }}
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
  .announcement {{
    background:rgba(255,181,107,0.09); border:1px solid rgba(255,181,107,0.28);
    border-radius:12px; padding:14px 16px; margin:0 0 20px;
    font-size:14px; line-height:1.6; color:var(--text);
  }}
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
  .item.qwen .tag {{ color:var(--qwen); background:var(--qwen-bg); }}
  .item.nvidia .tag {{ color:var(--nvidia); background:var(--nvidia-bg); }}
  .item.ars .tag {{ color:var(--ars); background:var(--ars-bg); }}
  .item.techcrunch .tag {{ color:var(--techcrunch); background:var(--techcrunch-bg); }}
  .item h2 {{ font-size:16.5px; margin:0 0 8px; font-weight:600; }}
  /* 摘要素材來源標記:黃=全文、綠=RSS 摘要、灰=只有標題。
     刻意不加圖例或說明文字,這是給自己觀察摘要品質用的。 */
  /* item-head 是 space-between 的 flex,三個子元素會被均分推開。
     margin-right:auto 把多餘空間全吃掉,色點就緊貼在來源標籤旁邊,時間照樣靠右。 */
  .dot {{
    width:7px; height:7px; border-radius:50%; flex:none;
    margin-right:auto;  /* 左邊距離靠 item-head 的 gap:10px 就夠了 */
  }}
  .dot.full {{ background:#e8b339; }}
  .dot.rss {{ background:#5ecb8a; }}
  .dot.title {{ background:#5a6376; }}
  .item h2 a {{ color:var(--text); text-decoration:none; }}
  .item h2 a:hover {{ color:var(--accent); }}
  .item p {{ margin:0; color:var(--muted); font-size:14px; }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:36px; opacity:.7; }}
  footer a {{ color:inherit; text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="title-row">
      <h1>🗞️ 每日 AI 快報<span class="version">v2</span></h1>
      <img class="hits-badge" src="https://hits.sh/xin-chi.github.io/ai-news-pipeline/{hits_key}.svg?style=flat-square&label=%F0%9F%91%80&color=242b3a&labelColor=151a24" alt="瀏覽次數" onerror="this.style.display='none'">
    </div>
    <p>蒐集當日來自三大 AI 實驗室、模型與硬體廠商、中文科技新聞、國外科技媒體與社群討論的最新動態,自動摘要每日更新</p>
    <p>{date} · 共 {count} 則</p>
    {broken_notice}
  </header>
  <div class="filter-bar" id="filterBar">{filter_checkboxes}</div>
  {announcement_html}
  {cards}
  <footer>由自動化 pipeline 每日生成 · 摘要僅依原文,連結直達原始出處 · <a href="verify/">摘要品質檢查</a></footer>
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
    <span class="dot {body_source}"></span>
    <span class="item-time">{time}</span>
  </div>
  <h2><a href="{url}" target="_blank" rel="noopener">{title}</a></h2>
  <p>{summary}</p>
</article>"""

# 順序等於預設顯示順序,也是 main.py 選稿時的優先順序。分四列給篩選列用(4×3)。
SOURCE_ROWS = [
    [("OpenAI Blog", "openai"), ("Anthropic Blog", "anthropic"), ("Google DeepMind", "deepmind")],
    [("Qwen", "qwen"), ("Hugging Face", "hf"), ("NVIDIA", "nvidia")],
    [("iThome", "ithome"), ("TechNews", "technews"), ("INSIDE", "inside")],
    [("Hacker News", "hn"), ("Ars Technica", "ars"), ("TechCrunch", "techcrunch")],
]
SOURCE_SLUG = [pair for row in SOURCE_ROWS for pair in row]
SOURCE_SLUG_MAP = dict(SOURCE_SLUG)


VERIFY_PAGE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20viewBox%3D%270%200%20100%20100%27%3E%3Ctext%20y%3D%27.9em%27%20font-size%3D%2790%27%3E%E2%98%95%3C/text%3E%3C/svg%3E">
<title>摘要品質檢查 · 每日 AI 快報</title>
<style>
  :root {{
    --bg:#0b0e14; --card:#151a24; --line:#242b3a;
    --text:#e8ecf4; --muted:#8a93a6; --accent:#7c9eff;
    --ok:#5ecb8a; --warn:#e8b339; --bad:#ff8a8a;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; color:var(--text);
    font-family:"Segoe UI",-apple-system,"Noto Sans TC",sans-serif; line-height:1.65;
    background:
      radial-gradient(900px circle at 15% -10%, rgba(124,158,255,0.14), transparent 55%),
      var(--bg);
  }}
  .wrap {{ max-width:760px; margin:0 auto; padding:48px 20px 72px; }}
  a {{ color:var(--accent); }}
  header h1 {{ font-size:26px; margin:0 0 6px; letter-spacing:-0.01em; }}
  header p {{ color:var(--muted); margin:0 0 4px; font-size:14px; }}
  .back {{ display:inline-block; margin-bottom:22px; font-size:13px; text-decoration:none; }}
  .stats {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin:22px 0 32px; }}
  .stat {{
    background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:14px 12px; text-align:center;
  }}
  .stat .num {{ display:block; font-size:22px; font-weight:700; letter-spacing:-0.02em; }}
  .stat .lbl {{ font-size:12px; color:var(--muted); }}
  h2 {{ font-size:16px; margin:32px 0 12px; font-weight:600; }}
  .note {{
    background:rgba(124,158,255,0.07); border:1px solid rgba(124,158,255,0.2);
    border-radius:12px; padding:13px 15px; font-size:13px; color:var(--muted); line-height:1.7;
  }}
  .note b {{ color:var(--text); font-weight:600; }}
  .note p {{ margin:0; }}
  .note ol {{ margin:6px 0 10px; padding-left:20px; }}
  .note li {{ margin:2px 0; }}
  .flag {{
    background:var(--card); border:1px solid var(--line); border-left:3px solid var(--warn);
    border-radius:12px; padding:14px 16px; margin-bottom:10px;
  }}
  .flag-head {{ display:flex; gap:10px; align-items:center; font-size:11.5px; color:var(--muted); margin-bottom:6px; flex-wrap:wrap; }}
  .flag h3 {{ font-size:14.5px; margin:0 0 6px; font-weight:600; }}
  .flag h3 a {{ color:var(--text); text-decoration:none; }}
  .flag h3 a:hover {{ color:var(--accent); }}
  .flag .sum {{ font-size:13px; color:var(--muted); margin:0 0 8px; }}
  .flag .why {{ font-size:13px; color:var(--warn); margin:0; }}
  .empty {{ color:var(--muted); font-size:14px; }}
  .cap {{ color:var(--muted); font-size:12.5px; margin:-4px 0 12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{
    text-align:right; font-weight:600; color:var(--muted); font-size:12px;
    padding:8px 10px; border-bottom:1px solid var(--line); white-space:nowrap;
  }}
  th:first-child, td:first-child {{ text-align:left; }}
  th.w {{ width:130px; }}
  td {{ text-align:right; padding:8px 10px; border-bottom:1px solid rgba(36,43,58,0.5); white-space:nowrap; }}
  td.ok {{ color:var(--ok); }}
  td.warn {{ color:var(--warn); }}
  td.muted {{ color:var(--muted); }}
  /* 通過率:數字 + 一條純 CSS 的長條,不需要任何圖表函式庫 */
  .rate {{ display:flex; align-items:center; gap:8px; justify-content:flex-end; }}
  .rate .bar {{ flex:1; height:6px; border-radius:3px; background:var(--line); overflow:hidden; max-width:72px; }}
  .rate .fill {{ display:block; height:100%; background:var(--ok); }}
  .rate .pct {{ min-width:34px; }}
  .dotmark {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; vertical-align:middle; }}
  .scroll {{ overflow-x:auto; }}
  @media (max-width: 520px) {{ .stats {{ grid-template-columns:repeat(2, 1fr); }} }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:40px; opacity:.7; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>摘要品質檢查</h1>
    <p>每天自動驗證每則摘要是不是真的有原文根據,結果公開記錄在這裡。</p>
    <a class="back" href="../">← 回每日 AI 快報</a>
  </header>

  <div class="stats">
    <div class="stat"><span class="num">{checked}</span><span class="lbl">累計檢查</span></div>
    <div class="stat"><span class="num" style="color:var(--ok)">{pass_rate}</span><span class="lbl">通過率</span></div>
    <div class="stat"><span class="num" style="color:var(--warn)">{flagged}</span><span class="lbl">被標記</span></div>
    <div class="stat"><span class="num" style="color:var(--muted)">{days}</span><span class="lbl">記錄天數</span></div>
  </div>

  <div class="note">
    <p>每則摘要要過三關:</p>
    <ol>
      <li>摘要不能跟標題一模一樣</li>
      <li>摘要裡的數字,原文必須找得到</li>
      <li>交給另一次 LLM 呼叫,判斷有沒有原文沒講的內容或誇大</li>
    </ol>
    <p>驗的是<b>模型當初真正看到的那份文字</b>。Hacker News 沒有內文可抓,不列入檢查。</p>
  </div>

  <h2>依摘要素材分組</h2>
  <p class="cap">摘要是拿什麼產生的,對應首頁標題旁的色點。這張表要回答的是:餵全文真的比餵 RSS 摘要可靠嗎?</p>
  <div class="scroll"><table>
    <tr><th>素材</th><th>檢查</th><th>通過</th><th>標記</th><th class="w">通過率</th></tr>
    {body_rows}
  </table></div>

  <h2>依來源分組</h2>
  <p class="cap">通過率由低到高排,最需要留意的排在最上面。</p>
  <div class="scroll"><table>
    <tr><th>來源</th><th>檢查</th><th>通過</th><th>標記</th><th class="w">通過率</th></tr>
    {source_rows}
  </table></div>

  <h2>每日紀錄</h2>
  <div class="scroll"><table>
    <tr><th>日期</th><th>檢查</th><th>通過</th><th>標記</th><th class="w">通過率</th></tr>
    {day_rows}
  </table></div>

  <h2>被標記的項目</h2>
  {flags}

  <footer>由自動化 pipeline 每日生成 · 保留最近 {retention} 天</footer>
</div>
</body>
</html>"""

FLAG_CARD = """<div class="flag">
  <div class="flag-head"><span>{date}</span><span>·</span><span>{source}</span></div>
  <h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
  <p class="sum">產生的摘要:{summary}</p>
  <p class="why">{problems}</p>
</div>"""


STATUS_KEYS = ("total", "passed", "flagged", "unverifiable", "error")
# 素材類型的顯示名稱與色點,對應首頁標題旁的那顆點
BODY_LABELS = [("full", "全文", "#e8b339"), ("rss", "RSS 摘要", "#5ecb8a"), ("title", "僅標題", "#5a6376")]


def _merge(groups: list[dict]) -> dict:
    """把多天的分組統計加總成一份 {分組名: {狀態: 次數}}。"""
    out = {}
    for g in groups:
        for name, counts in g.items():
            d = out.setdefault(name, dict.fromkeys(STATUS_KEYS, 0))
            for k in STATUS_KEYS:
                d[k] += counts.get(k, 0)
    return out


def _checked(d: dict) -> int:
    """真正驗過的則數。

    刻意不用 total:「無從檢查」的項目(HN 沒有內文可抓,只能從標題產生摘要)
    從頭到尾沒被驗過,把它們算進檢查統計只會讓數字難看又沒有意義。資料本身
    還是完整存在 history.json 裡,只是不顯示在這頁上。
    """
    return d.get("passed", 0) + d.get("flagged", 0)


def _rate(d: dict) -> float | None:
    c = _checked(d)
    return d.get("passed", 0) / c * 100 if c else None


def _stat_row(label: str, d: dict) -> str:
    pct = _rate(d)
    rate_cell = ('<td class="muted">—</td>' if pct is None else
                 f'<td><div class="rate"><span class="bar">'
                 f'<span class="fill" style="width:{pct:.0f}%"></span></span>'
                 f'<span class="pct">{pct:.0f}%</span></div></td>')
    return (
        f'<tr><td>{label}</td>'
        f'<td>{_checked(d)}</td>'
        f'<td class="ok">{d.get("passed", 0)}</td>'
        f'<td class="{"warn" if d.get("flagged") else "muted"}">{d.get("flagged", 0)}</td>'
        f'{rate_cell}</tr>'
    )


def render_verify(history: list, retention: int) -> str:
    """把 grounding 檢查的歷史紀錄渲染成 docs/verify/index.html。"""
    newest_first = sorted(history, key=lambda x: x.get("date", ""), reverse=True)
    overall = {k: sum(d.get(k, 0) for d in history) for k in STATUS_KEYS}
    overall_pct = _rate(overall)
    pass_rate = "—" if overall_pct is None else f"{overall_pct:.0f}%"

    by_body = _merge([d.get("by_body_source", {}) for d in history])
    body_rows = [
        _stat_row(f'<span class="dotmark" style="background:{color}"></span>{label}',
                  by_body.get(key, {}))
        for key, label, color in BODY_LABELS
        if _checked(by_body.get(key, {}))  # 「僅標題」整列都是沒驗過的,不列出來
    ]

    # 通過率由低到高:最需要留意的來源排最上面,所以這張表的順序每天都可能變。
    # 完全沒驗過的來源(HN)不列出來。
    by_source = _merge([d.get("by_source", {}) for d in history])
    source_rows = [
        _stat_row(html.escape(name), d)
        for name, d in sorted(
            ((n, d) for n, d in by_source.items() if _checked(d)),
            key=lambda kv: (_rate(kv[1]), -_checked(kv[1])),
        )
    ]

    day_rows = [_stat_row(html.escape(d.get("date", "")), d) for d in newest_first]

    flag_cards = [
        FLAG_CARD.format(
            date=html.escape(d.get("date", "")),
            source=html.escape(f.get("source", "")),
            url=html.escape(f.get("url", ""), quote=True),
            title=html.escape(f.get("title", "")),
            summary=html.escape(f.get("summary", "")),
            problems=html.escape("；".join(f.get("problems", []))),
        )
        for d in newest_first for f in d.get("flags", [])
    ]
    flags_html = "\n".join(flag_cards) or '<p class="empty">目前沒有任何項目被標記。</p>'

    out = DOCS / "verify"
    out.mkdir(parents=True, exist_ok=True)
    page = VERIFY_PAGE.format(
        checked=_checked(overall), pass_rate=pass_rate,
        flagged=overall["flagged"], days=len(history),
        body_rows="\n    ".join(body_rows),
        source_rows="\n    ".join(source_rows),
        day_rows="\n    ".join(day_rows),
        flags=flags_html, retention=retention,
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    return str(out / "index.html")


def render(items: list, broken_sources: list | None = None, announcement: str = "") -> str:
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
            # 沒有 body_source 的(理論上不該發生)當成最保守的「只有標題」
            body_source=it.get("body_source", "title"),
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

    announcement_html = ""
    if announcement:
        escaped = html.escape(announcement).replace("\n", "<br>")
        announcement_html = f'<div class="announcement">📣 {escaped}</div>'

    DOCS.mkdir(exist_ok=True)
    page = PAGE.format(
        date=now, count=len(items), cards=cards, hits_key=hits_key,
        filter_checkboxes=filter_checkboxes, broken_notice=broken_notice,
        announcement_html=announcement_html,
    )
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    return str(DOCS / "index.html")
