import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from .executor import run_tests
DANGEROUS_CALLS = {"eval": 25, "exec": 25, "compile": 10, "__import__": 20, "open": 10, "input": 5}
DANGEROUS_ATTRS = {"system": 25, "popen": 25, "run": 15, "call": 15, "Popen": 25,
                   "loads": 20, "load": 20, "remove": 15, "rmtree": 25}
DANGEROUS_IMPORTS = {"os", "subprocess", "pickle", "socket", "shutil", "ctypes", "marshal"}

def extract_code(text: str) -> str:
    """Take the last fenced code block that defines a function; fall back to the raw text."""
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    for b in reversed(blocks):
        if "def " in b:
            return b.strip() + "\n"
    return (blocks[-1] if blocks else text).strip() + "\n"


def _complexity(tree) -> int:
    n = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.With, ast.Assert)):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
    return n


def quality_score(code: str) -> float:
    """0-100 heuristic: docstring 25, type hints 20, line length 15, low complexity 25, clean I/O 15."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0.0
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return 0.0
    score = 0.0
    score += 25 if all(ast.get_docstring(f) for f in funcs) else 0
    hinted = all(f.returns is not None and all(a.annotation for a in f.args.args) for f in funcs)
    score += 20 if hinted else 0
    lines = code.splitlines()
    long_lines = sum(1 for l in lines if len(l) > 88)
    score += 15 if long_lines == 0 else 7
    cx = _complexity(tree)
    score += 25 if cx <= 6 else 15 if cx <= 10 else 5
    uses_io = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("print", "input") for n in ast.walk(tree))
    score += 0 if uses_io else 15
    return score


def _bandit_issues(code: str) -> int | None:
    """Optional: count bandit findings if bandit is installed."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "snippet.py")
            open(p, "w").write(code)
            r = subprocess.run([sys.executable, "-m", "bandit", "-q", "-f", "json", p],
                               capture_output=True, text=True, timeout=20)
            return len(json.loads(r.stdout).get("results", []))
    except Exception:
        return None


def security_score(code: str) -> tuple[float, int]:
    """Return (score 0-100, issue_count). AST scan for risky constructs, plus bandit if available."""
    penalty, issues = 0, 0
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0.0, 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in DANGEROUS_CALLS:
                penalty += DANGEROUS_CALLS[f.id]; issues += 1
            elif isinstance(f, ast.Attribute) and f.attr in DANGEROUS_ATTRS:
                penalty += DANGEROUS_ATTRS[f.attr]; issues += 1
        elif isinstance(node, ast.Import):
            hit = [a.name for a in node.names if a.name.split(".")[0] in DANGEROUS_IMPORTS]
            penalty += 10 * len(hit); issues += len(hit)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in DANGEROUS_IMPORTS:
            penalty += 10; issues += 1
    b = _bandit_issues(code) if issues == 0 and os.getenv("USE_BANDIT", "1") == "1" else None
    if b:
        issues += b; penalty += 10 * b
    return float(max(0, 100 - penalty)), issues


def failure_report(run: dict) -> str:
    if run.get("error") and not run["results"]:
        return f"Error: {run['error']}"
    lines = []
    for r in run["results"]:
        if not r["passed"]:
            detail = r.get("error") or f"got {r.get('got')}, expected {r.get('expected')!r}"
            lines.append(f"- input {r['args']}: {detail}")
    return "\n".join(lines[:6]) or "All checks passed."


def evaluate(code: str, task: dict) -> dict:
    run = run_tests(code, task["function"], task["tests"])
    results = run["results"]
    total = len(task["tests"])
    passed = sum(1 for r in results if r["passed"])
    correctness = passed / total if total else 0.0
    sec, n_issues = security_score(code)
    return {
        "passed": passed, "total": total, "correctness": correctness,
        "solved": int(passed == total and run["executed"]),
        "exec_success": int(run["executed"] and run.get("error") is None),
        "quality": quality_score(code), "security": sec, "sec_issues": n_issues,
        "error": run.get("error"), "failure_report": failure_report(run),
    }
