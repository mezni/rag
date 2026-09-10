"""
Pure domain logic — knows nothing about Stage, PipelineContext, or
logging. Takes a PipelineState, returns the files that changed plus
the updated state. This is what makes it trivially unit-testable and
reusable outside the pipeline framework if you ever need to.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.hashing import hash_file
from src.models.pipeline_context import FileRecord, FileStatus, PipelineState


class Loader:
    def __init__(self, input_dir: str | Path, glob_pattern: str = "**/*"):
        self.input_dir = Path(input_dir)
        self.glob_pattern = glob_pattern

    def scan(self) -> list[Path]:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")
        return [p for p in self.input_dir.glob(self.glob_pattern) if p.is_file()]

    def run(self, state: PipelineState) -> tuple[list[FileRecord], PipelineState]:
        now = datetime.now(timezone.utc)
        found_paths = self.scan()
        found_rel_paths = set()

        files_to_process: list[FileRecord] = []
        counts = {"new": 0, "updated": 0, "unchanged": 0, "deleted": 0}

        for abs_path in found_paths:
            rel_path = str(abs_path.relative_to(self.input_dir))
            found_rel_paths.add(rel_path)

            stat = abs_path.stat()
            new_hash = hash_file(abs_path)
            existing = state.files.get(rel_path)

            if existing is None:
                record = FileRecord(
                    path=rel_path,
                    absolute_path=str(abs_path),
                    size_bytes=stat.st_size,
                    hash=new_hash,
                    mtime=stat.st_mtime,
                    first_seen_at=now,
                    last_seen_at=now,
                    status=FileStatus.NEW,
                )
                state.files[rel_path] = record
                files_to_process.append(record)
                counts["new"] += 1

            elif existing.hash != new_hash:
                existing.hash = new_hash
                existing.size_bytes = stat.st_size
                existing.mtime = stat.st_mtime
                existing.last_seen_at = now
                existing.status = FileStatus.UPDATED
                files_to_process.append(existing)
                counts["updated"] += 1

            else:
                existing.last_seen_at = now
                existing.status = FileStatus.UNCHANGED
                counts["unchanged"] += 1

        for rel_path, record in state.files.items():
            if rel_path not in found_rel_paths and record.status != FileStatus.DELETED:
                record.status = FileStatus.DELETED
                counts["deleted"] += 1

        if state.last_run() is not None:
            run = state.last_run()
            run.files_scanned = len(found_paths)
            run.files_new = counts["new"]
            run.files_updated = counts["updated"]
            run.files_unchanged = counts["unchanged"]
            run.files_deleted = counts["deleted"]

        return files_to_process, state
