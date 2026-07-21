# 每日 AI 快報 Pipeline

多來源擷取 → 清洗去重 → LLM 摘要 → 自動排程輸出的每日 AI 新聞 pipeline。
每天由 GitHub Actions 定時執行,產物是一頁 GitHub Pages 靜態網頁,自動更新。

> 這是一條 **workflow(工作流)**,不是 agent —— 控制流由程式碼寫死,
> LLM 只在「摘要」節點被呼叫。開發者是編排者,LLM 是零件。

## 架構

    Hacker News API ┐
                    ├─→ 去重 ─→ 排序取 TopN ─→ 逐篇 LLM 摘要 ─→ 渲染靜態頁 ─→ commit
    arXiv API       ┘   (Jaccard/            (Gemini,         (docs/         (GitHub
                        可切 BGE-M3)          faithfulness)    index.html)    Actions)

## 設計重點

- **來源可靠性**:只用官方 API(HN、arXiv),無爬蟲脆弱性;HN upvote 自帶相關性排序。
- **去重可插拔**:預設輕量詞彙相似度(CI 快);dedup.py 打開 USE_EMBEDDINGS 即改用
  BGE-M3 語意去重。權衡:語意去重更準,但 CI 有模型啟動成本。
- **摘要 faithfulness**:逐篇餵、只依原文、禁止臆測;來源 URL 在程式碼裡綁死、
  從不進入 LLM,從根本杜絕張冠李戴。
- **零維運成本**:GitHub Actions 免費排程,摘要用便宜小模型,一個月成本 < NT$10。

## 使用

    pip install -r requirements.txt
    python main.py --mock       # 不呼叫 LLM,測整條流程
    export GEMINI_API_KEY=...    # 正式跑
    python main.py

部署:repo Settings → Pages → Source 選 docs/;把 GEMINI_API_KEY 加到 repo Secrets;
Actions 每天自動跑並更新頁面。
