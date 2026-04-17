# if_fun

Interactive Fiction game in the Infocom tradition, built as a showcase of agentic AI patterns.

## Stack

- Python, managed with `uv`
- Textual TUI, distributed as `uvx if_fun`
- OpenRouter API for LLM calls (mix of Opus / Sonnet / Haiku tiers)
- pydantic models for all agent I/O contracts (enables future Rust port)

## Development workflow

### Testing policy — mostly TDD, strict where deterministic

- **Strict TDD** (failing test first, then implementation) applies to all deterministic code:
  - State machines (room transitions, guards, effects)
  - Parser (canonical verb-object mapping)
  - Solvability Checker (BFS model checker)
  - Map Verifier (graph connectivity)
  - State Store (serialization, save/load)
  - Memory Curator (pure context-pruning logic)
  - Pydantic models and their validators
  - Anything without an LLM call in the hot path
- **Pragmatic testing** for agent/LLM code. Write tests *around* contracts, not behaviors:
  - Pydantic I/O schemas are verified (input validates, output parses)
  - Recorded-cassette tests for agent chains using saved LLM responses
  - A small smoke suite hits OpenRouter live, run pre-release, not per-commit
  - Don't try to TDD "the LLM writes good prose" — that way madness lies
- Follow the superpowers:test-driven-development skill for the deterministic slice.

### Pre-commit gate

All of these must pass before any commit:

- `uv run ruff format` — format
- `uv run ruff check --fix` — lint
- `uv run ty check` — type check
- `uv run pytest` — deterministic test suite green (cassette tests included; live LLM tests excluded)

Wire as a git pre-commit hook. Never commit with `--no-verify`. If a hook fails, fix the root cause; do not bypass.

### Evaluation and observability

- **Langfuse** is the LLM observability backend. Running in the user's home k8s cluster. Every LLM call is traced via the `langfuse` SDK (`@observe` decorator or manual spans). Config via env vars (`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
- **Pytest-based eval framework** lives under `evals/`. Every LLM-backed agent gets a dataset, a set of assertions, and parameterized tests over `(model, prompt_version)`.
- **Prompts are git-versioned.** Source of truth is Jinja templates in `if_fun/prompts/`. Optionally mirrored to Langfuse for their UI-based comparison features, but never fetched at runtime from Langfuse.
- **Eval tiers:**
  - Default / pre-commit — deterministic + cassette tests only. No live LLM calls.
  - `pytest -m eval_smoke` — small cases per agent. Nightly CI. Fast drift detection.
  - `pytest -m eval_full` — full dataset. Manual or weekly. Used when adopting a new model or changing a prompt.
- **When adopting a new model or changing a prompt**: run `eval_full` against the proposed change, compare to the previous run in Langfuse, record the decision in the spec or a dated notes file.

## Architecture

Every room is a three-layer stack:

1. **Mechanical** — state machine, pure Python, no LLM. Always present.
2. **Prose** — canonical description strings frozen on generation. Always present.
3. **Persona** — optional LLM agent overlay on ~5–15% of rooms.

Game runs in three phases: Generation (skeleton eager, prose parallel), Verification (model-checking + LLM critics in an evaluator-optimizer loop), Play (orchestrator-workers with routing and handoffs).

## Architecture doc — keep it current

Canonical architecture overview lives at `docs/architecture-overview.html`. **Any change to agent topology, phase structure, room model, or the pattern catalog must be reflected in that doc in the same change.** The doc is the source of truth for high-level architecture; code and specs refer to it.

When updating:
- Update the relevant section's prose and cast table
- Update the relevant SVG diagram if topology changed
- Add or revise pattern glossary entries in §7 if a new pattern is introduced
- Keep "Decisions already locked" in §1 accurate

## Specs and plans

- Specs: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plans: generated via superpowers:writing-plans skill
