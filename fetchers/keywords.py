"""跨來源共用的 AI 相關性關鍵字,給沒有 AI 專屬分類的來源(綜合新聞站)過濾雜訊用。"""
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral", "qwen",
    "openai", "anthropic", "deepmind", "hugging face", "transformer",
    "diffusion", "rag", "fine-tun", "embedding", "neural", "machine learning",
    "deep learning", "agent", "inference", "pytorch", "tensorflow",
    "人工智慧", "人工智能", "大型語言模型", "大語言模型", "機器學習", "深度學習", "生成式",
]


def looks_ai(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in AI_KEYWORDS)
