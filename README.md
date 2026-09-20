# 每日 AI 快報 Pipeline

多來源擷取 → 24 小時內限制 → 去重 → 抓原文全文 → LLM 摘要 → grounding 檢查
→ 自動排程輸出的每日 AI 新聞 pipeline。每天由 GitHub Actions 定時執行,產物是
GitHub Pages 靜態網頁,自動更新。

線上網址:https://xin-chi.github.io/ai-news-pipeline/
摘要品質檢查:https://xin-chi.github.io/ai-news-pipeline/verify/

## 來源

按優先順序(也是選稿時的搶名額順序、頁面上的顯示順序):

| 順序 | 來源 | 配額 | 保底 | 備註 |
|---|---|---|---|---|
| 1 | OpenAI Blog | 5 | ✓ | 官方 RSS |
| 2 | Anthropic Blog | 5 | ✓ | 非官方鏡像 RSS(官方沒提供) |
| 3 | Google DeepMind | 5 | ✓ | 官方 RSS |
| 4 | Qwen | 2 | ✓ | 官方 blog RSS |
| 5 | Hugging Face | 2 | ✓ | 官方 RSS,feed 不含摘要欄位 |
| 6 | NVIDIA | 2 | ✓ | 官方 RSS + 關鍵字過濾(blog 含遊戲/車用/醫療) |
| 7 | iThome | 2 | ✓ | AI 分類 RSS + 關鍵字過濾雙重保險 |
| 8 | TechNews 科技新報 | 2 | ✓ | AI 分類 RSS + 關鍵字過濾雙重保險 |
| 9 | INSIDE | 2 | ✓ | 綜合 RSS(無 AI 分類),靠關鍵字過濾 |
| 10 | Hacker News | 5 | ✓ | 官方 API,依 upvote 分數排序後取前幾名 |
| 11 | Ars Technica | 3 | — | AI 分類 RSS |
| 12 | TechCrunch | 3 | — | AI 分類 RSS |

只收過去 24 小時內發布的內容,不足 `TOP_N` 是正常情況,不會硬湊舊文章。

**排序不只是主題分類,也對應「摘要含金量」。** 前面的來源有實質內文可以濃縮,
愈後面愈薄;Hacker News 擺在後段是因為它沒有內文可抓(見下方「全文抓取」),
產出的摘要實際上只是標題翻譯,排前面會讓品質最薄的卡片最先被看到。

**保底**是給發文頻率低、不保護就會消失的來源。Ars Technica 和 TechCrunch
天天都有大量新文章,本來就搶得到名額,不需要這層保護。

**⚠️ Anthropic 來源的已知風險**:Anthropic 官方沒有提供 RSS feed,目前用的是
第三方維護的非官方鏡像(`tim-hilde.github.io/anthropic-rss`)。這代表內容真實性
無法 100% 保證,維護者若停止更新或網址失效,這個來源會直接掛掉,而且沒有官方
替代方案可以馬上換。目前接受這個取捨,因為確實沒有更好的管道。

## 架構

    12 個來源 ─→ 24h 過濾 ─→ 去重 ─→ 保底+優先順序選稿 ─→ 抓原文全文 ─→ 逐篇 LLM 摘要
    (RSS/API)   (published)  (Jaccard)   (main.py)        (trafilatura)    (Gemini)
                                                                                │
        commit ←─ 寄通知信 ←─ grounding 檢查 ←─ 渲染靜態頁 ←──────────────────────┘
      (Actions)    (SMTP)      (verify.py)      (docs/)

### 全文抓取

各來源在 feed 裡給的摘要長度差很多——Hugging Face 是 0 字(完全沒有摘要欄位),
TechNews/INSIDE 只有 60~80 字。這種長度餵給 LLM,產出的「摘要」其實只是把原句
換句話說,沒有真正在濃縮資訊。所以選稿之後會再去抓一次原文正文。

- **只對需要的抓**:RSS 摘要已經夠長的(Anthropic 7000+ 字)直接跳過。
- **Hacker News 一律跳過**:它的連結指向任意網站,每天不同網域,失敗率高,
  還常碰到付費牆。這也是 HN 排在後段的原因。
- **付費牆是切斷不是丟棄**:metered paywall 給的前半段是文章真正的開頭,新聞
  是倒金字塔寫法,重點就在前段,對 40 字的摘要已經夠用。只切掉樣板話本身
  (「Already a subscriber? Sign in」之類),保留正文。
- **偵測用整句樣板話,不用單字**:`subscribe`、`訂閱` 這種單字在 AI 新聞正文裡
  本來就常出現(實測一則 1016 字的 ChatGPT 訂閱方案報導會被誤切)。
- 切完太短、或比原本的 RSS 摘要還短,就退回用 RSS 摘要——最糟不會比原本差。

## 抑制幻覺

分成三層:**輸入端把關**、**生成時約束**、**事後驗證**。

**輸入端**:上面那套全文抓取的品質門檻。如果讓一段被腰斬的付費牆前導當成「全文」
餵進去,模型就得拿殘缺的脈絡去寫「這篇文章的重點」,只能靠外推補完——這是
prompt 擋不住的。

