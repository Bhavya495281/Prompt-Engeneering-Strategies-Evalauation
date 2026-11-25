from . import db
from .evaluator import evaluate, extract_code
from .llm import get_llm
from .prompts import build_prompt
from .tasks import TASK_MAP
MAX_ITERATIVE_ATTEMPTS = 3

def run_cell(llm, task: dict, strategy: str) -> dict:
    """One (task, strategy) sample. Iterative strategy retries with test feedback."""
    limit = MAX_ITERATIVE_ATTEMPTS if strategy == "iterative" else 1
    feedback, in_tok, out_tok, latency, code, ev = None, 0, 0, 0.0, "", None
    attempts = 0
    for attempt in range(1, limit + 1):
        attempts = attempt
        system, user = build_prompt(strategy, task, feedback)
        r = llm.generate(system, user, meta={"task_id": task["id"], "strategy": strategy, "attempt": attempt})
        in_tok += r.input_tokens
        out_tok += r.output_tokens
        latency += r.latency
        code = extract_code(r.text)
        ev = evaluate(code, task)
        if ev["solved"]:
            break
        feedback = {"code": code, "report": ev["failure_report"]}
    return {**ev, "attempts": attempts, "latency": latency, "in_tokens": in_tok, "out_tokens": out_tok, "code": code}


def create_run(provider: str, model: str | None, n_cells: int) -> int:
    llm = get_llm(provider, model)
    return db.execute("INSERT INTO runs(provider, model, status, total) VALUES (?,?,?,?)",
                      (llm.provider, llm.model, "queued", n_cells))


def execute_run(run_id: int, provider: str, model: str | None, task_ids: list, strategies: list, repeats: int):
    """Blocking; call from a background thread."""
    try:
        llm = get_llm(provider, model)
        db.execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
        for task_id in task_ids:
            task = TASK_MAP[task_id]
            for strategy in strategies:
                for rep in range(1, repeats + 1):
                    try:
                        r = run_cell(llm, task, strategy)
                    except Exception as e:  # API/network failure for this sample
                        r = {"attempts": 0, "passed": 0, "total": len(task["tests"]), "correctness": 0.0,
                             "solved": 0, "exec_success": 0, "quality": 0.0, "security": 0.0, "sec_issues": 0,
                             "latency": 0.0, "in_tokens": 0, "out_tokens": 0, "code": "",
                             "error": f"LLM error: {type(e).__name__}: {e}"}
                    db.execute(
                        """INSERT INTO results(run_id,task_id,strategy,repeat,attempts,passed,total_tests,correctness,
                           solved,exec_success,quality,security,sec_issues,latency,in_tokens,out_tokens,code,error)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (run_id, task_id, strategy, rep, r["attempts"], r["passed"], r["total"], r["correctness"],
                         r["solved"], r["exec_success"], r["quality"], r["security"], r["sec_issues"],
                         r["latency"], r["in_tokens"], r["out_tokens"], r["code"], r.get("error")))
                    db.execute("UPDATE runs SET done=done+1 WHERE id=?", (run_id,))
        db.execute("UPDATE runs SET status='finished' WHERE id=?", (run_id,))
    except Exception as e:
        db.execute("UPDATE runs SET status='failed', error=? WHERE id=?", (f"{type(e).__name__}: {e}", run_id))


def summarize(run_id: int) -> dict:
    by_strategy = db.query(
        """SELECT strategy, COUNT(*) n, AVG(solved) success_rate, AVG(correctness) avg_correctness,
                  AVG(exec_success) exec_rate, AVG(quality) quality, AVG(security) security,
                  AVG(latency) latency, AVG(in_tokens + out_tokens) tokens, AVG(attempts) attempts
           FROM results WHERE run_id=? GROUP BY strategy""", (run_id,))
    matrix = db.query(
        "SELECT strategy, task_id, AVG(correctness) correctness FROM results WHERE run_id=? GROUP BY strategy, task_id",
        (run_id,))
    ranked = sorted(by_strategy, key=lambda s: (-s["success_rate"], -s["quality"], s["tokens"]))
    return {"by_strategy": by_strategy, "matrix": matrix, "best": ranked[0]["strategy"] if ranked else None}
