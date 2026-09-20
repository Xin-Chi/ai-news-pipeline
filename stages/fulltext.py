"""抓原文全文,補足 RSS 摘要太短的問題。

為什麼需要:各來源在 feed 裡給的摘要長度差很多——Hugging Face 是 0 字
(完全沒有摘要欄位),TechNews/INSIDE 只有 60~80 字,這種長度餵給 LLM,
產出的「摘要」其實只是把原句換句話說,沒有真正在濃縮資訊。

設計原則:
1. 只對「有需要」的抓:已經有夠長內文的(Anthropic 7000+ 字)直接跳過,不浪費請求。
2. Hacker News 一律跳過:它的連結指向任意網站,每天不同網域,失敗率高,
   還常碰到付費牆(Economist、Nikkei 等)。
3. 抓失敗就沿用原本的 RSS 摘要——最糟也不會比現在差。
4. 抓到的東西要先清乾淨(_strip_paywall)再過長度門檻(_reject_reason)才採用。
   原本是「只要非空就採用」,但 full_text 在 summarize 裡優先於 abstract,
   所以一段 150 字的付費牆前導會蓋掉更完整的 RSS 摘要,模型就得拿殘缺的脈絡
   去寫「這篇文章的重點」——這是 prompt 擋不住的。
"""
import trafilatura

SKIP_SOURCES = {"Hacker News"}
# RSS 摘要已經有這麼長就不用抓了(Anthropic 7000+ 字會落在這裡)
ENOUGH_CHARS = 500
TIMEOUT = 20

# 抓回來的正文至少要這麼長才算數。比這短的多半是付費牆前導、同意 cookie 的頁面,
# 或 trafilatura 選錯了節點,拿去當「全文」比原本的 RSS 摘要更糟。
MIN_CHARS = 300
# 付費牆的提示語。碰到就從那裡切斷、留下前面的正文,不是整段丟掉——
# metered paywall 給的前半段是文章真正的開頭,新聞是倒金字塔寫法,重點就在前段,
# 對「40 字摘要」這個用途已經夠用。丟掉它改用更短的 RSS 摘要反而是降級。
# 要丟的只有這些樣板話本身,它們不是內文,留著只會變成模型的雜訊素材。
#
# 刻意只收「整句的樣板話」,不收 subscribe / subscription / 訂閱 這種單字:
# AI 新聞本身就常在報導訂閱制(實測一則 1016 字的 ChatGPT 訂閱方案新聞會被誤切),
# 單字判準的誤傷率太高。
PAYWALL_MARKERS = (
    "sign in to read", "already a subscriber", "create an account to",
    "for full access", "register to continue", "subscribe to continue",
    "subscribe to read", "to continue reading",
    "登入後繼續", "付費會員", "訂閱以繼續", "閱讀完整內容",
)


def _extract(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return ""
    # favor_precision:寧可少抓一點邊緣段落,也不要把導覽、推薦閱讀、廣告文案
    # 混進正文——那些東西餵給模型等於給它無關的素材去發揮。
    text = trafilatura.extract(
        downloaded, include_comments=False, include_tables=False, favor_precision=True
    ) or ""
    return " ".join(text.split())


def _strip_paywall(text: str) -> tuple[str, str]:
    """從最早出現的付費牆提示語切斷,回傳 (切過的正文, 命中的字樣)。
    沒命中就原樣回傳。切的是最早那個,因為提示語後面通常還跟著一串
    方案價格、登入表單文字之類的東西,一起留著只會變雜訊。"""
    lowered = text.lower()
    hits = [(lowered.find(m), m) for m in PAYWALL_MARKERS if m in lowered]
    if not hits:
        return text, ""
    pos, marker = min(hits)
    return text[:pos].strip(), marker


def _reject_reason(text: str, abstract: str) -> str:
    """回傳不採用這段正文的理由;空字串代表通過,可以採用。
    這裡只剩長度判斷——付費牆的處理是切斷(見 _strip_paywall),不是拒收。"""
    if len(text) < MIN_CHARS:
        return f"太短({len(text)} 字)"
    if len(text) < len(abstract):
        # RSS 摘要本來就比抓到的正文完整,換過去是降級
        return f"比 RSS 摘要還短({len(text)} < {len(abstract)} 字)"
    return ""


def enrich(items: list) -> list:
    """對需要的項目補上 full_text 欄位。不改動 abstract,讓後續要比對時
    還看得到原本 feed 給的內容。"""
    fetched = skipped = failed = rejected = trimmed = 0
    for it in items:
        if it["source"] in SKIP_SOURCES or len(it.get("abstract", "")) >= ENOUGH_CHARS:
            skipped += 1
            continue
        url = it.get("url")
        if not url:
            skipped += 1
            continue
        try:
            text = _extract(url)
        except Exception as e:
            text = ""
            print(f"[warn] 全文抓取出錯({it['source']}): {e}")
        if not text:
            failed += 1
            continue
        text, marker = _strip_paywall(text)
        if marker:
            print(f"[fulltext] 切掉付費牆提示({it['source']}): 命中「{marker}」,保留前 {len(text)} 字")
        reason = _reject_reason(text, it.get("abstract", ""))
        if reason:
            rejected += 1
            print(f"[fulltext] 不採用({it['source']}): {reason}")
            continue
        it["full_text"] = text
        fetched += 1
        trimmed += bool(marker)  # 只算真的有採用的,才對得上「成功 N 篇」
    print(f"[fulltext] 成功 {fetched} 篇(其中 {trimmed} 篇切掉付費牆提示), 跳過 {skipped} 篇, "
          f"失敗 {failed} 篇, 長度不合格 {rejected} 篇(後兩者沿用 RSS 摘要)")
    return items
