# 專案最佳化變更摘要與待補項目清單 (Changes Summary)

本文件彙整本次針對 `zero2005x/ipasAI` 專案所進行之門面重構、生態系 cross-link 網絡建立與 Topics 標籤規劃成果。

---

## 1. README 重構架構對照與 Diff 摘要

本次重構參考了 iPAS AI 領域最受歡迎專案 `yazelin/ipas-ai-quiz` 的呈現架構，將原本偏向工程報告風格的 README，全面升級為「學習者導向」的高轉換率開源門面：

| 段落順序 | 原始 README 結構 | 重構後 Proposed README 結構 | 變更說明 |
|:---:|:---|:---|:---|
| 1 | 專案標題 + Badges | 專案橫幅（佔位） | 新增頂部橫幅佔位（引導配置 1280x320 視覺圖） |
| 2 | 引言說明 | 一句話定位 + Badges | 整合繁中標籤、雙授權、PDF 引擎與一句話引言 |
| 3 | 電子書 PDF 直接下載 | 線上閱讀與 PDF 下載 | 保留三冊下載直連，新增線上閱讀/Pages TODO 佔位 |
| 4 | - | 專案截圖區 | 新增教材內頁、題目卡片、編譯工具 3 連截圖展示區 |
| 5 | - | 核心特色 (Features) | 提煉 5 大核心特色，幫助訪客 5 秒掌握專案亮點 |
| 6 | - | 推薦使用路徑 (Usage Path) | 新增關鍵 5 步循序指引，搭配真實相對路徑導引 |
| 7 | 專案規模與核心數據 | 專案規模與核心數據 | 保留完整 7 項指標對照數據表 |
| 8 | 三冊內容結構 (34 章大綱) | 三冊章節結構大綱 (34 章大綱) | 完整保留 34 章詳細考綱與各章節主題範疇 |
| 9 | 排版特色說明 | 專案目錄結構 | 精簡版面敘述，以清楚的目錄樹狀圖呈現 |
| 10 | 本地開發與編譯指南 | 本地開發與編譯指南 | 完整保留考綱檢查、程式檢測與 PDF 編譯指令 |
| 11 | - | 貢獻指南 (Contributing) | 新增 Issue 勘誤、PR 與社群討論引導 |
| 12 | - | 相關專案 (Related Projects) | 新增 11 個 iPAS 生態系專案 cross-link 降序表格 |
| 13 | 授權條款與免責聲明 | 授權條款與免責聲明 | 完整保留 CC BY-NC-SA 4.0 + MIT 雙授權及免責聲明 |

---

## 2. 待補項目清單 (TODO Checklist)

視覺資產已補齊，交付項目如下：

- [x] **橫幅圖檔**：`docs/banner.png`
  - 建議尺寸：`1280 x 320 px` PNG 格式。
  - 設計元素：包含「iPAS AI 應用規劃師」、「中級考綱教科書」、「經濟部 115.06 版」及三冊立體封面示意圖。
- [x] **截圖一（教材內頁）**：`docs/screenshots/sample-page.png`
  - 建議內容：展示課本風排版、考點卡、彩色語意提示框（觀念/實務/注意）與雙欄表格。
- [x] **截圖二（題目卡片）**：`docs/screenshots/sample-quiz.png`
  - 建議內容：展示懸掛縮排題幹、(A)至(D)選項，以及章末解答解析徽章（答案防透設計）。
- [x] **截圖三（編譯工具）**：`docs/screenshots/sample-build.png`
  - 建議內容：終端機執行 `python tools/build_pdf.py` 之編譯日誌畫面或渲染預覽圖。
- [ ] **線上閱讀部署**（選用）：若未來建立 GitHub Pages 或靜態閱讀網站，可將網址補入「線上閱讀與 PDF 下載」段落。

---

## 3. Topics 標籤套用摘要

已規劃之 20 個 Topics 標籤如下（詳細分類與入選理由請見 `docs/topics-strategy.md`）：

```text
ipas, ipas-ai, ai-application-planner, intermediate-level, specialist-level, machine-learning, deep-learning, mlops, generative-ai, llm, ai-governance, eu-ai-act, textbook, study-notes, exam-preparation, mock-exam, question-bank, pdf-translation, taiwan, traditional-chinese
```

### 套用指令（GitHub CLI）：
```bash
gh repo edit zero2005x/ipasAI --add-topic "ipas,ipas-ai,ai-application-planner,intermediate-level,specialist-level,machine-learning,deep-learning,mlops,generative-ai,llm,ai-governance,eu-ai-act,textbook,study-notes,exam-preparation,mock-exam,question-bank,pdf-translation,taiwan,traditional-chinese"
```

---

## 4. 推薦 Git Commit Messages

遵循 Conventional Commits 規範之建議英文 Commit 訊息：

1. **套用重構 README 與生態網絡**：
   ```text
   docs(readme): restructure README following yazelin pattern with usage path, screenshots, and related projects cross-linking
   ```
2. **新增 Topics 標籤規劃書與變更摘要**：
   ```text
   docs: add topics strategy document and optimization changes summary
   ```
