# iPAS AI 應用規劃師（中級）考綱教科書

![iPAS AI 應用規劃師中級考綱教科書](docs/banner.png)

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/Content-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version: v0.3.0](https://img.shields.io/badge/Version-v0.3.0-0F5C6E.svg)](https://github.com/zero2005x/ipasAI/releases)
[![PDF Engine](https://img.shields.io/badge/PDF%20Engine-Chrome%20Headless%20%7C%20WeasyPrint-success.svg)](https://github.com/zero2005x/ipasAI/releases)
[![Language: 繁體中文](https://img.shields.io/badge/Language-%E7%B9%81%E9%AB%94%E4%B8%AD%E6%96%87-red.svg)](https://github.com/zero2005x/ipasAI)

> iPAS AI 應用規劃師（中級）考綱教科書 v0.3 開源版 — 全套三冊完整教材 + 219 題原創情境模擬題 + 300 題官方試題解析索引 + 課本風 PDF 排版編譯工具鏈

本專案為經濟部產業人才能力鑑定 **「iPAS 人工智慧應用規劃師（中級）」** 完整開源備考教科書與題庫體系（對應考綱規範：**經濟部 115.06 版**）。全書約 80 萬字、34 個章節，涵蓋共通必考科及雙專業路線，並配備完整的自動化工程校驗管線與課本風 PDF 排版編譯系統。

---

## 線上閱讀與 PDF 下載

讀者可前往 **[GitHub Releases 頁面](https://github.com/zero2005x/ipasAI/releases)** 直接免費下載最新編譯之完整 A4 課本風 PDF：

| 冊別 | 考科代碼 | 對應路線／專業科目 | 規格 | PDF 下載 (Release) |
|:---:|:---:|:---|:---:|:---:|
| **第 I 冊** | **L21** | 人工智慧技術應用與規劃（共通必考科目） | 167 頁 | [下載第 I 冊 PDF](https://github.com/zero2005x/ipasAI/releases/download/v0.3.0/iPAS_AI_Level2_Book1_L21_Architecture_v0.3.pdf) |
| **第 II 冊** | **L22** | 巨量資料分析與處理（數據分析專業路線） | 193 頁 | [下載第 II 冊 PDF](https://github.com/zero2005x/ipasAI/releases/download/v0.3.0/iPAS_AI_Level2_Book2_L22_BigData_v0.3.pdf) |
| **第 III 冊** | **L23** | 深度學習與演算法實務（機器學習專業路線） | 180 頁 | [下載第 III 冊 PDF](https://github.com/zero2005x/ipasAI/releases/download/v0.3.0/iPAS_AI_Level2_Book3_L23_EdgeAI_v0.3.pdf) |

<!-- TODO: 若後續部署 GitHub Pages 線上閱讀版或線上模擬測驗，請在此處補上 Pages 連結 -->

---

## 專案截圖

| 教材章節內頁排版 | 題目卡片與答案防透設計 | 自動化 PDF 編譯管線 |
|:---:|:---:|:---:|
| ![教材內頁範例](docs/screenshots/sample-page.png)<br>*(課本風排版、考點卡、彩色呼告框)* | ![題目卡片範例](docs/screenshots/sample-quiz.png)<br>*(懸掛縮排題目卡、解析移至章末)* | ![編譯工具範例](docs/screenshots/sample-build.png)<br>*(實際 PDF 編譯日誌)* |

---

## 核心特色

- **完整涵蓋中級考綱全範疇**：全套三冊共 34 章、540 頁、約 80 萬字，嚴格對齊經濟部最新考綱標準規範。
- **三級題庫體系與詳解**：
  - **219 題原創情境模擬題**：四選項均附思路引導與深入逐項解析。
  - **300 題官方公告試題深度反查索引**：雙向對應課文段落，快速查驗知識盲點。
  - **110 題學習指引練習題**：章末嵌入官方指引範例題對位。
- **課本風高品質排版系統**：
  - 自動修復斷句硬換行，呈現流暢段落。
  - 獨立淡色模擬題卡（`sim-card`）與答案防透設計。
  - 語意提示框系統（觀念、實務、陷阱、注意、速記）。
  - 動態欄寬自適應對比表格，支援跨頁排版。
- **自動化工程校驗管線**：內建 Python 檢查器，包含官方考綱規格嚴格查核、程式碼語法檢測與字元多重集合多層防護。
- **純文字 Markdown 開源**：全書原始碼開放，支援 Fork、自訂主題與本地二次編譯。

---

## 推薦使用路徑

依循以下 5 個步驟，能最高效率掌握中級檢定全部考點：

1. **第一步：研讀考綱架構與各冊前頁地圖**
   - 檢視共通必考科目總體定位：[`book/L21/v0.3/front/`](book/L21/v0.3/front/)
   - 了解全書章節分層（核心必考、官方補充、產業延伸、版本敏感）。
2. **第二步：依報考路線循序精讀教材內容**
   - 共通必考科目：研讀第 I 冊 [`book/L21/v0.3/`](book/L21/v0.3/)（Ch 1 至 Ch 9）
   - 數據分析路線：研讀第 II 冊 [`book/L22/v0.3/`](book/L22/v0.3/)（Ch 1 至 Ch 13）
   - 演算法研發路線：研讀第 III 冊 [`book/L23/v0.3/`](book/L23/v0.3/)（Ch 1 至 Ch 12）
   - 考點補丁與共用模組：參閱 [`shared/book/modules/`](shared/book/modules/)
3. **第三步：每章章末自我檢測模擬題**
   - 演練題目卡片中的 4 選項模擬題（例如：[`book/L21/v0.3/ch01.md`](book/L21/v0.3/ch01.md)）。
   - 完成後翻至章末「模擬題解答與解析」核對詳解與考點邏輯。
4. **第四步：利用官方試題索引進行章節回測**
   - 查閱歷屆公告試題雙向索引：[`shared/book/apxA.md`](shared/book/apxA.md)
   - 依官方公告試題題號反查回教材對應節次，確認觀念理解完整性。
5. **第五步：使用編譯工具客製輸出專屬講義**
   - 使用 [`tools/build_pdf.py`](tools/build_pdf.py) 編譯單冊或全冊 A4 課本風 PDF。
   - 可依需求自訂 CSS 樣式與頁面比例。

---

## 專案規模與核心數據

| 統計指標 | 第 I 冊 (L21) | 第 II 冊 (L22) | 第 III 冊 (L23) | 全書總計 |
|:---|:---:|:---:|:---:|:---:|
| **章節數量** | 9 章 | 13 章 | 12 章 | **34 章** |
| **原創模擬題（含逐項詳解）** | 58 題 | 85 題 | 76 題 | **219 題** |
| **程式判讀題（Python / PySpark）** | 0 題 | 30 題 | 24 題 | **54 題** |
| **官方公告試題對位（114-2、115-1）** | 100 題 | 100 題 | 100 題 | **300 題** |
| **官方學習指引練習題章末對位** | 30 題 | 40 題 | 40 題 | **110 題** |
| **學習指引官方補充節點** | 7 節 | 14 節 | 14 節 | **35 節** |
| **考點補丁與共用模組** | 18 節 | 18 節 | 19 節 | **55 節** |

---

## 三冊章節結構大綱

### 第 I 冊：人工智慧技術應用與規劃（L21）
- **定位**：中級檢定所有考生必考之共通科目。
- **章節大綱**：
  - Ch 1 自然語言處理技術與應用（TF-IDF、Word2Vec、Transformer、BERT、GPT、T5、NER、RAG）
  - Ch 2 電腦視覺技術與應用（CNN、ResNet、YOLO、目標偵測、語意分割、實例分割、可解釋性）
  - Ch 3 生成式 AI 與大型語言模型（VAE、GAN、擴散模型、RLHF、DPO、提示工程、AI Agent）
  - Ch 4 多模態技術與跨領域應用（CLIP、BLIP、語音辨識、圖文生成、跨模態對齊）
  - Ch 5 AI 導入評估與架構設計（價值矩陣、POC 評估、成本估算、技術選型、數位成熟度）
  - Ch 6 AI 專案管理與敏捷實務（CRISP-DM、敏捷開發、護欄指標、風險評估、團隊協同）
  - Ch 7 AI 風險管理、法規與倫理（數位發展部《人工智慧風險分類框架》、個資法、著作權、代理變數、公平性）
  - Ch 8 跨領域 AI 應用規劃綜合實務（醫療、製造、金融、零售等場景選型與指標架構）
  - Ch 9 MLOps 與系統維運監控（CI/CD、資料漂移、概念漂移、服務降級、SLA）

### 第 II 冊：巨量資料分析與處理（L22）
- **定位**：數據分析師與巨量資料工程師專業路線。
- **章節大綱**：
  - Ch 1 統計分析基礎與資料描述（機率分佈、敘述統計、假設檢定原理、常見偏誤）
  - Ch 2 機率分佈與推論統計（常見離散/連續分佈、中心極限定理、參數估計）
  - Ch 3 假設檢定實務與 A/B 測試（t 檢定、Z 檢定、卡方檢定、ANOVA、兩類錯誤、統計檢定力）
  - Ch 4 資料清理、轉換與前處理實務（缺失值處理、異常值過濾、編碼、正規化）
  - Ch 5 特徵工程與維度縮減（特徵選取、特徵提取、PCA、SVD、t-SNE）
  - Ch 6 分散式運算架構與巨量資料管線（Hadoop、Spark、PySpark 程式判讀、DAG、串流架構）
  - Ch 7 關聯分析與推薦系統基礎（Apriori、FP-Growth、協同過濾、冷啟動）
  - Ch 8 分群與非監督式學習（K-Means、DBSCAN、階層式分群、評估指標）
  - Ch 9 資料視覺化與商業洞察表達（視覺化圖表選型、Tufte 原則、儀表板規劃）
  - Ch 10 大數據儲存與資料庫選型（SQL vs. NoSQL、圖資料庫、資料湖、特徵商店）
  - Ch 11 資料品質與資料治理實務（資料品質六維度、資料血統、資料字典、存取控制）
  - Ch 12 商業指標體系建構（北極星指標、AARRR、指標拆解、歸因分析）
  - Ch 13 資料隱私、合規與安全（去識別化技術、差異隱私、零信任、GDPR/CCPA）

### 第 III 冊：深度學習與演算法實務（L23）
- **定位**：機器學習工程師與演算法研發專業路線。
- **章節大綱**：
  - Ch 1 機器學習數學基礎（線性代數、微積分、機率與最佳化基礎）
  - Ch 2 經典機器學習演算法（線性迴歸、Logistic 迴歸、SVM、決策樹、隨機森林）
  - Ch 3 整合學習與 Boosting 架構（AdaBoost、GBDT、XGBoost、LightGBM、CatBoost）
  - Ch 4 類神經網路與深度學習核心原理（感知器、多層感知機、反向傳播、激活函數、正則化）
  - Ch 5 卷積神經網路實務（經典 CNN 架構、遷移學習、注意力機制在 CV 的應用）
  - Ch 6 序列模型與注意力架構（RNN、LSTM、GRU、Transformer、BERT vs. GPT）
  - Ch 7 模型訓練與最佳化技巧（最佳化器選型、學習率排程、批次正規化、梯度裁剪）
  - Ch 8 輕量化技術與模型壓縮（模型剪枝、知識蒸餾、權重晶化、LoRA/QLoRA）
  - Ch 9 模型驗證與評估指標體系（交叉驗證、混淆矩陣、ROC/AUC、PR-AUC、指標對位）
  - Ch 10 超參數調優與自動化機器學習（Grid Search、Random Search、Bayesian Optimization、AutoML）
  - Ch 11 隱私強化技術與聯邦學習（差分隱私、安全多方計算、同態加密、聯邦學習架構）
  - Ch 12 AI 偏誤診斷與可解釋性技術（SHAP、LIME、反事實解釋、偏誤緩解實務）

---

## 專案目錄結構

```text
├── book/                  # 三冊教科書核心 Markdown 書稿
│   ├── L21/v0.3/          # 第 I 冊章節檔 (front, ch01–ch09, apxB)
│   ├── L22/v0.3/          # 第 II 冊章節檔 (front, ch01–ch13, apxB)
│   └── L23/v0.3/          # 第 III 冊章節檔 (front, ch01–ch12, apxB)
├── shared/                # 三冊共用文檔與模組
│   └── book/              # 跨冊共用前頁、共用章節模組與附錄 A（歷屆試題索引）
├── audit/                 # 歷次版本修正查核日誌與嚴格白名單 (C01–C57)
├── tools/                 # 自動化檢查器、統計同步與 PDF 編譯工具集
│   ├── build_pdf.py       # Markdown → 課本風 HTML → Chrome Headless PDF
│   ├── check_book.py      # 考綱規範、用語、分層與索引自動化檢查器
│   ├── check_render_integrity.py  # 渲染完整性與字元多重集合驗證工具
│   └── test_code_blocks.py        # Python 程式碼區塊語法檢測
├── prompts/               # 撰寫規格指引與排版修正計畫文檔
├── docs/                  # 專案文檔、策略書與截圖資產
├── LICENSE                # 雙重授權條款 (CC BY-NC-SA 4.0 + MIT)
└── README.md              # 專案主說明文件
```

---

## 本地開發與編譯指南

### 環境需求
- Python 3.10+
- Google Chrome 或 Microsoft Edge（用於 Headless PDF 輸出）
- poppler-utils（可選，提供 `pdftotext` 驗證功能）

### 常用指令

```bash
# 1. 執行官方考綱嚴格語意與規格檢查（全冊 0 錯誤關卡）
python -B tools/check_book.py L21 --strict
python -B tools/check_book.py L22 --strict
python -B tools/check_book.py L23 --strict

# 2. 執行全書程式碼區塊語法檢查
python -B tools/test_code_blocks.py

# 3. 編譯產出單冊 A4 課本風 PDF（輸出至 build/<VOL>/）
python -B tools/build_pdf.py L21
python -B tools/build_pdf.py L22
python -B tools/build_pdf.py L23

# 4. 驗證渲染文字完整性與 PDF 識別碼
python -B tools/check_render_integrity.py
```

---

## 貢獻指南

歡迎社群夥伴共同完善這套開放教材！您可以透過以下方式參與：
- **回報勘誤**：若發現教材內容、程式碼、公式或試題解析有錯，歡迎提交 [Issue](https://github.com/zero2005x/ipasAI/issues)。
- **提供改進建議**：歡迎提交 Pull Request 協助修正文字、補強考點說明或優化編譯工具。
- **分享學習心得**：歡迎在 GitHub Discussions 或社群分享備考筆記與學習心得。

---

## 相關專案 (Related Projects)

以下是 GitHub 上其他與 iPAS AI 應用規劃師考試相關的開源專案，歡迎互相參考學習：

| 專案 | 範圍 | 內容特色 |
|---|---|---|
| [yazelin/ipas-ai-quiz](https://github.com/yazelin/ipas-ai-quiz) | 全級 | 611 題歷屆考古題線上模擬考（純前端 + Cloudflare 同步） |
| [thc1006/ipas-net-zero-quiz](https://github.com/thc1006/ipas-net-zero-quiz) | iPAS 淨零碳 | 781 題題庫 + AI 輔助解析（同屬 iPAS 系列，可參考其 React + TS 技術棧） |
| [andrew54068/ipas-quiz](https://github.com/andrew54068/ipas-quiz) | 中級 | 195 題已驗證 MCQ + 解析 + study-guide deep links |
| [alvinlin/iPAS-AIAP-Exam-Site](https://github.com/alvinlin/iPAS-AIAP-Exam-Site) | 全級 | 600 題線上模擬考 + HTML 教材 |
| [HongWeiRu/ipas-study](https://github.com/HongWeiRu/ipas-study) | 中級 | 互動式學習教材 |
| [ccwu0918/ipas-ai-overview](https://github.com/ccwu0918/ipas-ai-overview) | 中級 | 總覽互動簡報 |
| [polarbear0827/ipas-ai-middle-quiz](https://github.com/polarbear0827/ipas-ai-middle-quiz) | 中級 | 中級刷題 GitHub Pages app |
| [TEA-CARSON/ai-application-planner-middle-exam](https://github.com/TEA-CARSON/ai-application-planner-middle-exam) | 中級 | 歷屆試題 + JSON/CSV/Excel 題庫 |
| [lulumi7788/ipas-aiap-toolkit](https://github.com/lulumi7788/ipas-aiap-toolkit) | 初級 | 把官方 PDF 試題轉成可刷題庫的工具箱 |
| [LinSingYu/AI_Application_Planner_Quiz](https://github.com/LinSingYu/AI_Application_Planner_Quiz) | 全級 | 用 Gemini AI 生成題目與解析 |
| [HeyMrSalt/iPAS-Specialist-Notes](https://github.com/HeyMrSalt/iPAS-Specialist-Notes) | iPAS 資安工程師中級 | 同屬 iPAS 系列的資安工程師備考筆記 |

> 如果你也有 iPAS AI 相關的開源專案，歡迎開 issue 或 PR 加入此清單。

---

## 授權條款與免責聲明

- **教科書內容與題庫**：採用 [創用 CC 姓名標示-非商業性-相同方式分享 4.0 國際 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant) 授權。歡迎自由非商業轉載與分享，轉載時請註明出處並以相同方式分享。
- **編譯工具與程式碼**：採用 [MIT License](https://opensource.org/licenses/MIT) 授權。
- **免責聲明**：本教材為社群備考自學之開放教材，非經濟部 iPAS 官方發行品。試題對位與考綱索引僅為教學輔助，官方考題著作權歸經濟部產業發展署與主辦單位所有。
