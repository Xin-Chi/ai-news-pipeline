"""跨來源共用的 AI 相關性關鍵字,給沒有 AI 專屬分類的來源(綜合新聞站)過濾雜訊用。"""
import re

# 英文關鍵字用「完整單字」比對(不是子字串),避免像 "ai" 這種短字被 "Taiwan"、
# "email"、"maintain" 這類無關單字裡的 "ai" 誤判命中。
AI_KEYWORDS_EN = [
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral", "qwen",
    "openai", "anthropic", "deepmind", "hugging face", "transformer",
    "diffusion", "rag", "embedding", "neural", "machine learning",
    "deep learning", "agent", "inference", "pytorch", "tensorflow",
]
# 中文沒有空白分詞,子字串比對本來就不太會誤判(不會有詞彙意外包含這幾個詞),維持原樣。
AI_KEYWORDS_ZH = [
    "人工智慧", "人工智能", "大型語言模型", "大語言模型", "機器學習", "深度學習", "生成式",
]

_PATTERNS = [re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE) for k in AI_KEYWORDS_EN]
_PATTERNS.append(re.compile(r"\bfine-tun", re.IGNORECASE))  # 涵蓋 fine-tune/-tuning/-tuned


def looks_ai(text: str) -> bool:
    if any(p.search(text) for p in _PATTERNS):
        return True
    return any(k in text for k in AI_KEYWORDS_ZH)
