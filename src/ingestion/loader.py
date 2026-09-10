"""
Pure domain logic for scanning an input dir and classifying files
against persisted state. No Stage or pipeline-context imports.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.models.pipeline_context import FileRecord, FileStatus, PipelineState

_CHUNK_SIZE = 64 * 1024


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class LoaderResult:
    files_to_process: list[FileRecord]
    state: PipelineState
    scanned: int
    new: int
    updated: int
    unchanged: int
    deleted: int


class Loader:
    def __init__(self, input_dir: str | Path, glob_pattern: str = "**/*"):
        self.input_dir = Path(input_dir)
        self.glob_pattern = glob_pattern

    def run(self, state: PipelineState) -> LoaderResult:
        input_dir = self.input_dir
        if not input_dir.is_dir():
            raise ValueError(f"input dir does not exist: {input_dir}")

        known = state.files
        now = datetime.now(timezone.utc)
        to_process: list[FileRecord] = []

        scanned = new = updated = unchanged = deleted = 0
        seen: set[str] = set()

        for path in input_dir.glob(self.glob_pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(input_dir).as_posix()
            current_hash = _hash_file(path)
            stat = path.stat()
            seen.add(rel)
            scanned += 1

            record = known.get(rel)
            if record is None:
                record = FileRecord(
                    path=rel,
                    absolute_path=str(path),
                    size_bytes=stat.st_size,
                    hash=current_hash,
                    mtime=stat.st_mtime,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                record.status = FileStatus.NEW
                known[rel] = record
                new += 1
            elif record.hash != current_hash or record.mtime != stat.st_mtime:
                record.absolute_path = str(path)
                record.size_bytes = stat.st_size
                record.hash = current_hash
                record.mtime = stat.st_mtime
                record.last_seen_at = now
                record.status = FileStatus.UPDATED
                updated += 1
            else:
                record.last_seen_at = now
                record.status = FileStatus.UNCHANGED
                unchanged += 1

            if record.status in (FileStatus.NEW, FileStatus.UPDATED):
                to_process.append(record)

        for rel in list(known):
            if rel not in seen:
                known[rel].status = FileStatus.DELETED
                deleted += 1

        return LoaderResult(
            files_to_process=to_process,
            state=state,
            scanned=scanned,
            new=new,
            updated=updated,
            unchanged=unchanged,
            deleted=deleted,
        )