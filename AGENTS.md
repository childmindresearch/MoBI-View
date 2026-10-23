# Agent Instructions

Apply these requirements to new and edited code; do not assume existing code already complies. When modifying a file, it is your responsibility to ensure it complies in its entirety. However, do not make files you do not modify compliant.

# Agent Guide

MoBI-View visualizes real-time biosignals from Lab Streaming Layer (LSL) streams.
Follow [CONTRIBUTING.md](CONTRIBUTING.md) for contribution setup, licensing, and
the code of conduct. Use this guide for repository-specific agent conventions.

## Working Principles

- Read the relevant source, tests, and configuration before changing behavior.
- Keep changes focused; do not reformat unrelated code or add abstractions without
	an existing use case. Follow existing patterns before adding dependencies.
- Treat configuration and CI as the source of truth for tools and commands.
- Use clear Conventional Commit messages when asked to create commits.

## Architecture and Structure

The Python backend discovers LSL streams, manages data inlets, and broadcasts
samples over WebSocket. The SvelteKit frontend builds into static files served by
the Python server; there is no SvelteKit production server or API layer.

| Location | Responsibility |
| --- | --- |
| `src/MoBI_View/main.py` | Application startup and CLI entry point |
| `src/MoBI_View/core/` | Configuration, LSL discovery, data inlets, and exceptions |
| `src/MoBI_View/presenters/` | Stream management and application coordination |
| `src/MoBI_View/web/` | WebSocket handling, broadcasting, and static HTTP serving |
| `frontend/src/routes/` | Pages, layout, and global styles |
| `frontend/src/lib/components/` | Custom components, including the uPlot chart |
| `frontend/src/lib/components/ui/` | shadcn-svelte components backed by bits-ui |
| `frontend/src/lib/stores/` | WebSocket lifecycle and stream state |
| `frontend/src/lib/protocol.ts` | Frontend wire-protocol definitions and parsing |
| `tests/unit/` and `tests/smoke/` | Python unit and smoke tests |
| `scripts/test_streams.py` | Manual LSL stream-generation utility |

- Use `$lib` imports for shared frontend code. Keep helpers beside their page or
	component unless multiple use cases justify extracting them.
- Preserve existing component filenames and shadcn structure unless a task
	requires renaming. Do not introduce route groups, `$api` aliases, or a second UI
	directory just to match another project's conventions.
- The static adapter in `frontend/svelte.config.js` writes build output to
	`src/MoBI_View/web/static/`. Edit frontend sources, not generated bundles;
	rebuild when validating frontend integration with the Python server.

## Setup and Commands

Use Python 3.10–3.12, matching `pyproject.toml` and CI. CI uses Node.js 22.
`pylsl` also requires native `liblsl`; see
[README.md](README.md#installation) for platform-specific installation.

Run Python commands from the repository root:

| Command | Purpose |
| --- | --- |
| `uv sync` | Install the project and development dependencies |
| `uv run pre-commit install` | Install contribution hooks |
| `uv run mobi-view` | Start the application on localhost:8765 by default |
| `uv run pytest` | Run Python unit and smoke tests |
| `uv run ruff format --check` | Check Python formatting |
| `uv run ruff check` | Check Python lint rules |
| `uv run mypy .` | Check Python types |
| `uv run deptry ./src` | Check Python dependency usage |
| `uv run pre-commit run --all-files` | Run configured contribution hooks |

Run frontend commands from `frontend/`:

| Command | Purpose |
| --- | --- |
| `npm ci` | Install dependencies from the lockfile |
| `npm run dev` | Start Vite development mode; this script also runs `npm i` |
| `npm run check` | Sync SvelteKit and check Svelte/TypeScript types |
| `npm run format:check` | Check Prettier formatting |
| `npm test` | Run Vitest unit tests |
| `npm run build` | Build static assets into the Python package |

Run the relevant Python and frontend tests before completing changes (ie. if you modify only the front or backend, only run that testing suite). For code changes,
also run relevant checks above; build the frontend for frontend changes. Report
commands run, failures, and environment blockers accurately; never claim skipped
or blocked checks passed. CI is defined in
[.github/workflows/test.yaml](.github/workflows/test.yaml).

## Python Conventions

- Keep code compatible with the supported Python range, even though Ruff's
	configured target is `py312`.
- Use type annotations and Google-style docstrings, including module docstrings.
	Document public behavior and non-obvious edge cases without repeating types.
- Use `snake_case` for functions, modules, and variables, `PascalCase` for classes,
	and `SCREAMING_SNAKE_CASE` for constants.
- Follow `pyproject.toml`: Ruff uses four-space indentation and an 88-character
	line length. Lint rules cover annotations, docstrings, imports, errors, and
	unused code; mypy checks types.
- Keep LSL operations, presenter coordination, and web transport separate. Handle
	resource cleanup and thread/async boundaries explicitly.

## Frontend Conventions

- Use Svelte 5 runes and TypeScript with the existing SvelteKit, Tailwind 4,
	shadcn-svelte/bits-ui, and uPlot stack. Configuration enforces runes mode.
- Reuse existing UI components and styling patterns before adding alternatives.
- Use `camelCase` for logic, props, and handlers and `SCREAMING_SNAKE_CASE` for
	constants. Preserve protocol fields such as `stream_name` and `channel_labels`.
- Avoid `any`; use `unknown` with narrowing for untrusted values and unions or
	generics for known alternatives. Explain unavoidable uses of `any`.
- Add file-level JSDoc to new TypeScript modules and a component-purpose comment
	to new Svelte components. Document exported functions/classes and non-obvious
	behavior. Comments should explain intent rather than repeat obvious code.
- Use the committed Prettier configuration and its Svelte/Tailwind plugins, not
	the old template's four-space/no-semicolon/120-column rules. Do not reformat
	unrelated files to match inconsistent existing source.
- Vitest runs in a Node environment. Playwright, Zod, and oxlint are not currently
	configured; do not assume they are available.

## Tests and Cross-Layer Changes

- Test changed behavior, error paths, and cleanup. Documentation-only and
	configuration-only changes do not need artificial unit tests.
- Put Python tests in `tests/unit/` or `tests/smoke/`, using `test_<module>.py` and
	the existing pytest fixtures, mocks, and async test patterns.
- Colocate frontend tests as `*.test.ts`; Vitest discovers
	`frontend/src/**/*.test.ts`. Mock WebSocket and LSL boundaries rather than
	requiring live devices or external services in unit tests.
- Keep frontend protocol definitions and backend command/frame serialization in
	sync, updating tests on both sides. Data frames currently have no `type`
	discriminator; discovery responses use `discover_result`.
- Preserve bounded streaming buffers and dispose chart instances, subscriptions,
	timers, connections, and background workers when no longer needed.
- Preserve static-file path-containment checks and malformed-message handling
	when changing server request handling.
