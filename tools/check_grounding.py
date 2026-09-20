"""事後回頭查某一天的 grounding —— 手動跑。

平常的檢查已經由 stages/verify.py 在 pipeline 裡每天自動做掉了(結果在
docs/verify/)。這支腳本是給「想回頭查某一份已經產生的頁面」用的,例如
翻線上的舊版本、或是手上只有一個 index.html 檔的時候。

跟 pipeline 內建檢查的關鍵差別:**這支會重新抓一次原文**,因為從 HTML
裡拿不到當初餵給模型的那份文字。所以比對的對象是「現在的文章」而不是
「模型當初看到的文章」。Hacker News 尤其失真——pipeline 只餵標題,這裡卻
會拿整篇文章去比,通過了也不代表什麼。要看準確的結果請看 docs/verify/。

檢查邏輯(literal_check / judge)直接沿用 stages/verify.py,不另外寫一份。

用法:
  python tools/check_grounding.py              # 字面比對,全部卡片
  python tools/check_grounding.py --judge      # 加上 LLM 判定
  python tools/check_grounding.py --limit 5    # 只檢查前 5 則(省配額)
  python tools/check_grounding.py --file docs/index.html
"""
import argparse
import html
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from main import _load_dotenv  # noqa: E402
from stages import fulltext, summarize  # noqa: E402
from stages.verify import judge, literal_check  # noqa: E402

# 對應 render.py 的 CARD 樣板。色點那個 span 夾在 tag 與 h2 之間,
# 中間的 .*? 會直接跨過去,所以不用特別處理。
CARD_RE = re.compile(
    r'<article class="item [^"]*">.*?'
    r'<span class="tag">(?P<source>.*?)</span>.*?'
    r'<h2><a href="(?P<url>[^"]*)".*?>(?P<title>.*?)</a></h2>\s*'
    r'<p>(?P<summary>.*?)</p>',
    re.DOTALL,
)


def parse_cards(path: Path) -> list[dict]:
    page = path.read_text(encoding="utf-8")
    return [
        {k: html.unescape(v) for k, v in m.groupdict().items()}
        for m in CARD_RE.finditer(page)
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "docs" / "index.html"))
    ap.add_argument("--judge", action="store_true", help="加上 LLM faithfulness 判定(會用到 API 配額)")
    ap.add_argument("--limit", type=int, default=0, help="只檢查前 N 則")
    args = ap.parse_args()

    if args.judge:
        _load_dotenv()

    cards = parse_cards(Path(args.file))
    if args.limit:
        cards = cards[: args.limit]
    if not cards:
        print("沒有解析到任何卡片,確認一下檔案路徑與 render.py 的 CARD 樣板有沒有改過")
        return 1

    print(f"檢查 {len(cards)} 則 · 模式:{'字面比對 + LLM 判定' if args.judge else '字面比對'}\n")
    flagged = unfetchable = 0

    for i, c in enumerate(cards, 1):
        print(f"{i}. [{c['source']}] {c['title'][:50]}")
        print(f"   摘要:{c['summary']}")

        if c["summary"] == c["title"]:
            print("   ⚠️  摘要與標題完全相同 —— 這是 summarize 失敗後的 fallback,不是摘要")
            flagged += 1
            print()
            continue

        try:
            source = fulltext._extract(c["url"])
        except Exception as e:
            source = ""
            print(f"   原文抓取出錯:{e}")
        if not source:
            # HN 指向任意網站、付費牆、網站擋爬蟲都會落在這裡。注意:pipeline 當初
            # 可能是用 RSS 摘要或標題產生這則摘要的,這裡抓不到不代表當初沒根據。
            print("   ⏭️  抓不到原文,無法檢查")
            unfetchable += 1
            print()
            continue

        missing = literal_check(c["summary"], source)
        if missing:
            print(f"   ⚠️  原文找不到:{missing}")
            flagged += 1
        else:
            print("   ✅ 字面比對通過")

        if args.judge:
            time.sleep(summarize.RATE_LIMIT_DELAY)  # 守 15 RPM
            try:
                v = judge(c["summary"], source)
            except Exception as e:
                print(f"   LLM 判定失敗:{e}")
            else:
                if v.get("verdict") == "unsupported":
                    print(f"   ⚠️  LLM 判定沒根據:{v.get('problem')}")
                    flagged += 1
                else:
                    print("   ✅ LLM 判定有根據")
        print()

    print(f"—— 完成:{len(cards)} 則,標記 {flagged} 則,{unfetchable} 則抓不到原文無法檢查")
    if not args.judge:
        print("提醒:字面比對只驗得到數字與英數詞,中文語意層級的問題要加 --judge 才看得到")
    return 0


if __name__ == "__main__":
    sys.exit(main())
