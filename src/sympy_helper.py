"""
sympy_helper.py — Thin SymPy wrapper for 数学史記

Provides LaTeX string generation utilities backed by SymPy for accurate
math content in Manim templates and episode_config pre-computation.

Introduced for the 関孝和 episode for:
  - Determinant values / Sarrus expansion (『解伏題之法』1683)
  - Bernoulli numbers (『括要算法』1712)
  - Σk^p closed-form formulas
  - Polynomial expansion / matrix LaTeX

Design: see docs/SYMPY_HELPER_DESIGN.md
"""

from __future__ import annotations

from sympy import (
    Matrix,
    Rational,
    bernoulli,
    expand,
    latex,
    summation,
    symbols,
    sympify,
)

Number = int | Rational


# ---------------------------------------------------------------------------
# 1. Determinant utilities
# ---------------------------------------------------------------------------


def determinant_value(matrix: list[list[Number]]) -> Number:
    """Return the exact determinant value of the given matrix.

    Example:
        >>> determinant_value([[1,2,3],[4,5,6],[7,8,10]])
        -3
    """
    M = Matrix(matrix)
    det = M.det()
    if det.is_Integer:
        return int(det)
    return det


def determinant_latex(matrix: list[list[Number]], expanded: bool = False) -> str:
    """Return LaTeX for a determinant.

    Args:
        matrix: 2D list.
        expanded: If True, return the expanded term-by-term form
                  (e.g. "a \\cdot d - b \\cdot c"). Otherwise return
                  "\\det \\begin{pmatrix}...\\end{pmatrix}".
    """
    M = Matrix(matrix)
    n = M.shape[0]
    if not expanded:
        return r"\det " + matrix_to_latex(matrix)

    if n == 2:
        a, b = matrix[0]
        c, d = matrix[1]
        return f"{a} \\cdot {d} - {b} \\cdot {c}"
    if n == 3:
        terms = determinant_sarrus_terms(matrix)
        pos = " + ".join(t[1] for t in terms["positive"])
        neg = " - ".join(t[1] for t in terms["negative"])
        return f"{pos} - {neg}"
    # Fallback: generic symbolic expansion
    return latex(M.det())


def determinant_sarrus_terms(matrix: list[list[Number]]) -> dict:
    """Return the 6 Sarrus-rule terms for a 3x3 determinant.

    Returns:
        {
            "positive": [(sign_str, term_latex, term_value), ...],
            "negative": [(sign_str, term_latex, term_value), ...],
            "total": int | Rational
        }

    Raises:
        ValueError: if matrix is not 3x3.

    Example:
        >>> determinant_sarrus_terms([[1,2,3],[4,5,6],[7,8,10]])["total"]
        -3
    """
    if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
        raise ValueError("determinant_sarrus_terms requires a 3x3 matrix")

    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]

    positive = [
        ("+", f"{a} \\cdot {e} \\cdot {i}", a * e * i),
        ("+", f"{b} \\cdot {f} \\cdot {g}", b * f * g),
        ("+", f"{c} \\cdot {d} \\cdot {h}", c * d * h),
    ]
    negative = [
        ("-", f"{c} \\cdot {e} \\cdot {g}", c * e * g),
        ("-", f"{a} \\cdot {f} \\cdot {h}", a * f * h),
        ("-", f"{b} \\cdot {d} \\cdot {i}", b * d * i),
    ]
    total = sum(t[2] for t in positive) - sum(t[2] for t in negative)
    if hasattr(total, "is_Integer") and total.is_Integer:
        total = int(total)
    return {"positive": positive, "negative": negative, "total": total}


# ---------------------------------------------------------------------------
# 2. Bernoulli number utilities
# ---------------------------------------------------------------------------


def bernoulli_numbers(n: int) -> list[Rational]:
    """Return B_0, B_1, ..., B_n as a list of sympy Rationals.

    Note:
        SymPy (>=1.12) uses the convention B_1 = +1/2 (the "Bernoulli+"
        convention). This matches the original Jakob Bernoulli (1713)
        and 関孝和『括要算法』(1712) formulations, which used
        Σk^p from 0 to n-1 (or 1 to n with boundary adjustments that
        yield +1/2). Historical accuracy is preserved.

    Example:
        >>> bernoulli_numbers(6)
        [1, 1/2, 1/6, 0, -1/30, 0, 1/42]
    """
    return [bernoulli(k) for k in range(n + 1)]


def bernoulli_latex_table(n: int) -> str:
    """Return a LaTeX string listing B_0..B_n separated by \\quad.

    Example:
        >>> bernoulli_latex_table(4)
        'B_0 = 1,\\quad B_1 = \\frac{1}{2},\\quad B_2 = \\frac{1}{6},\\quad B_3 = 0,\\quad B_4 = -\\frac{1}{30}'
    """
    parts = []
    for k in range(n + 1):
        parts.append(f"B_{{{k}}} = {latex(bernoulli(k))}")
    return ",\\quad ".join(parts)


def sum_of_powers_formula(p: int) -> str:
    """Return the closed-form LaTeX for Σ_{k=1}^{n} k^p.

    Example:
        >>> sum_of_powers_formula(2)
        '\\sum_{k=1}^{n} k^{2} = \\frac{n \\left(n + 1\\right) \\left(2 n + 1\\right)}{6}'
    """
    if p < 0:
        raise ValueError("p must be >= 0")
    n = symbols("n")
    k = symbols("k")
    expr = summation(k**p, (k, 1, n))
    expr_simplified = expr.factor()
    lhs = f"\\sum_{{k=1}}^{{n}} k^{{{p}}}"
    return f"{lhs} = {latex(expr_simplified)}"


# ---------------------------------------------------------------------------
# 3. Polynomial expansion
# ---------------------------------------------------------------------------


def expand_polynomial_latex(expr_str: str) -> str:
    """Expand a polynomial string and return its LaTeX form.

    Example:
        >>> expand_polynomial_latex("(x+1)*(x+2)")
        'x^{2} + 3 x + 2'
    """
    expr = sympify(expr_str)
    return latex(expand(expr))


# ---------------------------------------------------------------------------
# 4. LaTeX formatting utilities
# ---------------------------------------------------------------------------


def matrix_to_latex(matrix: list[list[Number]], env: str = "pmatrix") -> str:
    """Convert a 2D list to a LaTeX matrix string.

    Args:
        env: LaTeX matrix environment ("pmatrix", "bmatrix", "vmatrix").

    Example:
        >>> matrix_to_latex([[1,2],[3,4]])
        '\\begin{pmatrix}1 & 2\\\\3 & 4\\end{pmatrix}'
    """
    rows = ["&".join(str(x) for x in row) for row in matrix]
    body = "\\\\".join(rows)
    return f"\\begin{{{env}}}{body}\\end{{{env}}}"


def fraction_to_latex(num: int, den: int) -> str:
    """Return \\frac{num}{den} in reduced form.

    Example:
        >>> fraction_to_latex(4, 6)
        '\\frac{2}{3}'
    """
    r = Rational(num, den)
    return latex(r)
