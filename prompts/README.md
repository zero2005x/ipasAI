# iPAS 中級考綱教科書 v0.3　改版工作包

這個資料夾是 **v0.3 改版的完整工作包**。三冊書（L21／L22／L23）的 v0.2.0 原始檔不存在，
只有印刷版 PDF，因此整條流程是「**從 PDF 重建可編輯結構 → 套用規則 → 自動檢查 → 編譯 PDF**」。

---

## 給 AI agent 的用法（照這個順序）

1. **先讀** `prompts/00_shared_spec.md`（共用規格：用語、分層、政府文件說法、自動檢查規則）。
2. **再讀**你要負責那一冊的任務 prompt：
   - `prompts/L21_task.md` — 第 I 冊（必考共通科）
   - `prompts/L22_task.md` — 第 II 冊（數據分析路線）
   - `prompts/L23_task.md` — 第 III 冊（機器學習路線）
3. **跑基準**：
   ```bash
   python3 tools/build_skeleton.py L21     # 重建結構
   python3 tools/check_book.py L21         # 取得目前違規清單
   ```
4. **改書**：編輯 `book/L21/v0.3/` 下的章節檔（**不要改 `skeleton.md`**）。
5. **驗收**：
   ```bash
   python3 tools/check_book.py L21 --strict   # 必須 exit 0
   python3 tools/build_pdf.py L21             # 產生 PDF
   ```

---

## 目錄結構

| 路徑 | 內容 | 可否手改 |
|---|---|---|
| `prompts/00_shared_spec.md` | **共用撰寫規格（凍結版）** | 改規則時改這裡 |
| `prompts/L2x_task.md` | 各冊具體待辦 | 可 |
| `shared/errata_1150410.json` | 學習指引勘誤表 19 條（結構化）＋用語對照 | 可 |
| `shared/language_rules.json` | 15 則核准的絕對化用語改寫＋通用偵測 | 可 |
| `sources_extracted/` | 官方 PDF 擷取原文、四份分析 CSV、115.06 範圍 | 不改（原始素材） |
| `book/L2x/skeleton.md` | v0.2.0 原文重建（page-anchored） | **不可**，用工具重生 |
| `book/L2x/toc.json` | 章節／節索引（偵測自正文） | **不可** |
| `book/L2x/stats.json` | 所有讀者可見數字的唯一來源 | **不可** |
| `book/L2x/v0.3/` | **要改的書稿**（front／ch01–ch13／apxA–B） | **可** ← 主要工作區 |
| `book/L2x/v0.3/REVIEW.md` | 自動產生的待辦與稽核報告 | 重生 |
| `build/L2x/` | 編譯產物（HTML／PDF） | 重生 |
| `ori_book_pdf/` | v0.2.0 三冊原始 PDF | 唯讀 |

---

## 工具

| 工具 | 用途 |
|---|---|
| `tools/build_skeleton.py L21` | 從 PDF 擷取重建 `skeleton.md`／`toc.json`／`stats.json` |
| `tools/check_book.py L21 [--strict] [--json out]` | 自動檢查（用語／絕對化／製作殘留／統計／索引／對應來源） |
| `tools/make_v03.py L21` | 切出 `v0.3/` 章節檔並產生 `REVIEW.md` |
| `tools/build_pdf.py L21` | Markdown → HTML → PDF（WeasyPrint） |

### 結構偵測的重要說明

**章節結構偵測自「正文」，不是印刷目錄。** v0.2.0 的印刷目錄不可靠：

- L21 印刷目錄的節標題與正文黏在一起，且**第 7、8、9 章各缺一節**。
- **L22 印刷目錄完全漏掉第 10–13 章**（大數據與機器學習、鑑別式 AI、生成式 AI、隱私安全），
  且第 9 章的節會漂移到後面的章。

正文的章標題很規律（每章都從頁首的「第 N章」開始），所以工具改以正文為準。
實測結果：**L21 9 章／L22 13 章／L23 12 章**，與 115.06 版評鑑內容範圍完全一致。

---

## 環境限制（已知）

- **沒有 pandoc**；PDF 走 `weasyprint` + 本機唯一 CJK 字型 `Droid Sans Fallback`。
- PDF 擷取原文的**數學式會失真**（例如 `∑n i=1(xi− ¯x)2`），v0.3 編輯時**必須逐式重打**。
- 用手算的表格在 PDF 擷取後會**黏成一行**，編輯時須重建表格。

---

## 目前進度

| 項目 | 狀態 |
|---|---|
| 共用規格、三冊任務 prompt | ✅ 完成 |
| L21／L22／L23 結構重建（skeleton／toc／stats） | ✅ 完成 |
| 自動檢查工具（六類檢查） | ✅ 完成，已驗證能抓到真實違規 |
| 勘誤表 19 條結構化 | ✅ 完成 |
| PDF 編譯管線 | ✅ 可跑（L21 135 頁 A4） |
| `v0.3/` 章節書稿 | ⏳ 已切出，內容仍為 v0.2.0 原文，**待套用 P0 修正** |

**尚未通過編譯關卡**（`check_book.py` error：L21 63、L22 64、L23 51）。這些 error 就是待辦清單本身。
