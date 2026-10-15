# ProjectLens

ProjectLens is a local Python repository analyzer. Milestone 1 is complete: the installable CLI scans a repository, parses Python without executing it, resolves import-level dependencies, detects cycles, calculates basic metrics, and can export deterministic JSON.

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
```

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

## Docker Compose (unverified)

Docker is unavailable in the environment where these files were authored, so
the image build and `docker compose up` have not been verified. The local
PostgreSQL migrations and a real API flow have been verified separately. Copy
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

- Python parsing only; other files are discovered and measured but not parsed for symbols or imports.
- The dependency graph represents Python import-level file dependencies, not runtime calls.
- File classes are heuristic.
- `.gitignore` is not honored; built-in excluded directories and explicit scanner exclusions apply.
- LOC is physical lines, including blank and comment lines.
- No coverage, health, or risk scores are produced.
- AI, project tracking, and frontend functionality are not included. The optional API and persistence layer are separate from the analyzer core and require the `app` extra.
- Repository code is never imported or executed.
- ProjectLens JSON exports carry a `projectlens_format` marker. Existing marked JSON files within the scan size limit are excluded and reported as `Excluded`. The exact `--output` path is excluded for the current run, including when it is inside the analyzed tree.

## Project status

Milestone 1 and the GitHub, persistence, and API portions of milestone 2 are implemented. The PostgreSQL test pass, Docker Compose deployment, and CI workflow are documented in step 2.4; Docker files have not been run locally. The roadmap for remaining work is in [TODO.md](TODO.md). See [architecture](docs/ARCHITECTURE.md) for analysis and API contracts.
