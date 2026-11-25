import os
import sqlite3
from pathlib import Path
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parents[2] / "data" / "results.db"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT DEFAULT CURRENT_TIMESTAMP,
  provider TEXT, model TEXT, status TEXT,
  total INTEGER, done INTEGER DEFAULT 0, error TEXT
);
CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER, task_id TEXT, strategy TEXT, repeat INTEGER,
  attempts INTEGER, passed INTEGER, total_tests INTEGER,
  correctness REAL, solved INTEGER, exec_success INTEGER,
  quality REAL, security REAL, sec_issues INTEGER,
  latency REAL, in_tokens INTEGER, out_tokens INTEGER,
  code TEXT, error TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);
"""
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = _conn()
    try:
        c.executescript(SCHEMA)
        c.commit()
    finally:
        c.close()

def execute(sql, args=()):
    c = _conn()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid
    finally:
        c.close()

def query(sql, args=()):
    c = _conn()
    try:
        return [dict(r) for r in c.execute(sql, args).fetchall()]
    finally:
        c.close()
