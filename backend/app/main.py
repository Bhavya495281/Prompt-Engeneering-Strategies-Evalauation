import csv
import io
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import db, runner
from .llm import available_providers
from .prompts import STRATEGIES
from .tasks import TASK_MAP, TASKS, public_task

app = FastAPI(title="Prompt Eval Lab", version="1.0")
db.init()
class RunRequest(BaseModel):
    provider: str = "mock"
    model: str | None = None
    tasks: list[str] = Field(default_factory=lambda: list(TASK_MAP))
    strategies: list[str] = Field(default_factory=lambda: list(STRATEGIES))
    repeats: int = Field(default=1, ge=1, le=10)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {"providers": available_providers()}


@app.get("/api/tasks")
def tasks():
    return [public_task(t) for t in TASKS]


@app.get("/api/strategies")
def strategies():
    return [{"id": k, **v} for k, v in STRATEGIES.items()]


@app.post("/api/runs")
def start_run(req: RunRequest, bg: BackgroundTasks):
    bad_t = [t for t in req.tasks if t not in TASK_MAP]
    bad_s = [s for s in req.strategies if s not in STRATEGIES]
    if bad_t or bad_s or not req.tasks or not req.strategies:
        raise HTTPException(400, f"Invalid selection. tasks={bad_t} strategies={bad_s}")
    if not available_providers().get(req.provider, False):
        raise HTTPException(400, f"Provider '{req.provider}' is not configured. Add its API key to .env")
    n = len(req.tasks) * len(req.strategies) * req.repeats
    try:
        run_id = runner.create_run(req.provider, req.model, n)
    except Exception as e:
        raise HTTPException(400, f"Could not start provider: {e}")
    bg.add_task(runner.execute_run, run_id, req.provider, req.model, req.tasks, req.strategies, req.repeats)
    return {"run_id": run_id, "total": n}


@app.get("/api/runs")
def list_runs():
    return db.query("SELECT * FROM runs ORDER BY id DESC LIMIT 50")


def _get_run(run_id: int):
    rows = db.query("SELECT * FROM runs WHERE id=?", (run_id,))
    if not rows:
        raise HTTPException(404, "Run not found")
    return rows[0]


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    return _get_run(run_id)


@app.get("/api/runs/{run_id}/summary")
def get_summary(run_id: int):
    _get_run(run_id)
    return runner.summarize(run_id)


@app.get("/api/runs/{run_id}/results")
def get_results(run_id: int):
    _get_run(run_id)
    return db.query("SELECT * FROM results WHERE run_id=? ORDER BY id", (run_id,))


@app.get("/api/runs/{run_id}/export.csv")
def export_csv(run_id: int):
    _get_run(run_id)
    rows = db.query("SELECT task_id,strategy,repeat,attempts,passed,total_tests,correctness,solved,exec_success,"
                    "quality,security,sec_issues,latency,in_tokens,out_tokens,error FROM results WHERE run_id=?",
                    (run_id,))
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"})


# Frontend (must be mounted last so /api routes win)
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
