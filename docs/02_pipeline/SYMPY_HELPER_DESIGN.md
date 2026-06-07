# src/sympy_helper.py 設計書

数学者「関孝和」回向けに導入された SymPy ラッパーモジュール。
パイプラインの **B (Manim 前の数式生成)** と **D (企画段階の事前計算)** をサポートする。

---

## 設計方針

- **薄いラッパーに徹する**。SymPyの機能を直接使えばよい場合は関数化しない
- **LaTeX文字列生成に特化**。Manimテンプレートに渡す文字列を作るのが主用途
- **純粋関数で副作用なし**（将来 QA ステップから呼ぶ想定）
- **型安全**: 戻り値は基本的に `str` または `dict[str, str]`
- **依存**: `sympy` のみ（`pip install sympy` でvenv完結）

---

## 前提：SymPy導入

```bash
venv\Scripts\activate
pip install sympy
```

`requirements.txt` があれば `sympy>=1.12` を追加。
なければ `pip freeze` で確認。

---

## モジュール構造

### ファイル: `src/sympy_helper.py`

### セクション構成
1. **行列式ユーティリティ** (determinant_*)
2. **ベルヌーイ数ユーティリティ** (bernoulli_*)
3. **多項式展開ユーティリティ** (poly_*)
4. **LaTeX整形ユーティリティ** (format_*)

---

## API仕様

### 1. 行列式ユーティリティ

```python
def determinant_value(matrix: list[list[int]]) -> int | Rational:
    """
    行列の行列式の正確な値を返す。

    Args:
        matrix: 2次元リスト（整数または有理数）

    Returns:
        行列式の値（整数またはsympy.Rational）

    Example:
        >>> determinant_value([[1,2,3],[4,5,6],[7,8,10]])
        -3
    """


def determinant_latex(matrix: list[list[int]], expanded: bool = False) -> str:
    """
    行列式のLaTeX文字列を返す。

    Args:
        matrix: 2次元リスト
        expanded: True なら展開式（aei + bfg + ... - ceg - ...）形式、
                  False なら行列式記号 |M| 形式

    Returns:
        LaTeX文字列（Manim MathTex に渡せる形式）

    Example:
        >>> determinant_latex([[1,2],[3,4]], expanded=True)
        '1 \\cdot 4 - 2 \\cdot 3'
    """


def determinant_sarrus_terms(matrix: list[list[int]]) -> dict:
    """
    3×3行列式のサラス則による6項展開を辞書で返す。
    Manimで対角線ごとに色分け表示する用途。

    Args:
        matrix: 3×3の2次元リスト

    Returns:
        {
            "positive": [(符号, 項のLaTeX, 値), ...],  # 正方向3項
            "negative": [(符号, 項のLaTeX, 値), ...],  # 負方向3項
            "total": int,  # 行列式の値
        }

    Raises:
        ValueError: 3×3以外の場合

    Example:
        >>> determinant_sarrus_terms([[1,2,3],[4,5,6],[7,8,10]])
        {
            "positive": [("+", "1 \\cdot 5 \\cdot 10", 50), ...],
            "negative": [("-", "3 \\cdot 5 \\cdot 7", 105), ...],
            "total": -3
        }
    """
```

### 2. ベルヌーイ数ユーティリティ

```python
def bernoulli_numbers(n: int) -> list[Rational]:
    """
    B_0 から B_n までのベルヌーイ数列を返す（有理数）。

    Args:
        n: 最大インデックス

    Returns:
        [B_0, B_1, ..., B_n] の有理数リスト

    Note:
        B_1 の符号は慣習により +1/2 または -1/2 の2通りある。
        SymPyのデフォルトは -1/2（関孝和の時代の定式化と同じ）。

    Example:
        >>> bernoulli_numbers(6)
        [1, -1/2, 1/6, 0, -1/30, 0, 1/42]
    """


def bernoulli_latex_table(n: int) -> str:
    """
    ベルヌーイ数列のLaTeX表組み文字列を返す。
    Manim formula_display で表示する用途。

    Args:
        n: 最大インデックス

    Returns:
        LaTeX配列形式の文字列

    Example:
        >>> bernoulli_latex_table(4)
        'B_0 = 1, \\quad B_1 = -\\frac{1}{2}, \\quad B_2 = \\frac{1}{6}, ...'
    """


def sum_of_powers_formula(p: int) -> str:
    """
    Σk^p (k=1..n) の閉形式公式（ベルヌーイ数を用いた表現）のLaTeX文字列。

    Args:
        p: 冪指数 (1, 2, 3, ...)

    Returns:
        LaTeX文字列

    Example:
        >>> sum_of_powers_formula(2)
        '\\sum_{k=1}^{n} k^2 = \\frac{n(n+1)(2n+1)}{6}'
    """
```

