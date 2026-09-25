"""Apply narrow, idempotent cleanup to the PDF-reconstructed v0.3 drafts.

Keep editorial changes here reviewable. Run from the repository root; the
original v0.2 PDFs and skeletons are never changed.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DATE = "中華民國 115 年 9 月 24 日"

# Row names were inspected against the original page transcription before
# reconstructing these two-column chapter-end recaps. Continuation lines are
# joined to the preceding named row; a second extracted header is discarded.
RECAP_LABELS = {
    "L21/ch01.md": "文本表示|TF-IDF|RNN|LSTM／ GRU|自注意力|架構選型|指標",
    "L21/ch02.md": "四大任務|CNN|IoU|mAP|偵測器|閾值|治理",
    "L21/ch03.md": "鑑別式 vs生成式|三架構弱點|溫度|RLHF|四層策略|幻覺|權限|法遵",
    "L21/ch04.md": "共享嵌入空間|三種融合|模態缺失|模態不平衡|時間對齊|治理",
    "L21/ch05.md": "四層可行性|效能基準|TCO|ROI|NPV|效益型態|階段閘門|高風險",
    "L21/ch06.md": "CRISP-DM|需求轉譯|標籤定義|標籤洩漏|四層 KPI|關鍵路徑|治理",
    "L21/ch07.md": "風險四象限|應對策略|框架四步驟|風險類型表|客觀固有風險|六大法益|框架三個「不」|金管會六指標|高風險措施|主管機關",
    "L21/ch08.md": "順序|缺失值|離群值|編碼|縮放|選型|洩漏六源",
    "L21/ch09.md": "推論型態|發布策略|MLOps|偏斜|兩種漂移|PSI|重訓|治理",
    "L22/ch01.md": "集中趨勢|偏態|變異數|CV|離群值|相關係數|程式",
    "L22/ch02.md": "分佈辨識|卜瓦松|常態|中央極限定理",
    "L22/ch03.md": "p值|決策用語|兩類錯誤|檢定力|單雙尾|多重比較|顯著性|程式",
    "L22/ch04.md": "品質六構面|缺失機制|缺失率門檻|插補鐵律|ETL／ ELT|程式",
    "L22/ch05.md": "三種架構|OLTP vs OLAP|欄式優勢|NoSQL四型|CAP|治理",
    "L22/ch06.md": "批次 vs串流|Hadoop vs Spark|惰性求值|Shuffle|資料傾斜|collect|Kafka|時間語意",
    "L22/ch07.md": "縮放方法|離群值敏感度|對數轉換|PCA前置|PCA性質|n_components|t-SNE|樹模型",
    "L22/ch08.md": "分群|選 k|關聯規則|圖分析|時序|不平衡四層|評估指標|重採樣",
    "L22/ch09.md": "選型|圓餅圖|誠信|可及性|效能|治理|編碼精確度",
    "L22/ch10.md": "5V|資料量|分散式訓練|維度詛咒|NumPy軸",
    "L22/ch11.md": "分野|時間點正確性|時間洩漏|時序切分|觀察期／表現期",
    "L22/ch12.md": "六項需求|去重|品質 vs數量|去毒|合規|在地化",
    "L22/ch13.md": "三組對應|差分隱私|聯邦學習|去識別化|k-匿名|模型|加密|四層檢核",
    "L23/ch01.md": "損失函數|貝氏|單純貝氏|偏差-變異|不可約誤差|ddof",
    "L23/ch02.md": "餘弦相似度|矩陣乘法|特徵值|SVD|PCA",
    "L23/ch03.md": "梯度下降|優化器|NaN|梯度消失|激活函數|epoch|複雜度",
    "L23/ch04.md": "五範式|L1|L2|方向性|Dropout|欠擬合",
    "L23/ch05.md": "集成|隨機森林|Boosting|學習率|縮放|predict_proba|DBSCAN",
    "L23/ch06.md": "歸納偏置|卷積輸出|參數量|輸出層|LSTM／ GRU|批次大小|遷移學習",
    "L23/ch07.md": "順序|fit／ transform|Pipeline|編碼|未知類別|縮放|資料增強|缺失",
    "L23/ch08.md": "五步流程|基準線|輸出層|softmax陷阱|限制導向",
    "L23/ch09.md": "Precision|Recall|F1|閾值|不平衡|R2|交叉驗證|洩漏六源|程式",
    "L23/ch10.md": "搜尋策略|訓練次數|best_score_|巢狀交叉驗證|過擬合|欠擬合|調參順序|壓縮",
    "L23/ch11.md": "六種攻擊|生成式風險|護欄五層|鐵律一|鐵律二|稽核",
    "L23/ch12.md": "六種偏誤|代理變數|不可能定理|三個介入點|可解釋性|解釋 ̸=因果|治理",
}


def rebuild_recaps(s: str, key: str) -> str:
    if key not in RECAP_LABELS or "主題 必記結論" not in s:
        return s
    labels = sorted(RECAP_LABELS[key].split("|"), key=len, reverse=True)
    lines = s.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if lines[i] != "主題 必記結論":
            out.append(lines[i]); i += 1; continue
        rows = []
        i += 1
        while i < len(lines) and not (lines[i].startswith("<!-- pdf-page") or lines[i].startswith("### ") or lines[i].startswith("#### ")):
            line = lines[i].strip()
            i += 1
            if not line or line == "主題 必記結論":
                continue
            label = next((x for x in labels if line.startswith(x + " ")), None)
            if label:
                rows.append([label, line[len(label):].strip()])
            elif rows:
                rows[-1][1] += line if line.startswith(("；", "，", "。", "／")) else " " + line
            else:
                raise ValueError(f"unmatched recap line before first row: {key}: {line}")
        if not rows:
            raise ValueError(f"empty recap: {key}")
        out.extend(["| 主題 | 必記結論 |", "| --- | --- |"])
        out.extend(f"| {a} | {b.replace('|', '∣')} |" for a, b in rows)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def rebuild_numbered_code(s: str) -> str:
    """Turn consecutive PDF-captured code line numbers into fenced examples."""
    lines = s.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if not re.match(r"^1(?=[A-Za-z_#])", lines[i]):
            out.append(lines[i]); i += 1; continue
        j = i + 1
        while j < len(lines) and re.match(rf"^{j-i+1}(?=[A-Za-z_#])", lines[j]):
            j += 1
        if j - i < 2:
            out.append(lines[i]); i += 1; continue
        out.extend(["", "```python"])
        for n in range(i, j):
            code = lines[n][len(str(n-i+1)):]
            code = code.replace("importnumpy", "import numpy").replace("importpandas", "import pandas")
            code = code.replace("fromscipyimportstats", "from scipy import stats")
            code = code.replace("fromsklearn.metricsimportconfusion_matrix", "from sklearn.metrics import confusion_matrix")
            code = code.replace("for_inrange", "for _ in range")
            code = code.replace("‑", "-")
            out.append(code)
        out.extend(["```", ""])
        i = j
    return "\n".join(out).rstrip() + "\n"


def rebuild_chapter_card(s: str) -> str:
    lines = s.splitlines()
    if "章節識別卡" not in lines:
        return s
    a = lines.index("章節識別卡")
    b = next((i for i in range(a + 1, len(lines)) if lines[i] == "學習目標"), None)
    if b is None:
        raise ValueError("chapter card has no learning-goal boundary")
    keys = ("官方代碼", "官方名稱", "官方備註", "所屬", "授證路線", "本版查核日",
            "對應來源", "先備知識", "建議時數", "本版題數", "備註")
    rows = []
    for line in lines[a + 1:b]:
        if not line.strip():
            continue
        key = next((k for k in keys if line.startswith(k + " ")), None)
        if not key:
            raise ValueError(f"unexpected chapter card row: {line}")
        rows.append(f"| {key} | {line[len(key):].strip().replace('|', '∣')} |")
    table = ["### 章節識別卡", "| 項目 | 內容 |", "| --- | --- |", *rows, "", "### 學習目標"]
    lines[a:b + 1] = table
    return "\n".join(lines).rstrip() + "\n"

def tidy_heading(m):
    a, b, c, d, title = m.groups()
    number = f"{a}.{b}.{c}" + (f".{d}" if d else "")
    depth = "#####" if d else "####"
    return f"{depth} {number} {title.strip()}"

def clean(path: Path):
    old = path.read_text(encoding="utf-8")
    s = old
    # The earlier copy called a future date an already-completed cutoff.
    s = re.sub(r"(?:資料截止日|查核日)\s*[：:]?\s*(?:中華民國\s*)?115\s*年?\s*10\s*月?\s*1\s*日?", f"本版查核日 {DATE}", s)
    s = re.sub(r"115[.．]10[.．]01(?=.{0,10}(?:查核|截止))", "115.09.24", s)
    s = s.replace("查核日中華民國 115 年 10 月 1 日", f"查核日 {DATE}")
    s = s.replace("查核日：中華民國 115年 10月 1日", f"查核日：{DATE}")
    s = s.replace("資料截止日：中華民國 115 年 10 月 1 日", f"本版查核日：{DATE}")
    s = s.replace("| 資料截止日 | 中華民國 115年 10月 1日 |", f"| 本版查核日 | {DATE} |")
    s = s.replace("| 資料截止日 | 中華民國 115 年 10 月 1 日 |", f"| 本版查核日 | {DATE} |")
    s = s.replace("| 內容凍結 | 115.11.01 |", f"| 本版校訂日 | {DATE} |")
    # The prior draft repeated the same guide citation three times in many
    # chapter cards; retain one exact page range and any separate errata ID.
    def source_line(m):
        line = m.group(0)
        guide = re.search(r"IPAS‑GUIDE‑L(?:21|22|23)（學習指引[^）]+）", line)
        if not guide:
            return line
        suffix = "、IPAS‑ERRATA‑MID" if "IPAS‑ERRATA‑MID" in line else ""
        return "對應來源 IPAS‑SCOPE‑11506、" + guide.group(0) + suffix
    s = re.sub(r"(?m)^對應來源 .*", source_line, s)
    key = f"{path.parts[-3]}/{path.name}"
    s = rebuild_recaps(s, key)
    if path.name.startswith("ch"):
        s = rebuild_numbered_code(s)
        s = rebuild_chapter_card(s)
    # A PDF line break can split a Chinese word inside a recovered table cell.
    s = "\n".join(
        re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", line)
        if line.startswith("| ") else line
        for line in s.splitlines()
    ).rstrip() + "\n"
    # Cover chapter cards contained manually assigned ratios with no segment data.
    s = re.sub(r"(?m)^層級分布\s+.*\n", "", s)
    # Remove duplicated literal text under a Markdown heading, caused by
    # lifting the original PDF's displayed heading into a Markdown heading.
    s = re.sub(r"(?m)^###\s+(\d+)\.(\d+)\s*\.(\d+)(?:\.(\d+))?\s*(.+)$", tidy_heading, s)
    lines = s.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)
        m = re.match(r"^#{2,5}\s+(.+)$", line)
        if m:
            heading = re.sub(r"\s+", "", m.group(1))
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.sub(r"\s+", "", lines[j]) == heading:
                i = j + 1
                continue
            chapter = re.match(r"^第\s*(\d+)章\s+(.+)$", m.group(1))
            if chapter and j + 1 < len(lines):
                marker = re.sub(r"\s+", "", lines[j])
                title = re.sub(r"\s+", "", lines[j+1])
                if marker == f"第{chapter.group(1)}章" and title == re.sub(r"\s+", "", chapter.group(2)):
                    i = j + 2
                    continue
        i += 1
    s = "\n".join(result).rstrip() + "\n"
    # Some chapter endnotes state outdated gaps that are in fact supplied.
    s = re.sub(r"(?m)^未解決資料缺口：學習指引頁碼；中級勘誤表完整條目。\s*$", "", s)
    if s != old:
        path.write_bytes(s.encode("utf-8"))
        return True
    return False

def main():
    changed=[]
    for vol in ('L21','L22','L23'):
        changed += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'book'/vol/'v0.3').rglob('*.md')) if clean(p)]
    print('updated', len(changed), 'Markdown files')
    for name in changed:
        print(name)

if __name__ == '__main__':
    main()
