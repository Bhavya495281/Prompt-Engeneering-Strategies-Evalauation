# Prompt Eval Lab

Evaluating prompt engineering strategies for code generation (B.Tech CSE Project-1).

Compares **Zero-Shot, Few-Shot, Chain-of-Thought, Role-Based and Iterative Refinement** prompting on five tasks
(reverse string, prime check, sort list, factorial, largest element) and scores every generated program on
**correctness, execution success, code quality, security, time and tokens**.

## Pipeline (matches the synopsis flowchart)

Task selection -> model selection -> prompt strategy -> code generation -> sandboxed testing -> data collection -> comparison.

## Quick start (3 commands)

```bash
pip install -r requirements.txt
python run.py          # opens http://localhost:8000
python -m pytest -q    # optional: run the tests
```

## Setup (optional virtual environment)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Edit `.env`: keep `LLM_PROVIDER=mock` to try the app offline, or add a key for a real model
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) or run a local model with Ollama (`ollama pull qwen2.5-coder:7b`).

## Run the web app

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Open http://localhost:8000, choose tasks and strategies, and click **Run experiment**.
API docs: http://localhost:8000/docs

## Run from the command line

```bash
python scripts/run_experiment.py --provider mock
python scripts/run_experiment.py --provider anthropic --repeats 3
python scripts/run_experiment.py --provider openai --strategies zero_shot cot --tasks is_prime factorial
```

## Tests

```bash
python -m pytest -q
```

## How each metric is computed

| Metric | Definition |
|---|---|
| Correctness | Passed test cases / total test cases. "Solved" means all tests pass. |
| Execution success | Code compiles and defines the function without crashing. |
| Quality (0-100) | Docstrings 25, type hints 20, line length 15, low cyclomatic complexity 25, no print/input 15. |
| Security (0-100) | 100 minus penalties for eval/exec, os/subprocess/pickle, file access, plus Bandit findings if installed. |
| Efficiency | Input + output tokens and wall-clock latency, summed over all attempts for Iterative Refinement. |

## Add your own task

Append a dict to `TASKS` in `backend/app/tasks.py` (id, function, signature, description, tests, reference, buggy).

## Safety note

Generated code runs in a separate Python process with a 5 s timeout, CPU and memory limits, and an empty environment.
That is fine for coursework, but for untrusted models run the backend in Docker with networking disabled.

## Folder structure

```
prompt-eval-lab/
├── backend/app/   main.py llm.py prompts.py tasks.py executor.py evaluator.py runner.py db.py
├── backend/tests/ test_pipeline.py
├── frontend/      index.html style.css app.js
├── scripts/       run_experiment.py
├── data/          results.db (created on first run)
├── requirements.txt  .env.example  pytest.ini  README.md
```
