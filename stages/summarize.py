"""LLM 層。faithfulness 原則沿用 RAG 經驗:
1. 逐篇餵、逐篇摘,不一次餵多篇讓來源錯亂。
2. 只依提供文字,禁止捏造。
3. 來源 URL 在程式碼綁死(見 main.py),不讓模型碰。
除了逐篇摘要,另外有 recommend() 讓模型從當天清單裡挑一則寫推薦語
(給通知信用),同樣只餵既有標題+摘要,且標題/連結一律取程式碼這邊的值。
預設 Gemini Flash-Lite;換模型只改 MODEL。--mock 不呼叫 LLM。"""
import json
import os
import time
import requests

# 主模型釘死版本,確保輸出風格穩定可預期;備援是不同世代的模型,
# 實測過兩者的速率額度是分開計算的(對主模型打到 429 的同一分鐘內,備援仍可正常回應),
# 所以主模型遇到 429(額度)、503(Google 容量不足)或被下架時,備援真的頂得上。
PRIMARY_MODEL = "gemini-3.1-flash-lite"
FALLBACK_MODEL = "gemini-3.5-flash-lite"
RATE_LIMIT_DELAY = 4.5  # 免費方案 15 RPM 上限(60/15=4 秒),抓 4.5 秒留安全margin
BODY_LIMIT = 5000  # 餵給模型的內文上限字數;新聞的重點幾乎都在前段,再長效益遞減

_fallback_uses = 0  # 這次執行用到備援模型幾次,跑完會印出來
SYSTEM = ("你是 AI 新聞摘要助理。只根據使用者提供的標題與內文,用繁體中文寫一句話"
          "(最多 40 字)的重點摘要。嚴禁補充提供內容以外的資訊或臆測。只回傳純文字。")

RECOMMEND_SYSTEM = (
    "你是每日 AI 快報的編輯。使用者會給你今天已收錄的文章清單(每則含編號、來源、標題、摘要),"
    "請挑出一則最值得優先閱讀的,並寫一句推薦語。\n"
    "\n"
    "挑選優先順序(由高到低):\n"
    "A. 重大消息優先:新模型或新產品發布、重要研究突破、產業重大事件,"
    "勝過一般性的評論、心得分享或週邊小道消息。\n"
    "B. 主題加權:跟 OpenAI、Anthropic、Google Gemini/DeepMind 相關的消息可以稍微優先"
    "(不論它來自哪個來源)。\n"
    "C. 條件相當時,選讀者看了最有收穫的那一則。\n"
    "\n"
    "嚴格規則(優先於上面的挑選偏好,不可為了讓推薦更吸引人而違反):\n"
    "1. 挑中的那一則必須真的跟人工智慧相關。清單是自動抓取的,偶爾會混進與 AI 無關的文章"
    "(例如只是標題剛好出現 neural、agent 這類字的生物學或商業新聞),這種一律不可以選。\n"
    "2. 只能依據清單裡的標題與摘要來判斷與描述,嚴禁補充清單以外的任何資訊、背景知識或臆測。\n"
    "3. 推薦語必須忠實轉述該則摘要已經寫到的內容,不得誇大,"
    "不得加入清單沒寫的評價或預測(例如「將顛覆產業」這種清單沒提到的話)。\n"
    "4. 不確定的細節就不要寫進去,寧可簡短也不要腦補。\n"
    "5. 推薦語用繁體中文,40 字以內,語氣可以口語一點。\n"
    "6. index 必須是清單中真實存在的編號。\n"
    "7. 如果清單裡沒有任何一則真的跟 AI 相關,就回傳 index = -1、reason 留空字串,"
    "不要勉強挑一則湊數。"
)
RECOMMEND_SCHEMA = {
    "type": "object",
    "properties": {"index": {"type": "integer"}, "reason": {"type": "string"}},
    "required": ["index", "reason"],
}


def _post_to(model: str, payload: dict, headers: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:200]}")
    return r.json()


