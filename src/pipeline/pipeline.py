"""
The engine. Knows nothing about loader/parser/chunker specifically —
just loops over whatever Stage list it's given, timing and logging
each one, and persists state at the end.

Per-stage logging/timing lives HERE rather than as a separate
LoggingStage in the stage list — that way every stage gets it for
free, and you can't forget to slot a logging stage in when you add
the 5th one.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from src.config.logger import get_logger
from src.models.pipeline_context import PipelineContext, PipelineRun
from src.pipeline.stage import Stage
from src.pipeline.state_store import StateStore

logger = get_logger(__name__)


class Pipeline:
    def __init__(self, stages: list[Stage], state_store: StateStore):
        self.stages = stages
        self.state_store = state_store

    def run(self, input_dir: str) -> PipelineContext:
        state = self.state_store.load()
        run = PipelineRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            input_dir=input_dir,
        )
        state.runs.append(run)

        context = PipelineContext(
            state=state,
            run=run,
            scratch={"input_dir": input_dir},
        )

        logger.info(f"Run {run.run_id} starting ({len(self.stages)} stages)")

        for stage in self.stages:
            start = time.monotonic()
            logger.info(f"-> stage '{stage.name}' starting "
                        f"({len(context.files_to_process)} files in flight)")
            try:
                context = stage.run(context)
            except Exception:
                logger.exception(f"Stage '{stage.name}' failed")
                raise
            duration = time.monotonic() - start
            run.stage_timings_seconds[stage.name] = round(duration, 4)
            logger.info(f"<- stage '{stage.name}' finished in {duration:.3f}s")

        run.finished_at = datetime.now(timezone.utc)
        self.state_store.save(context.state)

        logger.info(
            f"Run {run.run_id} done: scanned={run.files_scanned} "
            f"new={run.files_new} updated={run.files_updated} "
            f"unchanged={run.files_unchanged} deleted={run.files_deleted}"
        )
        return context
