# Python Conventions

Use the owning project's `pyproject.toml`, Makefile, and CI workflows as the
source of truth. They define the supported Python version, dependencies, tools,
and validation commands.

## Project Types

### Installable Packages

Installable Python projects use `uv`, a committed `uv.lock`, Hatchling, and a
`src` layout:

```text
pyproject.toml
uv.lock
src/<package>/
tests/
```

Use the Python version range declared in `pyproject.toml`.

### Validation Projects

Some repositories use Python only for validation scripts and tests. Their
`pyproject.toml` sets `tool.uv.package = false`, and they do not have a build
backend or `src` package. The docs repository runs its Python validator and
`unittest` suite directly with `python3`.

Follow each repository's layout and commands. Do not apply package conventions
to a validation project.

## Service Layout

Runtime services commonly contain:

- `config/` for Pydantic settings;
- `controllers/` for HTTP or gRPC adapters;
- `models/` for typed API and domain contracts;
- `lib/` or `services/` for business and integration logic;
- `main.py` for application construction and entry points.

These directories are optional. Add a layer only when the service needs it.
Keep generated code isolated and excluded from manual formatting, linting, type
checking, and coverage where configured.

## Style and Type Checking

- Run Ruff only in projects that configure it. Follow the project's enabled
  rules and line length.
- Run `ty` only in projects that configure it. Do not assume every project uses
  the same strictness.
- Use modern type annotations and explicit return types for public code.
- Never log credentials, tokens, full API keys, or sensitive payloads.

## Runtime Services

- Read environment configuration through Pydantic Settings.
- Use the service's configured environment-variable prefix.
- Reject unknown fields when required by an external protocol.
- Wrap external clients and translate transport failures into service-level
  errors.
- Construct applications through factories or explicit composition functions.
- Close long-lived clients and other resources during application shutdown.

## Tests

Services, tooling projects, and the Dify builder use pytest. Platform, client,
and docs validation use `unittest`. Use pytest-asyncio only in projects that
configure it.

Prefer in-process API tests, dependency overrides, mock transports, temporary
paths, and small fakes over network-dependent tests.

Each project under `tooling/cli_tools/` has its own lockfile and enforces at
least 80 percent test coverage. Reporting commands consumed by automation must
remain non-interactive.

## Validation

Install the development dependency group or optional extra declared by the
project. Run `make check` when the repository provides it. Common commands for
installable projects are:

```bash
uv run ruff check
uv run ruff format --check
uv run ty check
uv run pytest
```

Use the exact paths, extras, frozen options, and additional checks defined by
the owning repository.
