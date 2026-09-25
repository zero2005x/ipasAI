# zero2005x/ipasAI Topics 標籤策略規劃書

本文件為 GitHub 專案 `zero2005x/ipasAI`（iPAS AI 應用規劃師中級考綱教科書）設計之專案標籤（Topics）推廣策略，旨在提升專案在 GitHub 搜尋引擎、Explore、Topics 分類頁的曝光度與檢索權重。

---

## 1. 標竿分析：thc1006 vs. zero2005x

參考 iPAS 系列最具代表性的標籤實踐專案 `thc1006/ipas-net-zero-quiz`（使用上限 20 個 topics），對照分析如下：

| 維度 | thc1006/ipas-net-zero-quiz (20 個) | zero2005x/ipasAI 現況 | zero2005x/ipasAI 建議策略 (20 個) |
|---|---|---|---|
| 核心證照 | ipas, ipas-net-zero | 無 | ipas, ipas-ai, ai-application-planner |
| 級別區分 | 無 | 無 | intermediate-level, specialist-level |
| 主題範圍 | carbon-accounting, cbam, climate-change, esg, ifrs-s1, ifrs-s2, iso-14064, issb, net-zero, sbti, sustainability, tcfd | 無 | machine-learning, deep-learning, mlops, generative-ai, llm, ai-governance, eu-ai-act |
| 內容類型 | exam-preparation, quiz, study-tool | 無 | textbook, study-notes, exam-preparation, mock-exam, question-bank, pdf-translation |
| 技術/地區 | react, typescript, taiwan | 無 | taiwan, traditional-chinese |
| 總計 | 20 個標籤（已達最佳上限） | 0 個標籤 | 20 個標籤（精確對齊中級考綱與教材定位） |

---

## 2. 建議 20 個 Topics 分類與入選理由

依據 GitHub 搜尋引擎演算法與 iPAS 考生常見檢索關鍵字，精選以下 20 個標籤：

| 分類 | Topic | 推薦理由與檢索價值 |
|---|---|---|
| 證照識別 | `ipas` | 經濟部產業人才能力鑑定核心關鍵字，為所有 iPAS 系列專案必備總標籤 |
| 證照識別 | `ipas-ai` | iPAS 體系中人工智慧領域的專屬縮寫，方便跨級別檢索 |
| 證照識別 | `ai-application-planner` | 官方考綱之法定英文科目名稱（AI Application Planner） |
| 級別區分 | `intermediate-level` | 明確標示為「中級」規格，與初級入門教材精確區隔 |
| 級別區分 | `specialist-level` | 對應 iPAS 官方架構中的規劃師／專業級（Specialist Level）定位 |
| 主題範圍 | `machine-learning` | 第 II 冊（L22）與第 III 冊（L23）之核心考綱範疇 |
| 主題範圍 | `deep-learning` | 第 III 冊深度學習演算法、CNN、RNN、Transformer 之核心主題 |
| 主題範圍 | `mlops` | 第 I 冊 Ch 9 與整體系統生命週期、模型監控關鍵技術 |
| 主題範圍 | `generative-ai` | 第 I 冊 Ch 3 生成式 AI、提示工程、RLHF、AI Agent 核心主題 |
| 主題範圍 | `llm` | 大型語言模型技術與跨模態應用之高頻搜尋熱詞 |
| 主題範圍 | `ai-governance` | 第 I 冊 Ch 7 風險分類框架、倫理合規與治理規範 |
| 主題範圍 | `eu-ai-act` | 數位發展部與國際 AI 法規標準中之指標性立法，考綱指定範疇 |
| 內容類型 | `textbook` | 本專案核心產品定位（540 頁完整開源教科書），建立專屬識別 |
| 內容類型 | `study-notes` | 備考筆記通用標籤，吸引習慣以筆記為關鍵字檢索的讀者 |
| 內容類型 | `exam-preparation` | 證照備考領域之國際通用標籤，具備高權重流量 |
| 內容類型 | `mock-exam` | 本書收錄之 219 題原創情境模擬題與完整詳解 |
| 內容類型 | `question-bank` | 題庫與試題反查索引檢索標籤 |
| 內容類型 | `pdf-translation` | 本書提供之自動化編譯輸出與跨格式處理工具鏈 |
| 地區語言 | `taiwan` | 經濟部產業人才能力鑑定為台灣官方認證體系 |
| 地區語言 | `traditional-chinese` | 本書為全繁體中文原創教材，在繁中技術社群具備稀缺性 |

---

## 3. Topics 套用操作指南

GitHub Topics 可透過網頁介面或 GitHub API / CLI 進行套用。

### 方式 A：透過 GitHub 網頁介面（操作簡便）

1. 使用瀏覽器開啟專案主頁：`https://github.com/zero2005x/ipasAI`
2. 於頁面右上方「About」區塊點選齒輪圖示（Edit repository metadata）。
3. 在「Topics」輸入欄位中，依序填入上述 20 個標籤（輸入後按 Enter 鍵確認）：
   `ipas`, `ipas-ai`, `ai-application-planner`, `intermediate-level`, `specialist-level`, `machine-learning`, `deep-learning`, `mlops`, `generative-ai`, `llm`, `ai-governance`, `eu-ai-act`, `textbook`, `study-notes`, `exam-preparation`, `mock-exam`, `question-bank`, `pdf-translation`, `taiwan`, `traditional-chinese`
4. 點選「Save changes」完成儲存。

### 方式 B：透過 GitHub CLI 或 API（自動化執行）

#### 使用 GitHub CLI (`gh`) 一鍵套用：
```bash
gh repo edit zero2005x/ipasAI --add-topic "ipas,ipas-ai,ai-application-planner,intermediate-level,specialist-level,machine-learning,deep-learning,mlops,generative-ai,llm,ai-governance,eu-ai-act,textbook,study-notes,exam-preparation,mock-exam,question-bank,pdf-translation,taiwan,traditional-chinese"
```

#### 使用 GitHub REST API PUT 套用：
```bash
curl -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/zero2005x/ipasAI/topics \
  -d '{"names":["ipas","ipas-ai","ai-application-planner","intermediate-level","specialist-level","machine-learning","deep-learning","mlops","generative-ai","llm","ai-governance","eu-ai-act","textbook","study-notes","exam-preparation","mock-exam","question-bank","pdf-translation","taiwan","traditional-chinese"]}'
```

---

## 4. 補充建議：README 是否應增設 Topics 說明段落

經評估，建議**不要**在專案根目錄的 `README.md` 中獨立開闢專門的 Topics 段落，理由如下：
1. **GitHub 既有 UI 呈現**：GitHub 已經在專案頁面右側欄（About 區塊）以醒目的原生徽章集中呈現所有 Topics，重複列於 README 內容易分散讀者注意力。
2. **頂部 Badges 已涵蓋核心元數據**：`README.md` 開頭已配置 Shields.io 徽章（授權、版本、PDF 引擎、繁體中文），已具備足夠的元數據展示效果。
3. **保持 README 以學習者路徑為導向**：重構後的 README 應聚焦於「快速開始」、「推薦使用路徑」、「全書章節大綱」與「相關專案」，維持高度專注之閱讀動線。
