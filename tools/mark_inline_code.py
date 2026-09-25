#!/usr/bin/env python3
"""Mark inline code tokens in Markdown files for iPAS textbooks.

Usage:
    python tools/mark_inline_code.py scan
    python tools/mark_inline_code.py apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.check_text_integrity import BASELINE_FILE, find_target_files, normalize

CANDIDATES_FILE = ROOT / "tmp" / "inline_code_candidates.tsv"

KNOWN_APIS = [
    "StandardScaler", "MinMaxScaler", "RobustScaler", "OneHotEncoder", "LabelEncoder",
    "OrdinalEncoder", "SimpleImputer", "KNNImputer", "KMeans", "DBSCAN",
    "AgglomerativeClustering", "LinearRegression", "LogisticRegression", "Ridge",
    "Lasso", "ElasticNet", "DecisionTreeClassifier", "DecisionTreeRegressor",
    "RandomForestClassifier", "RandomForestRegressor", "GradientBoostingClassifier",
    "GradientBoostingRegressor", "SVC", "SVR", "GaussianNB", "MultinomialNB",
    "KNeighborsClassifier", "GridSearchCV", "RandomizedSearchCV", "StratifiedKFold",
    "KFold", "TimeSeriesSplit", "GroupKFold", "Pipeline", "make_pipeline",
    "ColumnTransformer", "make_column_transformer", "SMOTE", "train_test_split",
    "cross_val_score", "cross_validate", "confusion_matrix", "classification_report",
    "roc_auc_score", "roc_curve", "precision_recall_curve", "f1_score", "accuracy_score",
    "precision_score", "recall_score", "mean_squared_error", "mean_absolute_error",
    "r2_score", "silhouette_score", "fit_transform",
]

# Words / tokens to NEVER mark as code (general acronyms or concepts)
FORBIDDEN_TOKENS = {
    "BERT", "GPT", "T5", "ROC", "AUC", "PR", "VAE", "GAN", "CNN", "RNN",
    "LSTM", "GRU", "NLP", "AI", "API", "ML", "DL", "LLM", "RAG", "LoRA",
    "QLoRA", "RLHF", "DPO", "PPO", "KS", "PSI", "IoU", "mAP", "NER",
    "TF-IDF", "One-Hot", "BLEU", "ROUGE", "WER", "CER", "TP", "FP", "TN", "FN",
    "ACID", "JOIN", "MES", "POC", "IT", "OT", "CI/CD", "SLA", "GPU", "CPU",
    "TPU", "NPU", "RAM", "SSD", "S3", "SQL", "NoSQL", "PCA", "TSNE", "SVD",
    "DATA_ANALYSIS", "AI_PLANNER", "SYS_ARCH",
}

# Known Python parameter names
PYTHON_PARAM_NAMES = {
    "inplace", "ddof", "how", "axis", "subset", "alpha", "cv", "scoring",
    "random_state", "n_clusters", "test_size", "shuffle", "max_depth",
    "learning_rate", "n_estimators", "max_iter", "tol", "kernel", "gamma",
    "C", "penalty", "solver", "activation", "padding", "strides", "filters",
    "pool_size", "drop", "dropna", "keep", "ascending", "columns", "index",
    "by", "on", "dtype", "usecols", "parse_dates", "sep", "delimiter",
    "skiprows", "header", "method", "fill_value", "q", "bins", "labels",
    "n_components", "min_samples", "eps", "metric", "n_jobs", "weights",
    "criterion", "min_samples_split", "min_samples_leaf", "subsample",
}

# Protected blocks: backticks `...`, template syntax {{...}}, math formulas $...$
PROTECTED_PATTERN = re.compile(r"(\{\{[^}]+\}\}|\$[^$]+\$|`[^`]+`)")

# Regex components
# 1. Underscore identifier: lowercase identifier with underscore or standard ML split
RE_UNDERSCORE = re.compile(
    r"(?<![a-zA-Z0-9_`])([a-z][a-z0-9]*_[a-z0-9_]*|[Xy]_(?:train|test|scaled|res|pred|true|tr|te|score))(?![a-zA-Z0-9_`])"
)

# 2. Function calls with parentheses: e.g. drop_duplicates(), df['x'].mean()
RE_BRACKET_CALL = re.compile(r"(?<!`)(df\[['\"][^'\"]+['\"]\]\.[a-zA-Z_][a-zA-Z0-9_]*(?:\(\))?)(?!`)")
RE_CALL = re.compile(r"(?<![a-zA-Z0-9_`])([a-zA-Z_][a-zA-Z0-9_]*\(\))(?!`)")

# 3. Dot method chains: e.g. df.dropna, gs.best_score_, pd.read_csv (NOT stats.!)
RE_DOT = re.compile(
    r"(?<![a-zA-Z0-9_`])((?:df|pd|np|plt|sns|model|clf|pipe|pipeline|gs|scaler|pca|km|res)\.[a-zA-Z_][a-zA-Z0-9_]*)(?![a-zA-Z0-9_`])"
)

# 4. Param = Value
RE_PARAM = re.compile(
    r"(?<![a-zA-Z0-9_`])([a-zA-Z_][a-zA-Z0-9_]*\s*=\s*(?:True|False|None|\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\"))(?![a-zA-Z0-9_`])"
)

# 5. Known APIs
RE_APIS = re.compile(
    r"(?<![a-zA-Z0-9_`])(" + "|".join(re.escape(api) for api in sorted(KNOWN_APIS, key=len, reverse=True)) + r")(?![a-zA-Z0-9_`])"
)


def is_table_header(line: str, next_line: str | None) -> bool:
    """True if line is a table header row (followed by separator row)."""
    if "|" in line and next_line and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", next_line):
        return True
    return False


def find_spans_in_text(text: str) -> list[tuple[int, int, str, str]]:
    """Find all candidate spans [start, end, token, rule] in raw text outside of backticks."""
    spans: list[tuple[int, int, str, str]] = []

    # Priority 1: bracket calls (most specific)
    for m in RE_BRACKET_CALL.finditer(text):
        spans.append((m.start(1), m.end(1), m.group(1), "bracket_call"))

    # Priority 2: param = val (only valid Python parameter names)
    for m in RE_PARAM.finditer(text):
        full_match = m.group(1)
        param_name = full_match.split("=")[0].strip()
        if param_name in PYTHON_PARAM_NAMES:
            spans.append((m.start(1), m.end(1), full_match, "param_val"))

    # Priority 3: dot chains
    for m in RE_DOT.finditer(text):
        tok = m.group(1)
        spans.append((m.start(1), m.end(1), tok, "dot_chain"))

    # Priority 4: calls ()
    for m in RE_CALL.finditer(text):
        tok = m.group(1)
        name = tok[:-2]
        if name not in FORBIDDEN_TOKENS and not re.match(r"^\d+$", name):
            spans.append((m.start(1), m.end(1), tok, "call"))

    # Priority 5: underscore identifiers
    for m in RE_UNDERSCORE.finditer(text):
        tok = m.group(1)
        if tok not in FORBIDDEN_TOKENS:
            spans.append((m.start(1), m.end(1), tok, "underscore"))

    # Priority 6: known APIs
    for m in RE_APIS.finditer(text):
        tok = m.group(1)
        if tok not in FORBIDDEN_TOKENS:
            spans.append((m.start(1), m.end(1), tok, "known_api"))

    # Sort spans by start, and resolve overlaps by preferring longer / earlier spans
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    non_overlapping: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, tok, rule in spans:
        if start >= last_end:
            non_overlapping.append((start, end, tok, rule))
            last_end = end

    return non_overlapping


def mark_line(line: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Mark candidates in line with backticks. Returns (new_line, [(rule, token, snippet)])."""
    # Split line by backticks, templates, and math formulas:
    parts = PROTECTED_PATTERN.split(line)
    new_parts: list[str] = []
    records: list[tuple[str, str, str]] = []

    for i, part in enumerate(parts):
        # Odd indices are protected (backticks `...`, templates {{...}}, math $...$)
        if i % 2 == 1:
            new_parts.append(part)
        else:
            spans = find_spans_in_text(part)
            if not spans:
                new_parts.append(part)
                continue

            last_pos = 0
            res = []
            for start, end, tok, rule in spans:
                res.append(part[last_pos:start])
                res.append(f"`{tok}`")
                ctx_start = max(0, start - 20)
                ctx_end = min(len(part), end + 20)
                snippet = part[ctx_start:ctx_end].replace("\t", " ")
                records.append((rule, tok, snippet))
                last_pos = end
            res.append(part[last_pos:])
            new_parts.append("".join(res))

    return "".join(new_parts), records


