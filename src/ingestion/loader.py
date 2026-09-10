"""
Pure domain logic for scanning an input dir and classifying files
against the previous run's file records. No Stage or pipeline-context
imports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from src.ingestion.hashing import hash_file
from src.models.pipeline_context import FileRecord, FileStatus


class LoaderResult(BaseModel):
    files_to_process: list[FileRecord]
    files: dict[str, FileRecord]
    scanned: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0


class Loader(BaseModel):
    input_dir: Path
    glob_pattern: str = "**/*"
    output_dir: Path | None = None

    def run(self, previous_files: dict[str, FileRecord]) -> LoaderResult:
        input_dir = self.input_dir
        if not input_dir.is_dir():
            raise ValueError(f"input dir does not exist: {input_dir}")

        now = datetime.now(UTC)
        files: dict[str, FileRecord] = {}
        to_process: list[FileRecord] = []

        scanned = new = updated = unchanged = deleted = 0
        seen: set[str] = set()

        for path in input_dir.glob(self.glob_pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(input_dir).as_posix()
            current_hash = hash_file(path)
            stat = path.stat()
            seen.add(rel)
            scanned += 1

            if self.output_dir is not None:
                rel_dir = path.relative_to(input_dir).parent
                (self.output_dir / rel_dir).mkdir(parents=True, exist_ok=True)

            previous = previous_files.get(rel)
            if previous is None:
                record = FileRecord(
                    path=rel,
                    absolute_path=str(path),
                    size_bytes=stat.st_size,
                    hash=current_hash,
                    mtime=stat.st_mtime,
                    first_seen_at=now,
                    last_seen_at=now,
                    status=FileStatus.NEW,
                )
                new += 1
            elif previous.hash != current_hash or previous.mtime != stat.st_mtime:
                record = previous.model_copy(deep=True)
                record.size_bytes = stat.st_size
                record.absolute_path = str(path)
                record.hash = current_hash
                record.mtime = stat.st_mtime
                record.last_seen_at = now
                record.status = FileStatus.UPDATED
                updated += 1
            else:
                record = previous.model_copy(deep=True)
                record.last_seen_at = now
                record.status = FileStatus.UNCHANGED
                unchanged += 1

            files[rel] = record
            if record.status in (FileStatus.NEW, FileStatus.UPDATED):
                to_process.append(record)

        for rel, previous in previous_files.items():
            if rel in seen:
                continue
            record = previous.model_copy(deep=True)
            record.status = FileStatus.DELETED
            files[rel] = record
            deleted += 1

        return LoaderResult(
            files_to_process=to_process,
            files=files,
            scanned=scanned,
            new=new,
            updated=updated,
            unchanged=unchanged,
            deleted=deleted,
        )
