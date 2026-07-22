# 每日 AI 快報 Pipeline

多來源擷取 → 24 小時內限制 → 去重 → LLM 摘要 → 自動排程輸出的每日 AI 新聞 pipeline。
每天由 GitHub Actions 定時執行,產物是一頁 GitHub Pages 靜態網頁,自動更新。


線上網址:https://xin-chi.github.io/ai-news-pipeline/

## 來源

按優先順序(也是選稿時的搶名額順序、頁面上的顯示順序):

| 順序 | 來源 | 備註 |
|---|---|---|
| 1 | OpenAI Blog | 官方 RSS |
| 2 | Anthropic Blog | 非官方鏡像 RSS(官方沒提供 RSS) |
| 3 | Google DeepMind | 官方 RSS |
| 4 | iThome | AI 分類 RSS,另加關鍵字過濾雙重保險 |
| 5 | TechNews 科技新報 | AI 分類 RSS,另加關鍵字過濾雙重保險 |
| 6 | INSIDE | 綜合 RSS(無 AI 分類),用關鍵字過濾 |
| 7 | Hacker News | 官方 API,upvote 排序 |
| 8 | Hugging Face Blog | 官方 RSS |
| 9 | arXiv | 官方 API(cs.AI / cs.CL / cs.LG) |

每個來源當天有發文的話保底 1 篇,剩下名額依上表順序去搶;
只收過去 24 小時內發布的內容,不足 20 篇是正常情況,不會硬湊舊文章。

## 架構

    9 個來源(RSS/API) ─→ 24h 過濾 ─→ 去重 ─→ 保底+優先順序選稿 ─→ 逐篇 LLM 摘要 ─→ 渲染靜態頁 ─→ commit
                        (published)   (Jaccard)   (main.py)         (Gemini)          (docs/         (GitHub
                                                                                        index.html)    Actions)

## 設計重點

- **來源容錯**:每個 fetcher 統一回傳 `(items, error)`,單一來源掛掉不會讓整條
  pipeline 失敗,只會在頁面顯示小紅字提示——區分「今天沒發文」(正常)跟
  「抓取本身出錯」(異常)這兩種情況。
- **去重**:輕量詞彙相似度(Jaccard),標題切詞後比重疊比例。
- **降低摘要幻覺風險(靠設計,非事後驗證)**:逐篇餵給 LLM(不會把多篇文章
  一次塞給它混淆);prompt 明文禁止臆測;來源 URL 在程式碼裡綁死、從不進入
  LLM,杜絕張冠李戴。這三個都是預防性的工程作法,沒有額外的步驟去事後驗證
  摘要是否忠於原文。
- **Gemini 免費額度限流**:免費方案 15 RPM 上限,`summarize.py` 每次呼叫間隔
  4.5 秒,避免同一批次呼叫互相排擠導致 429。
- **前端篩選**:純 JavaScript,勾選來源即時篩選卡片顯示(不重新抓資料);
  當天沒發文的來源 checkbox 會自動鎖定,滑鼠移過去有提示文字。
- **零成本**:GitHub Actions(public repo 免費排程)+ GitHub Pages(免費)+ Gemini
  API 免費額度,目前完全 $0。每天呼叫量維持在免費額度內。

## 使用

    pip install -r requirements.txt
    python main.py --mock       # 不呼叫 LLM,測整條流程(仍會真的抓 9 個來源)
    python main.py

排程:
Actions 排程目標台灣時間 6:30 觸發(`.github/workflows/daily.yml`),排早一點是
因為 GitHub 的 schedule 觸發常常會晚 1~2 小時。
