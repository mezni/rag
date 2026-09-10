from datetime import UTC, datetime
from pathlib import Path

from src.chunking.chunker import Chunker, ChunkFile, chunk_text
from src.models.pipeline_context import (
    FileRecord,
    PipelineContext,
    PipelineRun,
    PipelineState,
)
from src.pipeline.stages import ChunkerStage


def _make_record(path: str = "docs/doc.pdf", content: str = "Hello PDF.") -> FileRecord:
    return FileRecord(
        path=path,
        absolute_path=f"/tmp/{path}",
        size_bytes=3,
        hash="unused",
        mtime=1.0,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        stage_outputs={"parser": {"content": content}},
    )


def test_chunk_text_splits_long_text() -> None:
    text = "The quick brown fox jumps over the lazy dog. " * 50
    chunks = chunk_text(text, chunk_size=24, chunk_overlap=6)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert "quick" in chunks[0]


def test_chunk_text_single_chunk_for_short_text() -> None:
    chunks = chunk_text("Just one short sentence.", chunk_size=512, chunk_overlap=0)
    assert chunks == ["Just one short sentence."]


def test_chunker_writes_chunk_file(tmp_path: Path) -> None:
    record = _make_record(content="Alpha. " * 100)
    output = tmp_path / "processed"

    Chunker(output_dir=output, chunk_size=32, chunk_overlap=8).chunk_one(record)

    dest = output / "docs" / "doc.chunks.json"
    assert dest.exists()
    payload = ChunkFile.model_validate_json(dest.read_text(encoding="utf-8"))
    assert payload.source == "docs/doc.pdf"
    assert payload.chunk_count == len(payload.chunks)
    assert payload.chunks[0].chunk_id == "docs/doc.pdf:0"
    assert payload.chunks[0].char_count == len(payload.chunks[0].text)


def test_chunker_stage_outputs_recorded(tmp_path: Path) -> None:
    record = _make_record(content="Beta. " * 100)
    output = tmp_path / "processed"

    Chunker(output_dir=output, chunk_size=32, chunk_overlap=8).run([record])

    info = record.stage_outputs["chunker"]
    assert info["chunk_count"] == len(info["chunk_ids"])
    assert info["processed_path"] == str(output / "docs" / "doc.chunks.json")


def test_chunker_skips_record_without_parser_content(tmp_path: Path) -> None:
    record = _make_record(content="")
    output = tmp_path / "processed"

    result = Chunker(output_dir=output, chunk_size=32, chunk_overlap=8).run([record])

    assert record.stage_outputs["chunker"]["chunk_count"] == 0
    assert not (output / "docs" / "doc.chunks.json").exists()
    assert result.chunked == 0


def test_chunker_run_counts_chunked_files(tmp_path: Path) -> None:
    output = tmp_path / "processed"
    chunker = Chunker(output_dir=output, chunk_size=32, chunk_overlap=8)

    result = chunker.run(
        [_make_record(path="a.pdf", content="One. " * 100), _make_record(path="b.pdf")]
    )
    assert result.chunked == 2


def test_chunker_stage_updates_run_count(tmp_path: Path) -> None:
    run = PipelineRun(
        run_id="r1",
        started_at=datetime.now(UTC),
        input_dir="/tmp/in",
        output_dir="",
    )
    context = PipelineContext(
        state=PipelineState(runs=[run]),
        run=run,
        files_to_process=[_make_record(content="Gamma. " * 100)],
    )

    ChunkerStage(chunk_size=32, chunk_overlap=8).run(context)

    assert context.run.files_chunked == 1
