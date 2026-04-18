# if_fun

Interactive Fiction game in the Infocom tradition, built as a showcase of agentic AI patterns.

## Current status: Phase A (Walking Skeleton)

A deterministic substrate with a hardcoded 5-room test world. No LLM code yet.

## Running

```
uv sync
uv run if_fun play
```

Type `help` inside the game for commands.

## Development

```
uv run pre-commit run --all-files
uv run pytest
```

## Architecture

See `docs/architecture-overview.html` for the canonical design and `docs/superpowers/specs/2026-04-16-if-fun-design.md` for the spec.

Phase A implementation plan: `docs/superpowers/plans/2026-04-16-if-fun-phase-a-walking-skeleton.md`.
