# ProjectLens

ProjectLens is a local Python repository analyzer. Milestone 1 is complete: the installable CLI scans a repository, parses Python without executing it, resolves import-level dependencies, detects cycles, calculates basic metrics, and can export deterministic JSON.

## Install

Python 3.10 or newer is required. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate                 # POSIX; on Windows use .venv\Scripts\Activate.ps1
python -m pip install -e 'backend[dev]'
```

## Usage

```sh
python -m projectlens analyze /path/to/python/project
projectlens analyze . --output analysis.json
python -m projectlens analyze . --top 5 --max-diagnostics 3
```

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
- AI, database, API, project tracking, and frontend functionality are not included.
- Repository code is never imported or executed.
- ProjectLens JSON exports carry a `projectlens_format` marker. Existing marked JSON files within the scan size limit are excluded and reported as `Excluded`. The exact `--output` path is excluded for the current run, including when it is inside the analyzed tree.

## Project status

Milestone 1, the local Python analyzer CLI, is complete. The roadmap for GitHub integration, persistence, project tracking, AI, and frontend work is in [TODO.md](TODO.md). See [architecture](docs/ARCHITECTURE.md) for analysis and CLI contracts.
