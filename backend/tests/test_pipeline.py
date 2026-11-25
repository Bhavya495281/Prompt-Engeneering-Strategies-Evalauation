import os
import tempfile
import time
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["USE_BANDIT"] = "0"
from fastapi.testclient import TestClient
from backend.app import db
from backend.app.evaluator import evaluate, extract_code, security_score
from backend.app.executor import run_tests
from backend.app.main import app
from backend.app.tasks import TASK_MAP, TASKS
db.init()
def test_reference_solutions_pass_and_buggy_fail():
    for t in TASKS:
        assert evaluate(t["reference"], t)["solved"] == 1, t["id"]
        assert evaluate(t["buggy"], t)["solved"] == 0, t["id"]

def test_extract_code_takes_last_function_block():
    txt = "think\n```python\nx=1\n```\nfinal:\n```python\ndef f():\n    return 1\n```"
    assert "def f" in extract_code(txt)

def test_infinite_loop_times_out():
    r = run_tests("def f(x):\n    while True:\n        pass\n", "f", [{"args": [1], "expected": 1}])
    assert "Timeout" in (r["error"] or "")

def test_syntax_error_reported():
    ev = evaluate("def f(:\n", TASK_MAP["factorial"])
    assert ev["exec_success"] == 0 and ev["correctness"] == 0

def test_security_flags_dangerous_code():
    score, issues = security_score("import os\ndef f(x):\n    return eval(x)\n")
    assert issues >= 2 and score < 70

def test_api_end_to_end_with_mock():
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    r = c.post("/api/runs", json={"provider": "mock", "tasks": ["is_prime", "factorial"],
                                  "strategies": ["zero_shot", "iterative"], "repeats": 2})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    for _ in range(100):
        if c.get(f"/api/runs/{run_id}").json()["status"] == "finished":
            break
        time.sleep(0.2)
    s = c.get(f"/api/runs/{run_id}/summary").json()
    rates = {x["strategy"]: x["success_rate"] for x in s["by_strategy"]}
    assert rates["iterative"] == 1.0 and rates["zero_shot"] == 0.0
    assert s["best"] == "iterative"
    assert c.get(f"/api/runs/{run_id}/export.csv").text.startswith("task_id")

def test_unconfigured_provider_rejected():
    c = TestClient(app)
    os.environ.pop("OPENAI_API_KEY", None)
    assert c.post("/api/runs", json={"provider": "openai"}).status_code == 400