**生成時**:逐篇餵、逐篇摘(不把多篇一次塞給模型混淆);prompt 明文禁止臆測;
來源 URL 在程式碼裡綁死、從不進入 LLM,杜絕張冠李戴;`temperature` 設 0
(摘要不需要創意,取樣隨機性只會提高挑到低機率字的機會);摘要上限 40 字——
這一條意外地是最有效的抑制器,短到沒有空間塞編造的細節。

**事後驗證**(`stages/verify.py`):每則摘要都要過三關——

1. 摘要不能跟標題一模一樣(那代表 summarize 當時失敗,fallback 成了標題)
2. 摘要裡的數字與英文詞,原文必須找得到
3. 把原文和摘要交給另一次 LLM 呼叫,判斷有沒有原文沒講的內容或誇大

**驗的是模型當初真正看到的那份文字,不是事後重抓的版本。** 重抓會比對到另一個
版本的文章,而且只餵標題產生的摘要會被拿去跟整篇文章比對而假性通過——那等於
沒驗到 pipeline 的行為。Hacker News 因此一律記為「無從檢查」而不是通過。

結果公開在 [`/verify/`](https://xin-chi.github.io/ai-news-pipeline/verify/),
`docs/verify/history.json` 就是資料庫,git 提供版本歷史。**目前只觀測、不介入**:
被標記的項目仍照常顯示在首頁,不會被下架或改寫。要先累積足夠的實際 flag 率,
有數據再決定要不要升級成攔截——為了還沒量到的問題加一個會誤判的元件並不划算。

首頁每張卡片的來源標籤旁有一顆色點,標示這則摘要是拿什麼產生的:
🟡 全文 / 🟢 RSS 摘要 / ⚫ 只有標題。

## 其他設計重點

- **來源容錯**:每個 fetcher 統一回傳 `(items, error)`,單一來源掛掉不會讓整條
  pipeline 失敗,只在頁面顯示小紅字提示——區分「今天沒發文」(正常)跟
  「抓取本身出錯」(異常)。
- **模型備援**:主模型遇到 429(額度)、503(Google 端容量不足)或被下架時,
  自動改打另一個世代的模型。實測過兩者的速率額度是分開計算的:對主模型打到
  429 的同一分鐘內,備援仍可正常回應。
  安全過濾擋下的情況(`PROHIBITED_CONTENT`)刻意不重試,換個模型一樣會被同一套
  政策擋下,重打只是浪費配額。
- **AI 關鍵字比對用完整單字,不是子字串**:英文關鍵字用 regex word boundary,
  避免 "Taiwan"、"email" 這類字裡剛好包含 "ai" 被誤判(踩過這個坑)。中文沒有
  這個風險,維持子字串比對。
- **去重**:輕量詞彙相似度(Jaccard),標題切詞後比重疊比例。
- **Gemini 免費額度限流**:15 RPM 上限,每次呼叫間隔 4.5 秒。
- **前端篩選**:純 JavaScript,勾選來源即時篩選(不重新抓資料);當天沒發文的
  來源 checkbox 自動鎖定。
- **通知信**:每天更新完寄一封,含各來源篇數、LLM 選出的推薦文章、grounding
  檢查結果。憑證走環境變數,沒設定就跳過不寄;寄信失敗只印警告不中斷 pipeline。
  log 裡不印收件者信箱——這個 repo 是公開的,CI log 任何人都看得到。
- **零成本**:GitHub Actions + GitHub Pages + Gemini API 免費額度,目前 $0。
  每天約 51 次 LLM 呼叫(25 摘要 + 1 推薦 + 25 驗證),免費額度上限 1000 RPD。

### 一個刻意的架構偏離

原本的設計原則是「這是 workflow 不是 agent:控制流由程式碼寫死,LLM 只在摘要
那一格被呼叫」。現在有兩處不成立了:

- `summarize.recommend()` 讓模型從當天清單裡挑一則寫推薦語(給通知信用)
- `verify.judge()` 做 grounding 判定

兩者都是刻意加的,不是疏忽。防護作法是**讓模型只回編號、不回內容**:推薦的
標題與連結一律取程式碼這邊的值,模型碰不到;回傳的編號不在範圍內、或推薦語
是空的,就整個當失敗、信件略過推薦區塊,不冒險顯示錯的東西。

## 使用

    pip install -r requirements.txt

    python main.py --mock   # 不呼叫 LLM、不寄信,測整條流程(仍會真的抓 12 個來源)
    python main.py

    # 事後回頭查某一份已產生的頁面(會重新抓原文,結果不如 /verify/ 準確)
    python tools/check_grounding.py --judge --limit 5

憑證放 `.env`(本機)或 GitHub Secrets(CI):`GEMINI_API_KEY`、`EMAIL_ADDRESS`、
`EMAIL_APP_PASSWORD`、`EMAIL_TO`。

`announcement.txt` 有內容時,頁面上會顯示一塊公告;清空就不顯示。

排程目標台灣時間 6:30(`.github/workflows/daily.yml`),排早一點是因為 GitHub
的 schedule 觸發常常會晚 1~2 小時(實測遇過 20 分鐘到 7 小時 44 分)。
