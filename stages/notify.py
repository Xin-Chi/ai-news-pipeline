"""每日更新完成後寄一封通知信。

憑證走環境變數(本機從 .env、CI 從 GitHub Secrets),沒設定就直接跳過不寄。
寄信失敗也只印警告、不丟例外——通知信掛掉不該讓整條 pipeline 失敗,
網頁本身已經產生好了。
"""
import os
import smtplib
from collections import Counter
from email.mime.text import MIMEText
from email.header import Header

SITE_URL = "https://xin-chi.github.io/ai-news-pipeline/"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def _redact(text: str, *secrets: str | None) -> str:
    """把憑證/信箱從要印出去的字串裡抹掉(CI log 是公開的)。"""
    for s in secrets:
        if s:
            text = text.replace(s, "[已遮蔽]")
    return text


def _build_body(
    items: list, date_str: str, broken_sources: list | None,
    recommendation: dict | None, verification: dict | None = None,
) -> str:
    counts = Counter(it["source"] for it in items)
    lines = [
        "今天的 AI 快報已經更新了。",
        "",
        f"更新時間:{date_str}",
        f"共 {len(items)} 則",
        "",
        "各來源篇數:",
    ]
    lines += [f"  · {source} {count} 篇" for source, count in counts.most_common()]
    if recommendation:
        # 標題與連結取自我們自己的資料,不用模型回傳的文字,避免它重打時改到字。
        item = recommendation["item"]
        lines += [
            "",
            "今天最推薦的一篇:",
            f"  {item['title']}",
            f"  （{item['source']}）",
            f"  {recommendation['reason']}",
            f"  {item['url']}",
        ]
    if verification:
        # 正常的日子只佔一行;有被標記才列明細,不然每天都會有一大塊看膩的文字。
        lines += ["", "摘要 grounding 檢查:"]
        lines.append(
            f"  通過 {verification['passed']}、標記 {verification['flagged']}、"
            f"無從檢查 {verification['unverifiable']}"
            + (f"、出錯 {verification['error']}" if verification.get("error") else "")
        )
        for f in verification.get("flags", []):
            lines += [
                "",
                f"  ⚠️ [{f['source']}] {f['title']}",
                f"     摘要:{f['summary']}",
                f"     {'；'.join(f['problems'])}",
            ]
        lines += ["", f"  檢查紀錄:{SITE_URL}verify/"]
    if broken_sources:
        lines += ["", f"⚠️ 今天抓取異常的來源:{'、'.join(broken_sources)}"]
    lines += ["", f"看完整內容:{SITE_URL}"]
    return "\n".join(lines)


def send_daily_summary(
    items: list,
    date_str: str,
    broken_sources: list | None = None,
    recommendation: dict | None = None,
    verification: dict | None = None,
    dry_run: bool = False,
) -> None:
    sender = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_APP_PASSWORD")
    recipient = os.environ.get("EMAIL_TO") or sender
    if not sender or not password:
        print("[notify] 沒有 email 憑證,跳過寄信")
        return

    body = _build_body(items, date_str, broken_sources, recommendation, verification)
    if dry_run:
        # --mock 時不該把假摘要寄進真的信箱。照樣組信、只是不送出,
        # 這樣信件內容的排版問題在 mock 就看得到。
        print("[notify] --mock:只預覽不寄出\n" + "\n".join("    " + l for l in body.splitlines()))
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(f"每日 AI 快報 · {date_str} · 共 {len(items)} 則", "utf-8")
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.login(sender, password)
            server.send_message(msg)
        # 不印收件者/寄件者信箱:這個 repo 是公開的,CI log 任何人都看得到,
        # 印出去等於把信箱公開給爬蟲收集。
        print("[notify] 通知信已寄出")
    except Exception as e:
        # 例外訊息理論上不會帶到憑證,但這裡會進公開 log,所以再保險過濾一次。
        print(f"[warn] 通知信寄送失敗: {_redact(str(e), password, sender, recipient)}")
