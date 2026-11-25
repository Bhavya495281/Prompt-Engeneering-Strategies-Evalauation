import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
from backend.app import db, runner
from backend.app.prompts import STRATEGIES
from backend.app.tasks import TASK_MAP

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="mock", choices=["mock", "anthropic", "openai", "ollama"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--tasks", nargs="*", default=list(TASK_MAP))
    ap.add_argument("--strategies", nargs="*", default=list(STRATEGIES))
    ap.add_argument("--repeats", type=int, default=1)
    a = ap.parse_args()
    db.init()
    n = len(a.tasks) * len(a.strategies) * a.repeats
    run_id = runner.create_run(a.provider, a.model, n)
    print(f"Run #{run_id}: {n} samples with provider={a.provider}")
    runner.execute_run(run_id, a.provider, a.model, a.tasks, a.strategies, a.repeats)

    s = runner.summarize(run_id)
    print(f"\n{'Strategy':<22}{'Solved':>8}{'Tests':>8}{'Quality':>9}{'Security':>10}{'Tokens':>8}{'Latency':>9}")
    for r in s["by_strategy"]:
        print(f"{STRATEGIES[r['strategy']]['name']:<22}{r['success_rate']*100:>7.0f}%{r['avg_correctness']*100:>7.0f}%"
              f"{r['quality']:>9.0f}{r['security']:>10.0f}{r['tokens']:>8.0f}{r['latency']:>8.2f}s")
    print(f"\nBest strategy: {STRATEGIES[s['best']]['name'] if s['best'] else 'n/a'}")
    print(f"Results stored in {db.DB_PATH} (run #{run_id}). Open the web UI to explore them.")


if __name__ == "__main__":
    main()