def process_file(path: Path, apply: bool = False) -> tuple[str, list[tuple[int, str, str, str]]]:
    """Process a single markdown file, returning (new_text, candidate_records)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_code = False
    new_lines: list[str] = []
    all_records: list[tuple[int, str, str, str]] = []

    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            new_lines.append(line)
            continue
        if in_code:
            new_lines.append(line)
            continue

        s = line.strip()
        # Skip headings, html comments, callout fences, table separators
        if not s or s.startswith(("#", "<!--", ":::")):
            new_lines.append(line)
            continue
        if re.match(r"^\|?[\s:\-|]+\|[\s:\-|]*$", s):
            new_lines.append(line)
            continue

        # Skip table header row
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None
        if is_table_header(line, next_line):
            new_lines.append(line)
            continue

        marked_line, recs = mark_line(line)
        new_lines.append(marked_line if apply else line)
        for rule, tok, snippet in recs:
            all_records.append((idx + 1, rule, tok, snippet))

    new_text = "\n".join(new_lines)
    if text.endswith("\n"):
        new_text += "\n"
    return new_text, all_records


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Mark inline code in book Markdown files.")
    parser.add_argument("mode", choices=["scan", "apply"], help="Scan to TSV or apply changes.")
    args = parser.parse_args()

    files = find_target_files()
    total_candidates = 0
    all_candidates: list[tuple[str, int, str, str, str]] = []

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        _, recs = process_file(p, apply=False)
        for ln, rule, tok, snippet in recs:
            all_candidates.append((rel, ln, rule, tok, snippet))
        total_candidates += len(recs)

    if args.mode == "scan":
        CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            f.write("filename\tline_no\trule\ttoken\tsnippet\n")
            for rel, ln, rule, tok, snippet in all_candidates:
                f.write(f"{rel}\t{ln}\t{rule}\t{tok}\t{snippet}\n")

        print(f"Scanned {len(files)} files.")
        print(f"Total inline code candidates: {total_candidates}")
        print(f"Output saved to: {CANDIDATES_FILE.relative_to(ROOT)}")

        by_rule: dict[str, int] = {}
        for _, _, rule, _, _ in all_candidates:
            by_rule[rule] = by_rule.get(rule, 0) + 1
        print("Candidate breakdown by rule:")
        for r, c in sorted(by_rule.items(), key=lambda x: -x[1]):
            print(f"  - {r}: {c}")

    elif args.mode == "apply":
        with open(BASELINE_FILE, encoding="utf-8") as f:
            baseline = json.load(f)

        all_pass = True
        for p in files:
            new_text, _ = process_file(p, apply=True)
            norm_new = normalize(new_text)
            rel = p.relative_to(ROOT).as_posix()
            norm_base = baseline[rel]["normalized"]
            if norm_new != norm_base:
                print(f"[FAIL INTEGRITY] {rel}")
                all_pass = False
            else:
                p.write_text(new_text, encoding="utf-8")

        print(f"Applied inline code markings to {len(files)} files.")
        print(f"Text integrity check: {'ALL PASS' if all_pass else 'FAILED'}")


if __name__ == "__main__":
    main()
