# ProjectLens

ProjectLens is an open-source developer platform combining deterministic repository analysis with project and roadmap tracking.

It will measure repository structure, dependencies, code health, and development activity, then connect that evidence to planned work. An optional AI layer will explain structured analysis results later.

## Current status

Planning and repository structure only. No analysis engine, installable package, API, or frontend has been implemented yet.

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

## Planned CLI

These commands describe the milestone acceptance criteria; they do not work yet.

```bash
python -m projectlens analyze /path/to/python/project
python -m projectlens analyze . --output analysis.json
```

An installed `projectlens` command will expose the same interface.

## Setup and Docker

Installation and test commands will be added with the first executable milestone. Docker and Docker Compose setup will be documented when backend services are introduced. There are currently no runtime dependencies or containers to configure.

## Screenshots

Screenshots will be added after the frontend milestone.

## Contributing

Development proceeds in small, reviewable steps, with a commit after each completed step. Start with the next unfinished item in [TODO.md](TODO.md). A dedicated contribution guide, code of conduct, and license will be added before the public release. No open-source license has been selected yet.
