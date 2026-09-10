# RAG Ingestion Pipeline

Turns a directory of documents into versioned, machine-readable markdown files,
driven by an incremental state machine that remembers every run.

```
input (PDFs) ──▶ loader ──▶ parser ──▶ cleaner ──▶ output (.txt + .md)
                     │          │           │
                     └──────────┴───────────┴──▶ state.json (one run = one entry)
```

## Stages

The pipeline is a sequence of `Stage`s orchestrated by the engine. Stages only
mutate the `PipelineContext` passed between them (see `src/pipeline/stage.py`).

| Stage            | Job                                                                                                  |
| ---------------- | ---------------------------------------------------------------------------------------------------- |
| `logging`        | Pass-through observability: logs how many files were known and their statuses before this run.        |
| `loader`         | Scans `input_dir` and classifies each file against the previous run (`NEW`/`UPDATED`/`UNCHANGED`/`DELETED`). Mirrors directories into the output dir but never copies files. |
| `parser`         | Extracts raw text from PDFs via llama-index. Writes `<stem>.txt` and versions it: v1 on first parse, then increments on every modification (old text archived as `<stem>.vN.txt`). Remembers files containing no usable text but does not pass them downstream. |
| `cleaner`        | Converts each `.txt` into markdown with the `markitdown` library. The text is fed in as HTML so embedded `<b>…</b>` labels become real markdown (`**…**`) instead of leaking through. Writes `<stem>.md` in the same directory. |

## State model (`data/state/state.json`)

One file, one entry per run. Each run snapshots its own view of every file, so a
single file doubles as history and diff baseline (no `state_last.json`).

```jsonc
{
  "version": 1,
  "runs": [
    {
      "run_id": "...",
      "started_at": "...",
      "finished_at": "...",
      "failed": false,
      "input_dir": "data/raw",
      "output_dir": "data/processed",
      "files_scanned": 12, "files_new": 12, "files_updated": 0,
      "files_unchanged": 0, "files_deleted": 0, "files_sent_downstream": 12,
      "files_cleaned": 12,
      "stage_timings_seconds": { "logging": 0.0, "loader": 0.08, ... },
      "files": {
        "docs/doc.pdf": {
          "path": "docs/doc.pdf",
          "absolute_path": "data/raw/docs/doc.pdf",
          "status": "new",           // new | updated | unchanged | deleted
          "version": 1,              // bumped on every modification
          "stage_outputs": {
            "parser":  { "version": 1, "processed_path": "data/processed/docs/doc.txt" },
            "cleaner": { "version": 1 }
          }
        }
      }
    }
  ]
}
```

### Deletion handling

When a file present in the previous run is gone from disk, the loader marks it
`DELETED`. On that transition the engine removes the processed artifacts (both
`.txt` and `.md`) plus their `v*` archives from the output dir.

## Layout

```
app/main.py                  CLI entry point (wires the 4 stages)
src/config/logger.py         logging setup
src/ingestion/               pure domain logic (no Stage/pipeline imports)
  loader.py                  scan + classify, mirrors dirs
  parser.py                  PDF → text, versioning
  cleaner.py                 markitdown conversion, markdown output
  hashing.py                 file hashing
src/models/pipeline_context.py   data contracts (FileRecord, PipelineRun, …)
src/pipeline/
  pipeline.py                engine: loop, timing, identity guards, failure handling
  stage.py                   Stage base class
  stages/                    loader/parser/cleaner/logging stages
  state_store.py             atomic load/save of state.json
tests/                       52 tests (pytest)
scripts/generate_docs.py     sample corpus generator
```

## Usage

```bash
# install deps
uv sync

# run the pipeline (defaults: data/raw → data/processed, state in data/state)
uv run python app/main.py

# options
uv run python app/main.py \
  --input-dir data/raw \
  --output-dir data/processed \
  --state    data/state/state.json \
  --max-runs 0          # 0 = keep every run, otherwise keep the N most recent

# tests
uv run pytest
```

## Conventions

- Ingestion modules (`src/ingestion/*`) are pure: no Stage or pipeline-context
  imports, so they stay unit-testable on their own.
- Stages are thin orchestration; substantive logic lives in `src/ingestion/`.
- Stages must mutate `context.state` / `context.run` in place. Replacing them
  raises a `RuntimeError` from the engine.
- State is written atomically (`*.tmp` then `os.replace`).
- Pydantic `BaseModel` fields are set with keyword arguments only.