def _post(payload: dict) -> dict:
    """先打主模型,失敗就改打備援模型。

    注意:安全過濾擋下的情況(PROHIBITED_CONTENT)會回 HTTP 200、只是沒有
    candidates 欄位,不會走到這裡的備援邏輯——那是正確的,因為換個模型
    一樣會被同一套安全政策擋下,重打只是浪費配額。
    """
    global _fallback_uses
    # 金鑰走 header,不走 URL query string,避免出現在 request 例外訊息、
    # proxy log 或終端機輸出裡(requests 的 HTTPError 預設會印出完整 URL)。
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    try:
        return _post_to(PRIMARY_MODEL, payload, headers)
    except Exception as primary_error:
        print(f"[warn] 主模型 {PRIMARY_MODEL} 失敗,改用備援 {FALLBACK_MODEL}: {primary_error}")
        try:
            data = _post_to(FALLBACK_MODEL, payload, headers)
            _fallback_uses += 1
            return data
        except Exception as fallback_error:
            raise RuntimeError(
                f"主模型與備援都失敗(主: {primary_error} | 備援: {fallback_error})"
            ) from None


def _first_text(data: dict) -> str:
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_llm(title: str, body: str) -> str:
    return _first_text(_post({
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": f"標題:{title}\n\n內文:{body[:BODY_LIMIT]}"}]}],
        # temperature 0:摘要不需要創意,要的是「同樣的輸入給同樣的輸出」。
        # 取樣隨機性只會增加挑到低機率(也就是比較沒根據)那個字的機會。
        "generationConfig": {"temperature": 0, "maxOutputTokens": 120},
    }))


def recommend(items: list) -> dict | None:
    """從當天清單挑一則推薦,回傳 {'item': 那一則, 'reason': 推薦語}。

    防幻覺:只餵既有標題+摘要;模型只回「編號」而不是重打標題,標題與連結
    一律用我們自己的資料;編號不在範圍內或推薦語是空的就當失敗。
    任何失敗都回 None,信件就不放推薦區塊,不冒險顯示錯的東西。
    """
    if not items:
        return None
    listing = "\n".join(
        f"{i}. [{it['source']}] {it['title']}\n   摘要:{it.get('summary', '')}"
        for i, it in enumerate(items)
    )
    try:
        time.sleep(RATE_LIMIT_DELAY)  # 接在逐篇摘要後面,一樣要守 15 RPM
        raw = _first_text(_post({
            "system_instruction": {"parts": [{"text": RECOMMEND_SYSTEM}]},
            "contents": [{"parts": [{"text": listing}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 200,
                "responseMimeType": "application/json",
                "responseSchema": RECOMMEND_SCHEMA,
            },
        }))
        data = json.loads(raw)
        idx, reason = data.get("index"), str(data.get("reason", "")).strip()
        if idx == -1:  # 模型判定今天沒有真正跟 AI 相關的,不硬湊
            print("[notify] 今天沒有適合推薦的 AI 文章,信件略過推薦區塊")
            return None
        if not isinstance(idx, int) or not (0 <= idx < len(items)) or not reason:
            raise ValueError(f"回傳不合法(index={idx!r}, 推薦語長度={len(reason)})")
        return {"item": items[idx], "reason": reason}
    except Exception as e:
        print(f"[warn] 推薦選稿失敗,信件略過推薦區塊: {e}")
        return None

def summarize(item: dict, mock: bool = False) -> dict:
    # 有抓到全文就優先用;沒有(抓失敗、來源被跳過)就沿用 feed 給的摘要,
    # 再沒有才用標題(HN 沒有 abstract 欄位,一律落在這裡)。
    # body_source 記下這篇實際上是拿什麼餵給模型的,render 會據此標色點。
    if item.get("full_text"):
        item["body_source"], body = "full", item["full_text"]
    elif item.get("abstract"):
        item["body_source"], body = "rss", item["abstract"]
    else:
        item["body_source"], body = "title", item["title"]
    if mock:
        item["summary"] = f"(mock)關於「{item['title'][:20]}」的摘要"
    else:
        try:
            item["summary"] = _call_llm(item["title"], body)
        except Exception as e:
            item["summary"] = item["title"]
            print(f"[warn] summarize failed for {item['id']}: {e}")
    return item

def summarize_all(items: list, mock: bool = False) -> list:
    result = []
    for i, it in enumerate(items):
        if not mock and i > 0:
            time.sleep(RATE_LIMIT_DELAY)
        result.append(summarize(it, mock=mock))
    if _fallback_uses:
        print(f"[summarize] 本次有 {_fallback_uses} 次改用備援模型 {FALLBACK_MODEL}")
    return result
