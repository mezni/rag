"""Streamlit dashboard for the RAG ingestion pipeline.

Features
--------
* **Run Pipeline** button — invokes ``uv run python app/main.py`` and then
  displays a summary of the latest run plus the 10 most recent runs.
* Shows per‑run counts (new / updated / unchanged / deleted / scanned) and
  stage timings.
* Pulls data from ``data/state/state.json`` so no extra persistence is needed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent  # rag repo root
_STATE_PATH = _ROOT / "data" / "state" / "state.json"


def _run_pipeline() -> subprocess.CompletedProcess:
    """Execute the ingestion pipeline and return the CompletedProcess."""
    cmd = ["uv", "run", "python", "app/main.py"]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=_ROOT)


def _load_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Read the last *limit* runs from the pipeline state file."""
    if not _STATE_PATH.exists():
        return []
    with open(_STATE_PATH, encoding="utf-8") as f:
        state = json.load(f)
    runs = state.get("runs", [])
    return runs[-limit:]  # newest first


def _render_latest(run: dict[str, Any]) -> None:
    """Render the most recent run's summary statistics."""
    st.subheader("Latest run")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", run.get("files_scanned", 0))
    c2.metric("New", run.get("files_new", 0))
    c3.metric("Updated", run.get("files_updated", 0))
    c4.metric("Unchanged", run.get("files_unchanged", 0))
    d1, d2 = st.columns(2)
    d1.metric("Deleted", run.get("files_deleted", 0))
    d2.metric("Chunked", run.get("files_chunked", 0))

    timings = run.get("stage_timings_seconds", {})
    if timings:
        st.write("**Stage timings (seconds)**")
        for stage, t in timings.items():
            st.caption(f"{stage}: {t:.3f}")

    # human‑readable pipeline finish line, if present in stdout
    st.caption("Run finished successfully.")


def _render_history(runs: list[dict[str, Any]]) -> None:
    """Render a table of the most recent *limit* runs."""
    if not runs:
        st.info("No runs yet — click **Run Pipeline** to start.")
        return

    st.subheader(f"Last {len(runs)} runs")
    rows = []
    for run in runs:
        rows.append(
            {
                "Run ID": run.get("run_id", "")[:8],
                "New": run.get("files_new", 0),
                "Updated": run.get("files_updated", 0),
                "Unchanged": run.get("files_unchanged", 0),
                "Deleted": run.get("files_deleted", 0),
                "Scanned": run.get("files_scanned", 0),
                "Chunked": run.get("files_chunked", 0),
            }
        )
    st.table(rows)


# ---------------------------------------------------------------------------
# Streamlit app layout
# ---------------------------------------------------------------------------

st.set_page_config(page_title="RAG Pipeline Dashboard", page_icon="📊", layout="wide")

st.title("📊 RAG Ingestion Pipeline Dashboard")

# --- Run pipeline ---
if st.button("▶️ Run Pipeline"):
    with st.spinner("Running pipeline…"):
        proc = _run_pipeline()
    # Show raw output so the user can see the final summary line
    if proc.stdout.strip():
        st.code(proc.stdout[-3000:])
    if proc.stderr.strip():
        st.error(proc.stderr[-2000:])

    # Refresh the view
    runs = _load_runs(limit=10)
    _render_latest(runs[-1] if runs else {})
    _render_history(runs)

# --- Static initial view (when the page loads without a button click) ---
st.write("---")
st.subheader("Last 10 runs")
runs = _load_runs(limit=10)
_render_history(runs)
if runs:
    _render_latest(runs[-1])
