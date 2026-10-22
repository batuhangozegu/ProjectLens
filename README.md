# ProjectLens

ProjectLens is a local repository analyzer. The installable CLI scans repositories, parses Python and Dart without executing code, resolves Python imports and Dart file/package URIs, detects cycles, reports declared frameworks and source-to-test matches, calculates basic metrics, and can export deterministic JSON.

Analysis JSON also includes an explainable `metrics.health` heuristic (formula version 1) based on dependency cycles, unresolved imports, test file presence by name/import heuristic, and TODO/FIXME density. It is not a quality guarantee, correctness measure, or coverage measure; components with missing data are reported as unavailable. Older stored snapshots may omit this optional key.

Every new analysis also includes `metrics.risk`, an explainable static heuristic based on file churn (when requested), size, dependency cycles, test file matching, and local fan-in. It is not a prediction of defects; test matches are not coverage. Git history is opt-in, uses a deterministic window relative to the HEAD commit date, and is unavailable for non-Git trees and the API's depth-one checkouts. Older snapshots may omit both `metrics.risk` and `metrics.git_history`.

Analyses also include optional `metrics.findings` for large functions/classes, classes with many methods, and high local dependency fan-in/out. These use documented static thresholds and line spans, so they are review prompts rather than defect predictions. Older snapshots may omit this key; see [architecture](docs/ARCHITECTURE.md#size-and-coupling-findings-56).

## Setup

Python 3.10 or newer is required. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate                 # POSIX; on Windows use .venv\Scripts\Activate.ps1
python -m pip install -e 'backend[dev]'
```

The `dev` extra installs the test tools for the analyzer and CLI. Install the
optional API, database, and migration dependencies with
`python -m pip install -e 'backend[dev,app]'` when you want to run the API.

## Usage

```sh
python -m projectlens analyze /path/to/python/project
projectlens analyze . --output analysis.json
python -m projectlens analyze . --top 5 --max-diagnostics 3
python -m projectlens analyze . --git-history --history-days 180
```

History collection has bounded output and commit limits. It excludes merge commits and rename tracking, and stores only author counts (never raw emails). The report labels churn as commit counts, not lines changed or bug probability. See [architecture](docs/ARCHITECTURE.md#git-history-and-explainable-risk-55) for the formula, unavailable reasons, and limits.

## Run the API locally with PostgreSQL

Create a development role and database in PostgreSQL (replace the placeholders
with local values; use a development database ending in `_dev`):

```sh
psql -U postgres -c "CREATE ROLE projectlens LOGIN PASSWORD 'YOUR_LOCAL_PASSWORD';"
psql -U postgres -c "CREATE DATABASE projectlens_dev OWNER projectlens;"
```

Install the app extra and copy `backend/.env.example` to `backend/.env`, then
replace its placeholder URL with your local PostgreSQL URL. The `.env` file is
read automatically from the current directory or `backend/`; keep real
credentials out of version control. Use a separate database ending in `_test`
for the PostgreSQL test pass.

```sh
python -m pip install -e 'backend[dev,app]'
cd backend
alembic upgrade head
uvicorn --factory projectlens.app.api:create_app --host 127.0.0.1 --port 8000
```

Create a project and start an analysis (replace the public GitHub URL with a repository you can access):

```sh
curl -X POST http://127.0.0.1:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"repository_url":"https://github.com/OWNER/REPOSITORY","branch":"main"}'
curl http://127.0.0.1:8000/api/v1/jobs/JOB_ID
curl http://127.0.0.1:8000/api/v1/health
```

The create endpoint returns immediately with project and job IDs; poll the returned `job_url` for completion. The API only accepts public HTTPS GitHub repository URLs.

### Roadmap import and progress

Import Markdown checklist text directly in the request body; the API does not
read server-side files. The request is limited to 1 MiB. Re-importing matches
stable parser keys, creates no duplicates, and only checked boxes can complete
an existing TODO or IN_PROGRESS task. Existing titles/categories and manually
managed tasks are preserved. Use `dry_run` to preview the same report without
database writes.

```sh
curl -X POST http://127.0.0.1:8000/api/v1/projects/PROJECT_ID/roadmap/import \
  -H 'Content-Type: application/json' \
  --data-binary '{"markdown":"# Setup\n- [ ] Install dependencies\n- [x] Create project\n","dry_run":true}'
curl http://127.0.0.1:8000/api/v1/projects/PROJECT_ID/roadmap/progress
curl 'http://127.0.0.1:8000/api/v1/projects/PROJECT_ID/roadmap/progress?source=import'
```

Progress counts DONE tasks as complete; IN_PROGRESS earns no partial credit,
and BLOCKED tasks remain in the denominator. An empty roadmap reports a null
percentage and `state: "empty"`. This is manual task status only; analysis-based
estimates are not included.

Code-aware estimates are available separately at
`GET /api/v1/projects/PROJECT_ID/tasks/TASK_ID/assessment` and
`GET /api/v1/projects/PROJECT_ID/roadmap/assessment`. They report snapshot
evidence and uncertainty without changing or blending into manual progress.

## Run tests

From the repository root, the default test run uses isolated temporary SQLite
databases for DB-touching tests:

```sh
PYTHONPATH=backend/src python -m pytest backend/tests -p no:cacheprovider
```

To add PostgreSQL coverage, create a disposable database whose name ends in
`_test` (for example `projectlens_test`) and set `TEST_DATABASE_URL` to it.
The test fixture drops and recreates only ProjectLens tables and
`alembic_version` in that database before and after each DB test. It refuses a
PostgreSQL URL without the `_test` suffix. `DATABASE_URL` is not used to select
the test target.

```sh
TEST_DATABASE_URL='postgresql+psycopg://projectlens:YOUR_LOCAL_PASSWORD@localhost:5432/projectlens_test' \
  PYTHONPATH=backend/src python -m pytest backend/tests -p no:cacheprovider
```

On PowerShell, set `$env:TEST_DATABASE_URL` and `$env:PYTHONPATH` before running
the same pytest command.

## Docker Compose

The image build and `docker compose up --build` have been verified on Docker
29.8: migrations run to head, the API reports healthy, runs as a non-root user
with a read-only filesystem, and a real analysis (public clone, snapshot saved
to PostgreSQL) completes inside the container. Copy
`.env.compose.example` to the repository-root `.env`, choose a local password
using URL-safe characters, then start the stack:

```sh
docker compose up --build
```

Compose starts PostgreSQL with a named volume, waits for its health check,
runs a one-shot migration service, and then starts the API. The API is bound to
`127.0.0.1:${API_PORT}` (default `8000`); `docker compose down -v` also removes
the database volume.

`--output FILE` writes the full result as UTF-8 JSON. The terminal summary is still printed. JSON is deterministic and contains repository-relative paths; the selected root path is deliberately omitted so identical trees produce identical JSON when copied elsewhere. Largest-file and diagnostic display limits affect the summary; `--top` also sets how many largest files are included in the result.

### Example output

Captured by running `python -m projectlens analyze backend/tests/fixtures/sample_repo` (the `Root:` line shows a shortened path; the rest is verbatim):

```text
ProjectLens analysis
Root: .../sample_repo
*** PARTIAL RESULT: some files or directories could not be fully analyzed. ***

Files: 10 (Python: 8)
Physical LOC: 25 (known: 10, unavailable: 0)
Python LOC: 21 (known: 8, unavailable: 0)
Largest files:
       7 LOC  src/pkg/left.py
       4 LOC  src/pkg/right.py
       3 LOC  broken.py
       2 LOC  README.md
       2 LOC  pyproject.toml
       2 LOC  src/isolated.py
       2 LOC  tests/test_sample.py
       1 LOC  flat.py
       1 LOC  flat_consumer.py
       1 LOC  src/pkg/__init__.py
TODO/FIXME: 2 (TODO: 1, FIXME: 1)
Dependencies: 3 local edges, 1 external, 0 unresolved
Cycle groups: 1
Frameworks declared: 0
Test matches: 0 of 6 source files have a matching test file (name/import heuristic, not coverage)
Health: 25.0 (poor, confidence: medium)
  Health component unavailable (todo_density): Marker data is incomplete (1 files unavailable), with 2 known markers across 18 LOC; TODO/FIXME density cannot be scored.
Risk: 0 high, 0 medium, 6 low
  src/pkg/left.py (low, 2 points: cycle, untested)
  src/pkg/right.py (low, 2 points: cycle, untested)
  flat.py (low, 1 points: untested)
  1. src/pkg/left.py, src/pkg/right.py
Diagnostics: 2
  parse/SyntaxError [broken.py]: invalid syntax (line 3)
  parse/TokenizeError [broken.py]: ('unexpected EOF in multi-line statement', (3, 0)) (line 3)
```

The sample contains a syntax-error file, so the command exits with code 3 (partial analysis).

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Analysis completed without conditions marked partial by the pipeline. |
| 1 | Fatal analysis or output error: invalid, missing, unreadable, or non-directory root; or an invalid/unwritable output path (including a directory). The error is printed to stderr without a traceback. |
| 2 | Usage error from argparse. |
| 3 | A result was produced, but `AnalysisResult.partial` is true because the pipeline found unreadable directories/files, files over the size limit, parse failures, or parser diagnostics. JSON is written before this code is returned. |

Expected exclusions and skipped symlinks alone do not make the pipeline result partial.

## Scope and limitations

- Python and Dart source files are parsed for symbols, directives/import records, and comment markers. Dart support uses a small standard-library lexer and does not resolve types.
- Python imports and Dart relative/local `package:` directives contribute to the merged dependency graph. Dart resolution uses local pubspec names only; unknown packages are external and no package manager or repository code is run.
- File classes are heuristic.
- `.gitignore` is not honored; built-in excluded directories and explicit scanner exclusions apply.
- LOC is physical lines, including blank and comment lines.
- Framework detection reports recognized dependencies declared in manifests; it does not mean the repository uses them in code. Source-to-test matches use resolved imports and filename/path heuristics; they are not coverage and do not report whether tests pass.
- The health indicator is a heuristic based on static analysis, not a quality guarantee, correctness measure, or coverage measure. Missing or incomplete facts make individual components unavailable; older snapshots may not include `metrics.health`.
- AI, project tracking, and frontend functionality are not included. The optional API and persistence layer are separate from the analyzer core and require the `app` extra.
- Repository code is never imported or executed.
- ProjectLens JSON exports carry a `projectlens_format` marker. Existing marked JSON files within the scan size limit are excluded and reported as `Excluded`. The exact `--output` path is excluded for the current run, including when it is inside the analyzed tree.

## Project status

Milestone 1 and the GitHub, persistence, and API portions of milestone 2 are implemented. The PostgreSQL test pass, Docker Compose deployment, and CI workflow are documented in step 2.4; Docker Compose has been run and verified locally. The roadmap for remaining work is in [TODO.md](TODO.md). See [architecture](docs/ARCHITECTURE.md) for analysis and API contracts.

## Web interface

A React/TypeScript client lives in [`frontend/`](frontend/README.md). With the API running on port 8000:

```sh
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`. See the [frontend README](frontend/README.md#using-the-app) for what each screen shows.
