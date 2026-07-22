"""LLM 摘要層。faithfulness 原則沿用 RAG 經驗:
1. 逐篇餵、逐篇摘,不一次餵多篇讓來源錯亂。
2. 只依提供文字,禁止捏造。
3. 來源 URL 在程式碼綁死(見 main.py),不讓模型碰。
預設 Gemini Flash-Lite;換模型只改 _call_llm。--mock 不呼叫 LLM。"""
import os
import time
import requests

MODEL = "gemini-3.1-flash-lite"
RATE_LIMIT_DELAY = 4.5  # 免費方案 15 RPM 上限(60/15=4 秒),抓 4.5 秒留安全margin
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
SYSTEM = ("你是 AI 新聞摘要助理。只根據使用者提供的標題與內文,用繁體中文寫一句話"
          "(最多 40 字)的重點摘要。嚴禁補充提供內容以外的資訊或臆測。只回傳純文字。")

def _call_llm(title: str, body: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": f"標題:{title}\n\n內文:{body[:1500]}"}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 120},
    }
    # 金鑰走 header,不走 URL query string,避免出現在 request 例外訊息、
    # proxy log 或終端機輸出裡(requests 的 HTTPError 預設會印出完整 URL)。
    r = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": key},
        json=payload,
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def summarize(item: dict, mock: bool = False) -> dict:
    body = item.get("abstract", "") or item["title"]
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
    return result
