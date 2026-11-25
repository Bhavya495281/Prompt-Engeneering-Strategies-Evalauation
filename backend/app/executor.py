import json
import subprocess
import sys
import tempfile
TIMEOUT_SECONDS = 5
SENTINEL = "@@RESULT@@"
HARNESS = r'''
import sys, json, copy
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except Exception:
    pass

payload = json.loads(sys.stdin.read())
out = {"executed": False, "results": [], "error": None}
ns = {"__name__": "generated"}
try:
    exec(compile(payload["code"], "<generated>", "exec"), ns)
    fn = ns[payload["function"]]
    out["executed"] = True
except BaseException as e:
    out["error"] = f"{type(e).__name__}: {e}"
    print("@@RESULT@@" + json.dumps(out)); sys.exit(0)

for t in payload["tests"]:
    args = copy.deepcopy(t["args"])
    r = {"args": t["args"], "passed": False}
    try:
        val = fn(*args)
        if "raises" in t:
            r["error"] = "expected " + t["raises"] + " but got " + repr(val)
        else:
            r["got"] = repr(val)
            r["passed"] = (val == t["expected"] and type(val) == type(t["expected"]))
    except BaseException as e:
        if t.get("raises") == type(e).__name__:
            r["passed"] = True
        else:
            r["error"] = type(e).__name__ + ": " + str(e)
    r["expected"] = t.get("expected", t.get("raises"))
    out["results"].append(r)
print("@@RESULT@@" + json.dumps(out))
'''

def run_tests(code: str, function: str, tests: list) -> dict:
    """Return {executed, results[], error}. Never raises."""
    payload = json.dumps({"code": code, "function": function, "tests": tests})
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", HARNESS],
                input=payload, capture_output=True, text=True,
                timeout=TIMEOUT_SECONDS, cwd=tmp, env={},
            )
        except subprocess.TimeoutExpired:
            return {"executed": True, "results": [], "error": f"Timeout after {TIMEOUT_SECONDS}s (possible infinite loop)"}
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(SENTINEL):
            return json.loads(line[len(SENTINEL):])
    if proc.returncode < 0:  # killed by a signal, e.g. SIGXCPU (CPU limit) or SIGKILL (memory limit)
        return {"executed": True, "results": [], "error": "Timeout or resource limit exceeded (possible infinite loop)"}
    err = (proc.stderr or "no output").strip().splitlines()
    return {"executed": False, "results": [], "error": err[-1] if err else "crashed"}
