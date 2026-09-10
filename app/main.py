"""CLI entry point. Wires stages into a Pipeline and runs it once."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.pipeline import Pipeline
from src.pipeline.stages import LoaderStage, LoggingStage
from src.pipeline.state_store import StateStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RAG ingestion pipeline")
    parser.add_argument("--input-dir", required=True, help="directory to scan")
    parser.add_argument(
        "--state",
        default=".rag/state.json",
        help="path to persisted pipeline state (default: %(default)s)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="keep only the most recent N runs in state (0 = keep all)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    stages = [
        LoggingStage(),
        LoaderStage(),
    ]

    pipeline = Pipeline(
        stages=stages,
        state_store=StateStore(args.state),
        max_runs=args.max_runs,
    )
    pipeline.run(args.input_dir)


if __name__ == "__main__":
    main()