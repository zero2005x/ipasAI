#!/usr/bin/env python3
"""Execute and test Python code blocks in textbook markdown files.
"""
import ast
import glob
import io
import sys
import textwrap
import unittest.mock as mock

def get_code_blocks():
    bt = chr(96) * 3
    blocks = []
    for f in sorted(glob.glob('book/*/v0.3/ch*.md') + glob.glob('shared/book/**/*.md')):
        lines = open(f, encoding='utf-8').read().splitlines()
        in_py = False
        cur = []
        start_no = 0
        for no, line in enumerate(lines, 1):
            if line.strip().startswith(bt + 'python'):
                in_py = True
                cur = []
                start_no = no
            elif in_py and line.strip() == bt:
                in_py = False
                blocks.append((f, start_no, textwrap.dedent('\n'.join(cur))))
            elif in_py:
                cur.append(line)
    return blocks

def make_env():
    import numpy as np
    import pandas as pd
    
    np.random.seed(42)
    n = 100
    p = 5
    X = np.random.randn(n, p)
    y = np.random.randint(0, 2, size=n)
    X_train, X_test = X[:80], X[80:]
    y_train, y_test = y[:80], y[80:]
    
    df = pd.DataFrame({
        'x': [1.0, 2.0, 3.0, 4.0, 5.0] * 20,
        'sales': [10.0, 20.0, 30.0, 40.0, 50.0] * 20,
        'region': ['North', 'South', 'North', 'South', 'North'] * 20,
        'amount': [100.0, 200.0, 150.0, 300.0, 250.0] * 20,
        'store': ['A', 'B', 'A', 'B', 'A'] * 20,
        'price': [15.0, 25.0, 35.0, 45.0, 55.0] * 20,
        'quantity': [2, 4, 1, 5, 3] * 20,
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'] * 20,
        'national_id': ['A123', 'B234', 'C345', 'D456', 'E567'] * 20,
        'phone': ['0912', '0923', '0934', '0945', '0956'] * 20,
        'birth_date': pd.date_range('1990-01-01', periods=100, freq='D'),
        'gender': ['M', 'F', 'M', 'F', 'M'] * 20,
        'zipcode': ['10001', '10002', '10003', '10004', '10005'] * 20,
    })
    sales = df.copy()
    orders = df.copy()
    
    # Mock plt to avoid GUI windows popping up
    plt_mock = mock.MagicMock()
    ax_mock = mock.MagicMock()
    
    # Mocks for ML
    class DummyModel:
        def __init__(self, *args, **kwargs):
            self.classes_ = np.array([0, 1])
            self.feature_importances_ = np.ones(5) / 5
            self.labels_ = np.zeros(100)
            self.best_score_ = 0.85
        def fit(self, *args, **kwargs): return self
        def fit_transform(self, X, *args, **kwargs): return X
        def transform(self, X, *args, **kwargs): return X
        def fit_resample(self, X, y, *args, **kwargs): return X, y
        def predict(self, X): return np.zeros(len(X))
        def predict_proba(self, X): return np.column_stack([np.ones(len(X))*0.4, np.ones(len(X))*0.6])
        def add(self, *args, **kwargs): pass
        def compile(self, *args, **kwargs): pass

    env = {
        'np': np,
        'numpy': np,
        'pd': pd,
        'pandas': pd,
        'X': X,
        'y': y,
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'X_tr': X_train,
        'X_te': X_test,
        'y_tr': y_train,
        'y_te': y_test,
        'x_tr': X_train,
        'x_te': X_test,
        'X_scaled': X,
        'X_res': X,
        'y_res': y,
        'y_true': y,
        'y_pred': y,
        'x': np.array([1, 2, 3, 4, 5]),
        'df': df,
        'sales': sales,
        'orders': orders,
        'plt': plt_mock,
        'ax': ax_mock,
        'branches': ['B1', 'B2'],
        'scores': [96.0, 97.0],
        'epochs': range(10),
        'train_loss': [0.5]*10,
        'val_loss': [0.6]*10,
        'loader': [(X[:10], y[:10])],
        'optimizer': DummyModel(),
        'model': DummyModel(),
        'PCA': DummyModel,
        'StandardScaler': DummyModel,
        'KMeans': DummyModel,
        'DBSCAN': DummyModel,
        'SMOTE': DummyModel,
        'RandomForestClassifier': DummyModel,
        'GradientBoostingClassifier': DummyModel,
        'GridSearchCV': DummyModel,
        'Adam': DummyModel,
        'Dense': DummyModel,
        'Conv2D': DummyModel,
        'param_grid': {'n_estimators': [10, 50]},
        'train_test_split': lambda *args, **kwargs: (X_train, X_test, y_train, y_test) if len(args)==2 else (X_train, X_test),
        'cross_val_score': lambda *args, **kwargs: np.array([0.8, 0.82, 0.81, 0.83, 0.79]),
        'roc_auc_score': lambda y_true, y_score: 0.85,
        'confusion_matrix': lambda y_true, y_pred, labels=None: np.array([[50, 5], [10, 35]]),
        'matplotlib': mock.MagicMock(),
        'sns': mock.MagicMock(),
    }
    return env

def main():
    blocks = get_code_blocks()
    print(f"Testing {len(blocks)} code blocks across the books...")
    
    syntax_errs = []
    runtime_errs = []
    passed = 0
    
    for f, no, code in blocks:
        # 1. Syntax check
        try:
            ast.parse(code)
        except Exception as e:
            syntax_errs.append((f, no, str(e), code))
            continue
            
        # 2. Runtime check in mock environment
        env = make_env()
        try:
            exec(code, env)
            passed += 1
        except Exception as e:
            # Check if it's missing imports like torch/pyspark/scipy that might not be installed,
            # or if it's an intended error question (e.g. "下列程式會發生什麼錯誤")
            runtime_errs.append((f, no, type(e).__name__, str(e), code[:80]))
            
    print(f"Results: {passed} passed directly, {len(syntax_errs)} syntax errors, {len(runtime_errs)} runtime exceptions.")
    
    if syntax_errs:
        print("\n--- SYNTAX ERRORS ---")
        for f, no, err, code in syntax_errs:
            print(f"[{f}:{no}] {err}\n{code[:100]}\n")
            
    if runtime_errs:
        print("\n--- RUNTIME EXCEPTIONS (Review for legitimate snippets / mocks) ---")
        for f, no, err_type, err_msg, snippet in runtime_errs:
            print(f"[{f}:{no}] {err_type}: {err_msg} | snippet: {snippet.strip().replace(chr(10), ' ')}")

if __name__ == '__main__':
    main()
