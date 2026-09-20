"""摘要 grounding 檢查 —— 只觀測,不介入。

接在 summarize 之後跑,用 pipeline 記憶體裡「模型真正看到的那份文字」去驗,
刻意不重抓原文:重抓驗到的是另一個版本的文章,而且 Hacker News 那種只餵標題
產生的摘要,會被拿去跟整篇文章比對而假性通過——那等於沒驗到 pipeline 的行為。

三關:
1. 摘要 == 標題:那是 summarize 失敗後的 fallback,不是摘要(嚴格說這關在抓
   pipeline 失敗,不是抓幻覺,但同樣是讀者會看到的品質問題)。
2. 字面比對(免費):摘要裡出現的數字與英數詞,原文必須找得到。
3. LLM judge(每則一次呼叫):問模型這句摘要有沒有原文沒說的東西。

結果只寫進 docs/verify/,不影響首頁、不阻斷發布。刻意不在卡片上標記被 flag 的
項目——那會從「觀測」變成「介入」。先累積幾週的實際 flag 率,有數據再決定。
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

from stages import summarize

DOCS = Path(__file__).resolve().parent.parent / "docs"
HISTORY_PATH = DOCS / "verify" / "history.json"
# 每天一筆,實測約 1.8 KB(通過的只記次數,只有被標記的才存明細),一年 0.62 MB。
# 容量在這個專案裡不是限制條件——docs/index.html 每天 commit 13.7 KB,比這還大。
# 設上限純粹是不讓頁面無止境變長,被砍掉的紀錄在 git 歷史裡還找得回來。
RETENTION_DAYS = 365

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
# 3 個字元以上的英數詞才算,避免 AI、of 這種長度抓出一堆雜訊
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9.\-]{2,}")

JUDGE_SYSTEM = (
    "你是事實查核員。使用者會給你一篇文章的原文,以及一句根據它寫成的中文摘要。\n"
    "請判斷這句摘要是否完全有原文支持。\n"
    "unsupported 的情況包含:摘要提到原文沒有的事實、數字或人事物;"
    "把原文的說法誇大或加強(例如原文說「可能」摘要寫成「將會」);"
    "或是摘要描述的重點根本不是這篇文章在講的事。\n"
    "只是用不同措辭轉述、或只挑原文其中一個重點來寫,都算 supported。\n"
    "verdict 只能是 supported 或 unsupported。"
    "unsupported 時,problem 用繁體中文一句話指出是哪裡沒根據;supported 時 problem 留空字串。"
)
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["supported", "unsupported"]},
        "problem": {"type": "string"},
    },
    "required": ["verdict", "problem"],
}


def literal_check(summary: str, source: str) -> list[str]:
    """回傳摘要裡出現、但原文找不到的字串。

    限制(不要把空清單當成「沒問題」):中文摘要對英文原文,中文詞彙無從比對,
    只有數字與英數詞驗得到;而且摘要限 40 字,本來就很少寫到數字,涵蓋率天生就低。
    換算過的數字(原文 a billion → 摘要「10 億」)也會誤報。
    真正能抓到語意層級問題的是 judge()。
    """
    lowered = source.lower()
    missing = [n for n in NUM_RE.findall(summary) if n not in source]
    missing += [w for w in WORD_RE.findall(summary) if w.lower() not in lowered]
    return missing


def judge(summary: str, source: str) -> dict:
    """LLM faithfulness 判定。會真的打一次 API,呼叫端要自己先做 RPM 間隔。"""
    raw = summarize._first_text(summarize._post({
        "system_instruction": {"parts": [{"text": JUDGE_SYSTEM}]},
        "contents": [{"parts": [{"text": f"原文:\n{source[:summarize.BODY_LIMIT]}\n\n摘要:{summary}"}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 200,
            "responseMimeType": "application/json",
            "responseSchema": JUDGE_SCHEMA,
        },
    }))
    return json.loads(raw)


def check_item(item: dict) -> dict:
    """驗一則,回傳一筆紀錄。status: passed / flagged / unverifiable / error。"""
    rec = {
        "source": item["source"],
        "title": item["title"],
        "url": item.get("url", ""),
        "summary": item.get("summary", ""),
        "body_source": item.get("body_source", "title"),
        "status": "passed",
        "problems": [],
    }

    if rec["summary"] == rec["title"]:
        rec["status"] = "flagged"
        rec["problems"].append("摘要與標題完全相同 —— summarize 當時失敗,這是 fallback 不是摘要")
        return rec

    source_text = item.get("full_text") or item.get("abstract") or ""
    if not source_text:
        # 只有標題可用(HN 全部落在這裡)。沒有原文就沒有「根據」可驗,
        # 誠實記成無從檢查,不要假裝通過。
        rec["status"] = "unverifiable"
        rec["problems"].append("只有標題可用,無從比對")
        return rec

    missing = literal_check(rec["summary"], source_text)
    if missing:
        rec["status"] = "flagged"
        rec["problems"].append(f"原文找不到:{'、'.join(missing)}")

    # 接在逐篇摘要/推薦之後,一樣要守 15 RPM
    time.sleep(summarize.RATE_LIMIT_DELAY)
    v = judge(rec["summary"], source_text)
    if v.get("verdict") == "unsupported":
        rec["status"] = "flagged"
        rec["problems"].append(f"LLM 判定沒根據:{v.get('problem', '').strip()}")
    return rec


def _tally(records: list, key: str) -> dict:
    """依 key 分組,數各個 status 各幾次。"""
    out = {}
    for r in records:
        d = out.setdefault(r[key], dict.fromkeys(
            ("total", "passed", "flagged", "unverifiable", "error"), 0))
        d["total"] += 1
        d[r["status"]] += 1
    return out


def run(items: list, date_str: str) -> dict:
    """驗整天的項目,回傳一筆當日紀錄。單則出錯不影響其他則。"""
    records = []
    for it in items:
        try:
            records.append(check_item(it))
        except Exception as e:
            print(f"[warn] grounding 檢查出錯({it['source']}): {e}")
            records.append({
                "source": it["source"], "title": it["title"], "url": it.get("url", ""),
                "summary": it.get("summary", ""), "body_source": it.get("body_source", "title"),
                "status": "error", "problems": [str(e)[:200]],
            })

    counts = {k: sum(1 for r in records if r["status"] == k)
              for k in ("passed", "flagged", "unverifiable", "error")}
    print(f"[verify] {len(records)} 則:通過 {counts['passed']}、標記 {counts['flagged']}、"
          f"無從檢查 {counts['unverifiable']}、出錯 {counts['error']}")
    for r in records:
        if r["status"] == "flagged":
            print(f"[verify] ⚠️ [{r['source']}] {r['title'][:40]} — {'; '.join(r['problems'])}")

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": date_str,
        "total": len(records),
        **counts,
        # 分組統計存的是「各狀態的次數」而不只是總數,這樣頁面才算得出各自的通過率。
        # 最想看的一組是 by_body_source:全文摘要的通過率有沒有真的比 RSS 摘要高。
        # 多存這兩組讓一天的紀錄從 215 漲到約 1.8 KB(實測),一年 0.62 MB。
        # 對照:docs/index.html 每天 commit 13.7 KB,所以這仍然是小頭。
        "by_source": _tally(records, "source"),
        "by_body_source": _tally(records, "body_source"),
        # 只留被標記/出錯的明細,通過的算次數就好——這頁是拿來看問題的,
        # 全部留著會讓 JSON 和頁面都膨脹好幾倍。
        "flags": [r for r in records if r["status"] in ("flagged", "error")],
    }


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 讀不到 grounding 歷史紀錄,當成空的重新開始: {e}")
        return []


def append_history(day: dict) -> list[dict]:
    """把當日紀錄併進歷史檔。同一天重跑會覆蓋,不會留下兩筆。"""
    history = [d for d in load_history() if d.get("date") != day["date"]]
    history.append(day)
    history.sort(key=lambda d: d.get("date", ""))
    history = history[-RETENTION_DAYS:]
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return history
