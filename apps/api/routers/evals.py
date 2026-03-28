# evals.py — Eval results API for the frontend dashboard
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter

log = structlog.get_logger()
router = APIRouter(prefix="/evals", tags=["evals"])

_RESULTS_DIR = Path(__file__).parent.parent / "evals" / "results"


@router.get("/latest")
async def get_latest_results() -> dict[str, Any]:
    """Return the most recent eval run results."""
    if not _RESULTS_DIR.exists():
        return {"summary": None, "message": "No eval results found. Run: python -m evals.runner"}

    result_files = sorted(_RESULTS_DIR.glob("eval_*.json"), reverse=True)
    if not result_files:
        return {"summary": None, "message": "No eval results found. Run: python -m evals.runner"}

    latest = result_files[0]
    data = json.loads(latest.read_text())
    data["file"] = latest.name
    return data


@router.get("/history")
async def get_eval_history() -> dict[str, Any]:
    """Return summary of all eval runs for trend tracking."""
    if not _RESULTS_DIR.exists():
        return {"runs": []}

    runs = []
    for f in sorted(_RESULTS_DIR.glob("eval_*.json"), reverse=True)[:20]:
        try:
            data = json.loads(f.read_text())
            runs.append({
                "file": f.name,
                "timestamp": f.stem.replace("eval_", ""),
                "summary": data.get("summary", {}),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return {"runs": runs}
