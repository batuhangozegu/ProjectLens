# ProjectLens

ProjectLens is an open-source developer platform combining deterministic repository analysis with project and roadmap tracking.

It will measure repository structure, dependencies, code health, and development activity, then connect that evidence to planned work. An optional AI layer will explain structured analysis results later.

## Current status

The installable Python package and CLI foundation are implemented. The analysis engine, API, and frontend have not been implemented yet.

The first milestone is a local Python repository analyzer. GitHub integration, storage, project tracking, and AI follow in separate milestones. The frontend comes last.

## Architecture

The analysis core will operate independently of HTTP, databases, and AI providers. A CLI will invoke the same pipeline that a future backend can call.

```text
Local repository
  -> scan and classify files
  -> parse Python source
  -> extract symbols and imports
  -> resolve local dependencies
  -> construct dependency graph and detect cycles
  -> compute metrics and source comment markers
  -> produce structured results
  -> terminal summary / JSON export
```

See [architecture and directory plan](docs/ARCHITECTURE.md) and the [implementation checklist](TODO.md).

## CLI status

The package and CLI are installable. `--help` works, but analysis is not implemented yet; `analyze` exits with an explicit not-implemented message.

```bash
python -m projectlens analyze /path/to/python/project
python -m projectlens analyze . --output analysis.json
```

An installed `projectlens` command will expose the same interface.

## Setup and Docker

Python 3.10 or newer is required. From the repository root, create and activate a virtual environment, then install the package with its test tools.

PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "backend[dev]"
python -m projectlens --help
projectlens --help
Set-Location backend
pytest
```

POSIX shell:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e 'backend[dev]'
python -m projectlens --help
projectlens --help
cd backend
pytest
```

The package has no runtime dependencies; `pytest` is installed only by the `dev` extra. Repository analysis is not implemented yet. Docker and Docker Compose setup will be documented when backend services are introduced.

## Screenshots

Screenshots will be added after the frontend milestone.

## Contributing

Development proceeds in small, reviewable steps, with a commit after each completed step. Start with the next unfinished item in [TODO.md](TODO.md). A dedicated contribution guide, code of conduct, and license will be added before the public release. No open-source license has been selected yet.
