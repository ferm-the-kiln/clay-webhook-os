"""Safe formula evaluator for compute columns.

Supports:
- Template interpolation: "Hello {{first_name}} from {{company}}"
- Functions: UPPER(col), LOWER(col), TRIM(col), CONCAT(a, " ", b), LEFT(col, n), RIGHT(col, n)
- Conditionals: IF(condition, then_value, else_value)

No eval() — uses regex-based parsing only.
"""

import re

from app.core.pipeline_runner import evaluate_condition

# Match {{column_name}} patterns
_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")

# Match FUNCTION(args) patterns
_FUNC_RE = re.compile(r"^(UPPER|LOWER|TRIM|CONCAT|LEFT|RIGHT)\((.+)\)$", re.IGNORECASE)

# Match IF(condition, then, else) — top-level only
_IF_RE = re.compile(r"^IF\((.+)\)$", re.IGNORECASE)


def evaluate_formula(formula: str, row: dict) -> str:
    """Evaluate a formula against a row and return the string result."""
    formula = formula.strip()

    # Template mode: contains {{col}} patterns
    if _TEMPLATE_RE.search(formula):
        return _TEMPLATE_RE.sub(lambda m: str(row.get(m.group(1), "")), formula)

    # IF mode
    if_match = _IF_RE.match(formula)
    if if_match:
        return _evaluate_if(if_match.group(1), row)

    # Function mode
    func_match = _FUNC_RE.match(formula)
    if func_match:
        func_name = func_match.group(1).upper()
        args_str = func_match.group(2)
        return _evaluate_function(func_name, args_str, row)

    # Plain column reference
    if formula in row:
        return str(row[formula])

    # Return as-is (literal string)
    return formula


def _evaluate_function(func_name: str, args_str: str, row: dict) -> str:
    """Evaluate a function call."""
    args = _split_args(args_str)

    if func_name == "UPPER":
        val = _resolve_value(args[0], row) if args else ""
        return val.upper()

    if func_name == "LOWER":
        val = _resolve_value(args[0], row) if args else ""
        return val.lower()

    if func_name == "TRIM":
        val = _resolve_value(args[0], row) if args else ""
        return val.strip()

    if func_name == "CONCAT":
        return "".join(_resolve_value(a, row) for a in args)

    if func_name == "LEFT":
        if len(args) >= 2:
            val = _resolve_value(args[0], row)
            try:
                n = int(args[1].strip())
            except ValueError:
                n = 0
            return val[:n]
        return ""

    if func_name == "RIGHT":
        if len(args) >= 2:
            val = _resolve_value(args[0], row)
            try:
                n = int(args[1].strip())
            except ValueError:
                n = 0
            return val[-n:] if n > 0 else ""
        return ""

    return ""


def _evaluate_if(inner: str, row: dict) -> str:
    """Parse IF(condition, then_value, else_value) and evaluate."""
    parts = _split_args(inner)
    if len(parts) < 3:
        return ""

    condition = parts[0].strip()
    then_val = parts[1].strip()
    else_val = parts[2].strip()

    if evaluate_condition(condition, row):
        return _resolve_value(then_val, row)
    return _resolve_value(else_val, row)


def _resolve_value(token: str, row: dict) -> str:
    """Resolve a token: strip quotes for literals, look up in row for column refs."""
    token = token.strip()

    # Quoted string literal
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]

    # Column reference
    if token in row:
        return str(row[token])

    # Return as literal
    return token


def _split_args(args_str: str) -> list[str]:
    """Split function arguments respecting quoted strings and nested parens."""
    args: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    quote_char = ""

    for ch in args_str:
        if in_quote:
            current.append(ch)
            if ch == quote_char:
                in_quote = False
        elif ch in ('"', "'"):
            in_quote = True
            quote_char = ch
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        args.append("".join(current).strip())

    return args