### 3. 多項式展開ユーティリティ

```python
def expand_polynomial_latex(expr_str: str) -> str:
    """
    多項式を展開してLaTeXで返す。

    Args:
        expr_str: SymPy式文字列（例: "(x+1)*(x+2)*(x-3)"）

    Returns:
        展開後のLaTeX

    Example:
        >>> expand_polynomial_latex("(x+1)*(x+2)")
        'x^{2} + 3 x + 2'
    """
```

### 4. LaTeX整形ユーティリティ

```python
def matrix_to_latex(matrix: list[list[int]]) -> str:
    """
    行列をLaTeX pmatrix / bmatrix 形式に変換。

    Args:
        matrix: 2次元リスト

    Returns:
        LaTeX文字列

    Example:
        >>> matrix_to_latex([[1,2],[3,4]])
        '\\begin{pmatrix}1 & 2\\\\3 & 4\\end{pmatrix}'
    """


def fraction_to_latex(num: int, den: int) -> str:
    """
    分数を \\frac{num}{den} 形式に変換（既約化）。
    """
```

---

## 使用例（パイプラインでの呼び出し）

### 例1: episode_config.json 作成時（事前計算）

```python
from src.sympy_helper import (
    bernoulli_numbers, determinant_value, determinant_sarrus_terms,
)

# ベルヌーイ数 B_0〜B_12 を括要算法に合わせて計算
print(bernoulli_numbers(12))
# → [1, -1/2, 1/6, 0, -1/30, 0, 1/42, 0, -1/30, 0, 5/66, 0, -691/2730]

# 3×3行列式の検証
M = [[1,2,3],[4,5,6],[7,8,10]]
print(determinant_value(M))  # -3
print(determinant_sarrus_terms(M))  # 展開項と符号の辞書
```

### 例2: Manimテンプレート `determinant_expansion.py` 内で呼び出し

```python
# determinant_expansion.py の _build_seki_method() 内
from sympy_helper import determinant_sarrus_terms, matrix_to_latex

MATRIX = [[1,2,3],[4,5,6],[7,8,10]]
terms = determinant_sarrus_terms(MATRIX)
matrix_tex = matrix_to_latex(MATRIX)

# Manim MathTex に渡す
self.add(MathTex(matrix_tex))
for sign, term_tex, value in terms["positive"]:
    self.add(MathTex(f"+ {term_tex}"))
# ...
```

### 例3: 将来のQA統合（Gate 1拡張）

```python
# qa_checker.py の数式検証エージェントから
from src.sympy_helper import determinant_value

def check_determinant_claim(scene_text, matrix, claimed_value):
    actual = determinant_value(matrix)
    if actual != claimed_value:
        return {"severity": "critical", "msg": f"行列式値の不一致: {claimed_value} vs {actual}"}
    return None
```

---

## テスト方針

### 単体テスト（`tests/test_sympy_helper.py` 新規作成を推奨）

```python
def test_determinant_value_2x2():
    assert determinant_value([[1,2],[3,4]]) == -2

def test_determinant_value_3x3():
    assert determinant_value([[1,2,3],[4,5,6],[7,8,10]]) == -3

def test_bernoulli_numbers_known_values():
    bs = bernoulli_numbers(12)
    assert bs[0] == 1
    assert bs[1] == Rational(-1, 2)
    assert bs[2] == Rational(1, 6)
    assert bs[4] == Rational(-1, 30)
    assert bs[12] == Rational(-691, 2730)  # 有名な数

def test_sarrus_sign():
    terms = determinant_sarrus_terms([[1,2,3],[4,5,6],[7,8,10]])
    assert len(terms["positive"]) == 3
    assert len(terms["negative"]) == 3
    assert terms["total"] == -3
```

関孝和回の実装時に動作確認しつつテストを書く。

---

## 実装見積もり

| 項目 | 行数 |
|---|---|
| `determinant_*` 3関数 | ~50行 |
| `bernoulli_*` 3関数 | ~40行 |
| `expand_polynomial_latex` | ~10行 |
| `matrix_to_latex`, `fraction_to_latex` | ~30行 |
| docstring + コメント | ~30行 |
| **合計** | **約160行** |

---

## 将来拡張（今回はスコープ外）

- 楕円曲線の点加法可視化（ガウス回向け）
- 連分数展開（ラマヌジャン回の再ビルド時）
- ガロア群の生成元表示（ガロア回の再ビルド時）
- 差分方程式・漸化式のLaTeX生成
- 記号QAエージェント（`qa_checker.py` と統合）

---

## 導入手順（実装セッションで）

1. `pip install sympy` （venv内）
2. `src/sympy_helper.py` 作成
3. テスト作成 (オプション)
4. Manim 実装時に `from sympy_helper import ...` で呼び出し
