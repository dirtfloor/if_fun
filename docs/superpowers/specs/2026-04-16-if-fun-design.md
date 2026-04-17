# if_fun — Design Spec

**Date:** 2026-04-16
**Status:** Draft · awaiting user review
**Companion:** `docs/architecture-overview.html` (canonical architecture topology with diagrams and pattern glossary)

---

## 1. Goals

- A playable Interactive Fiction game in the tradition of Infocom's *Zork*, generated and hosted by agentic AI systems.
- The player selects a **theme** (fantasy, space, noir, steampunk, etc.) and a **size** (small / large / xlarge). The system generates a cohesive, solvable world and runs it turn-by-turn.
- Serve as an explicit showcase of agentic AI patterns — we actively prefer designs that exhibit multiple named patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, reflection, tool use, handoff, hierarchical agents, ReAct, model checking, LLM-as-judge, context engineering, observability).
- Saveable game state. Saveable world templates (skeleton-only) for replay.
- Production-grade observability and eval: every LLM call traced, every prompt versioned, regression detection automated.

## 2. Non-goals

- Multiplayer.
- Real-time anything — this is turn-based text.
- Graphical rendering beyond TUI styling (colored text, a map panel, status line).
- Voice input / TTS.
- Cross-device sync. Saves live on the local filesystem.
- Winning over novice players — assume the audience has played Infocom or at least text adventures before.
- Localization. English only for v1.

## 3. Stack

- **Language:** Python, managed with `uv`. All scripts run via `uv run`.
- **UI:** Textual TUI. Distributed as `uvx if_fun`.
- **LLM provider:** OpenRouter. Mixed model tiers (Opus-class, Sonnet-class, Haiku-class) chosen per agent by cost-vs-stakes.
- **Structured outputs:** pydantic v2 across the board. Every agent has a typed input schema and a typed output schema.
- **LLM client:** Either the `openai` SDK pointed at OpenRouter (simplest) or `pydantic-ai` (more ergonomic for structured outputs). Decision: **`pydantic-ai`** — cleaner contract enforcement and it natively handles structured output + tool use. Caveat: verify OpenRouter backend support before committing (open risk in §16).
- **Observability:** Langfuse. Self-hosted in user's home k8s cluster. `@observe` on every LLM call.
- **Formatter / linter:** ruff.
- **Type checker:** ty.
- **Tests:** pytest.
- **Future port:** Rust is a plausible target once agent contracts stabilize. Pydantic models map cleanly to serde structs.

## 4. Architecture Summary

The architecture doc at `docs/architecture-overview.html` is the canonical visual reference. This spec is the actionable document.

Every room has a **three-layer stack**:

| Layer | What | Who runs it |
|---|---|---|
| **1 — Mechanical** | State machine: variables, transitions, guards, effects | Pure Python, no LLM |
| **2 — Prose** | Canonical description strings, frozen at generation | String lookup |
| **3 — Persona** | Optional LLM agent overlay with voice, goals, optional autonomy | LLM |

The game runs in **three phases**:

1. **Generation** — build the world skeleton (map, puzzles, placements) and freeze the prose layer. Skeleton eager; prose lazy only in the sense that it's generated once on world creation, not regenerated per play.
2. **Verification** — deterministic checks (map connectivity, puzzle solvability via BFS) and LLM critics (story coherence, difficulty), looped through an Editor until all pass or a 3-iteration cap fires.
3. **Play** — turn-by-turn orchestration via the Game Master with a deterministic hot path and a ReAct cold path.

## 5. Room Model (Layer 1: Mechanical)

Each room is a state machine. The world state is the composition of all room state machines + player inventory + global flags.

### 5.1 State variables

Universal per room:

- `visited: bool`
- `items_present: set[ItemId]`
- `occupants: set[MobId]`
- `event_ids: list[EventId]` — append-only references into the world-level `event_log`
- `flags: dict[str, Any]` — room-specific, schema declared at generation

The authoritative event store lives once at the world level (`WorldState.event_log`); rooms hold only id references. This keeps saves flat and avoids duplicating event bodies.

Room-specific examples (declared by the Puzzle Designer per room):

- `door_north: Literal["locked", "unlocked", "broken"]`
- `chandelier: Literal["hanging", "fallen", "shattered"]`
- `altar: Literal["dormant", "active", "desecrated"]`

### 5.2 Transitions

Each transition is a pydantic model with:

```python
class Transition(BaseModel):
    id: str                          # stable identifier for verification + hints
    name: str                        # human-readable ("unlock north door")
    trigger: Trigger                 # player action, mob action, or time tick
    guards: list[Guard]              # preconditions (pydantic-validated)
    effects: list[Effect]            # state mutations + event emission
    narration_hint: str | None       # optional templating seed for the narrator
```

Guards and effects are themselves pydantic discriminated unions. The set of allowed guard/effect types is fixed and finite so the Solvability Checker can reason about them symbolically.

### 5.3 Composition

The world state is a pydantic model:

```python
class WorldState(BaseModel):
    rooms: dict[RoomId, RoomState]
    player: PlayerState
    globals: dict[str, Any]
    turn: int
    event_log: list[Event]
```

`WorldState` is the single serialization unit for saves. Every mutation goes through a `StateStore` service that validates transitions and appends events.

## 6. Phase 1 — Generation

### 6.1 Pipeline (sequential with parallel fan-out)

```
(theme, size)
  → World Architect       → concept document
  → Map Designer          → room graph (nodes, edges, exits)
  → Puzzle Designer       → puzzle DAG as state-machine fragments
  → Inhabitant Designer   → item + mob placements
  → Prose Writer × N      [parallel] canonical descriptions for every room/item/mob
  → Story Weaver          → opening, ending, story beats, NPC dialogue seeds
  → Sentience Picker      → which rooms get persona overlay
```

### 6.2 Agent contracts

Each agent is a function with typed input and output. Pseudocode signatures:

```python
async def world_architect(theme: Theme, size: SizeTier) -> WorldConcept: ...
async def map_designer(concept: WorldConcept) -> MapGraph: ...
async def puzzle_designer(concept: WorldConcept, map: MapGraph) -> PuzzleDAG: ...
async def inhabitant_designer(puzzles: PuzzleDAG, map: MapGraph) -> Placements: ...
async def prose_writer(entity: RoomSpec | ItemSpec | MobSpec, context: WorldContext) -> ProseBlock: ...
async def story_weaver(all_prose: ProseBundle, puzzles: PuzzleDAG) -> StoryArc: ...
async def sentience_picker(story: StoryArc, rooms: list[RoomSpec]) -> list[RoomId]: ...
```

Each agent's prompt is a Jinja template in `if_fun/prompts/`.

### 6.3 Size mapping

| Size | Rooms | Puzzles | Sentient rooms | Named antagonists | Gen budget (rough) |
|---|---|---|---|---|---|
| small | 8–12 | 2–3 | 1 | 0–1 | ~1 min |
| large | 25–35 | 6–8 | 2–4 | 1–2 | ~3 min |
| xlarge | 60–80 | 15+ | 5–8 | 3–5 | ~8 min |

Budgets are wall-clock targets, not hard caps. Prose Writer parallelism is bounded by OpenRouter concurrency limits (assume 10 concurrent by default; tune after first live run).

### 6.4 Theme handling

Theme is a free-form string supplied by the player. It is injected into every generator's system prompt as a constraint. No separate Theme Warden agent. Story Critic catches violations in verification.

A small curated list of "starter themes" (`fantasy`, `space`, `noir`, `steampunk`, `gothic-horror`, `post-apocalyptic`) is offered for quick selection in the TUI, but the player can always type a custom theme.

## 7. Phase 2 — Verification

### 7.1 Pipeline (parallel verifiers → evaluator-optimizer)

```
Generated World
  → [Map Verifier, Solvability Checker, Story Critic, Difficulty Judge]  (parallel)
  → Editor
    → Approved     — ship to player
    → Revise       — loop back to specific upstream generator with feedback
```

### 7.2 Map Verifier (deterministic)

- All rooms reachable from start.
- No orphan rooms, no orphan exits.
- Geometry consistency: if A→B is "north", B→A is "south" (unless explicitly marked one-way).
- Exit count distribution within expected bounds per size.

### 7.3 Solvability Checker (model checking)

BFS over the composed world state machine. Start state is the initial `WorldState`; goal predicate is the `win_condition` from the `StoryArc`. Outputs:

- `solvable: bool`
- `winning_trace: list[Action] | None` — shortest path to win
- `dag_depth: int` — longest puzzle-dependency chain
- `deadends: list[StateHash]` — states with no outgoing legal transitions that aren't the win state

State space is bounded by design: a dozen-ish boolean/enum flags, inventory items, room occupancy. For `small` and `large` tiers, BFS runtime is milliseconds. For `xlarge`, runtime is seconds to tens of seconds depending on state-space branching. Mitigations: cap `xlarge` at ~20 puzzles regardless of room count, cap inventory size, and enforce a hard timeout (default 60s) that triggers fail-loud rather than hang.

### 7.4 Story Critic (LLM)

Reads all canonical prose end-to-end. Output schema:

```python
class StoryCritique(BaseModel):
    coherent: bool
    tonal_violations: list[TonalViolation]     # prose that breaks theme
    contradictions: list[Contradiction]         # facts that conflict
    loose_ends: list[LooseEnd]                  # un-Chekhovian guns
    overall_score: int                          # 0-100
    comments: str
```

### 7.5 Difficulty Judge (LLM)

Reads `winning_trace` + `PuzzleDAG`. Scores difficulty against the requested `SizeTier`. Output schema includes flags when difficulty is too far from target.

### 7.6 Editor (evaluator-optimizer)

Reads all verifier reports. If any fail:

1. Classify the failure (structural vs. narrative).
2. Pick the upstream generator to re-invoke (e.g., prose violations → Prose Writer for the flagged rooms only; puzzle solvability failure → Puzzle Designer with the deadend state as feedback).
3. Construct feedback payload and re-invoke.
4. Rerun verifiers.
5. Cap at 3 total iterations. On non-convergence, fail loudly with a user-facing message (e.g., *"Could not generate a solvable xlarge space world after 3 attempts. Try a different theme or a smaller size."*)

## 8. Phase 3 — Play

### 8.1 Turn loop

```
Player input
  → Parser (deterministic, canonical verbs)
    → known verb: structured Action
    → unknown: Intent Interpreter (LLM router)
  → Game Master
    → hot path: apply transition → dispatch Narrator → return
    → cold path: ReAct loop (reason, probe state, propose transition, observe, revise)
  → [handoff to Room Persona if current room is sentient]
  → [Mob Agents tick in parallel if present in room or adjacent]
  → Memory Curator (prepares next-turn context)
  → Turn output to player
```

### 8.2 Hot path vs cold path

**Hot path.** A canonical verb with resolved objects that triggers a known transition. No reasoning needed. Zero or one LLM call (just the Narrator for prose). Covers ~80% of turns.

**Cold path.** Input that the parser can't resolve deterministically and that the Intent Interpreter flags as "creative/free-form." GM enters a ReAct loop:

- Observe current state via tool calls (`get_room_state`, `get_inventory`, `get_mob_states`).
- Reason about player intent.
- Propose a candidate `Action` or narration-only response.
- Simulate the action (dry run the transition).
- If legal, commit; if not, revise or reject with a reason.
- Hand off to Narrator.

The cold path is capped at 4 reasoning iterations per turn. (The cap is slightly higher than the Editor's 3 because each cold-path iteration is a single cheap LLM call — a state probe or a simulate-and-retry — whereas each Editor iteration re-runs an entire expensive generator. The two caps are unrelated.)

### 8.3 Mob tiers

- **Reactive mobs** (rats, goblins, patrol guards): one LLM call per turn. Input: local state + last few events. Output: single `MobAction`. Haiku tier.
- **Planner mobs** (named antagonists, recurring NPCs): ReAct loop with persistent state (`goal`, `current_plan: list[Action]`, `plan_status`). Revise plan when a step fails. Sonnet tier. Tick per turn.

### 8.4 Room Persona tiers

- **Passive persona** (most sentient rooms): GM hands off narration when player is present. Single LLM call. Sonnet.
- **Autonomous persona** (a few "signature" rooms — e.g., a sentient dungeon heart): ReAct loop. Holds goals, reasons about player behavior, can initiate effects (dim lights, produce whispers, reveal secrets). Sonnet.

### 8.5 Memory Curator

Maintains rolling context per playthrough. Responsibilities:

- Prune event log when it exceeds token budget.
- Summarize distant events into a compact recap.
- Decide which events are relevant to include in each LLM call (e.g., all events in the current room + last 10 events globally + any event involving a present mob).
- Small LLM call for summarization; everything else is deterministic.

## 9. State Model and Save Format

### 9.1 Save format

**Single JSON file** per save slot. Full snapshot. Path: `~/.local/share/if_fun/saves/<slot>.json`. Schema is `WorldState` serialized via pydantic.

Rationale: saves are always read whole and written whole; never a partial read. A single JSON file is trivial, diffable, human-readable, and easy to version as the schema evolves.

### 9.2 Template format

A **template** is a save file with dynamic state stripped out. Contains:

- `MapGraph`
- `PuzzleDAG`
- Canonical prose bundle
- `StoryArc`
- List of sentient rooms + persona specs
- Mob specs and placements

Regenerated every playthrough: reactive-mob current state, event logs, player state, globals. This means one template yields many distinct-feeling playthroughs.

Template path: `~/.local/share/if_fun/templates/<name>.json`.

### 9.3 Schema versioning

Every save and template carries `schema_version: int`. A `schema_migrations/` module holds upgrade functions. On load, if the saved version is older, migrations run in sequence. If newer, load fails with a clear error.

## 10. Prompt Caching Strategy

Every play-time LLM call has this prompt structure:

```
[stable world skeleton]           ← cache prefix
[room-scoped stable context]      ← optional nested cache
[turn-specific context]           ← fresh every turn
[player input + recent events]    ← fresh
```

Anthropic cache breakpoint inserted at the end of the stable world skeleton. On tools with prompt caching, expect high hit rates after turn 1.

Caching scope for v1 is the single outermost breakpoint. Room-scoped nested caching is a later optimization if token bills warrant it.

## 11. Evaluation and Observability

### 11.1 Langfuse

- Every LLM call wrapped via `@observe` or manual spans.
- Config via env vars: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.
- Trace metadata: agent name, prompt version, model, phase, world_id, turn_id.

### 11.2 Eval framework

Directory: `evals/`. Every LLM-backed agent has a dataset + checks + parameterized pytest module.

```
evals/
  conftest.py              # fixtures: model matrix, langfuse client, cassette loader
  datasets/
    world_architect/cases.jsonl
    map_designer/cases.jsonl
    intent_interpreter/cases.jsonl
    narrator/cases.jsonl
    ...
  checks/                  # pydantic + domain assertions
    world_architect.py
    ...
  judges/                  # Jinja templates for LLM-judge scoring
    coherence.j2
    voice_consistency.j2
  test_<agent>_eval.py     # parametrized over (model, prompt_version) × cases
```

### 11.3 Eval tiers (pytest markers)

- **default / pre-commit** — deterministic and cassette tests only. No live LLM calls.
- **`pytest -m eval_smoke`** — ~5 cases per agent. Nightly CI. Fast drift detection.
- **`pytest -m eval_full`** — full dataset. Manual or weekly. Required when adopting a new model or changing a prompt.

### 11.4 Prompt source of truth

Prompts live in `if_fun/prompts/` under git. Jinja templates. Langfuse receives **traces and scores**, not prompt templates. This keeps code and prompt changes atomic in one commit and preserves `git bisect`.

Optional: one-way mirror prompts to Langfuse for their comparison UI, using a helper script — never fetched at runtime.

### 11.5 Evaluation matrix (v1)

| Agent | Eval approach | Scoring |
|---|---|---|
| Map Designer | Generate → run Map Verifier | deterministic |
| Puzzle Designer | Generate → run Solvability Checker | deterministic |
| Intent Interpreter | Golden utterance → expected action mapping | deterministic |
| Narrator | State-delta → prose. Judge on tone, non-contradiction | LLM-judge |
| Room Persona | Persona spec + trigger → response. Judge on voice consistency | LLM-judge |
| Mob Agent | Mob state + perception → action. Assert legal; judge believability | mixed |
| Story Critic / Difficulty Judge / Editor | Known-bad world dataset → must flag expected defects | deterministic |

## 11.6 Standard logging (non-LLM)

Deterministic code uses Python's standard `logging` module with a sensible default config. INFO for phase transitions, DEBUG for transition decisions, WARNING for verifier findings, ERROR for fail-loud paths. Logs are written to stderr and to `~/.local/share/if_fun/logs/<date>.log`. This is independent of Langfuse, which only covers LLM calls.

## 11.7 Secrets and API keys

All secrets via environment variables. `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. Never logged, never written to save files, never included in traces. `.env` files supported for local development via `python-dotenv`; `.env` is gitignored by default. A `.env.example` lists required keys with placeholder values.

## 11.8 Cost guardrails

World generation can ramp costs quickly, especially on `xlarge`. The CLI exposes:

- `--max-cost-usd <n>`: aborts a generation if estimated cumulative spend (from Langfuse token accounting) exceeds the cap. Default: unlimited.
- `--dry-run`: runs generation with all LLM calls replaced by fixture responses (cassette-style). Useful for smoke-testing prompts and flow.

## 12. Testing Strategy

### 12.1 TDD policy

- **Strict TDD** for deterministic code: state machines, parser, Solvability Checker, Map Verifier, StateStore, Memory Curator pruning logic, pydantic validators.
- **Pragmatic testing** for LLM code: pydantic contract tests (inputs validate, outputs parse), recorded-cassette tests for agent chains, eval suite for subjective quality.

### 12.2 Cassette tests

Use `vcrpy` or equivalent to record LLM HTTP traffic once, replay deterministically. Cassettes checked in. Re-recording requires a dedicated command and is reviewed as a diff like any other artifact.

### 12.3 Live-LLM tests

Excluded from pre-commit. Live eval runs:

- `pytest -m eval_smoke` — CI nightly.
- `pytest -m eval_full` — manual or weekly.

### 12.4 End-to-end smoke

One fixture: generate a **small world** with a fixed seed and a fixed theme, play a scripted sequence of 10 canonical commands, assert the state machine ends in a known state. Uses cassettes for all LLM calls.

## 13. Directory Layout

```
if_fun/
  __init__.py
  cli.py                         # entry point for uvx if_fun
  tui/
    app.py                       # Textual App
    widgets/
      prose_pane.py
      map_pane.py
      status_line.py
      input_line.py
  world/
    state.py                     # WorldState, RoomState, PlayerState pydantic models
    transitions.py               # Transition, Guard, Effect discriminated unions
    store.py                     # StateStore service
    events.py                    # Event types + store
  parser/
    grammar.py                   # canonical verb-object grammar
    parser.py                    # deterministic parser
  agents/
    world_architect.py           # all @observe-wrapped
    map_designer.py
    puzzle_designer.py
    inhabitant_designer.py
    prose_writer.py
    story_weaver.py
    sentience_picker.py
    map_verifier.py              # deterministic
    solvability_checker.py       # deterministic
    story_critic.py
    difficulty_judge.py
    editor.py
    intent_interpreter.py
    game_master.py
    narrator.py
    room_persona.py
    mob_reactive.py
    mob_planner.py
    memory_curator.py
    hint_giver.py
  prompts/                       # Jinja templates, source of truth
    world_architect.j2
    ...
  openrouter/
    client.py                    # pydantic-ai client factory
    models.py                    # model-tier enum + routing
  save/
    save_format.py               # schema, read/write
    schema_migrations/
      __init__.py
      # migration modules added as the schema evolves
  templates/                     # template serialization
    template_format.py

evals/
  conftest.py
  datasets/
  checks/
  judges/
  test_<agent>_eval.py

tests/
  world/
  parser/
  agents/
  save/
  e2e/
    test_smoke_small_world.py
  fixtures/
    cassettes/

docs/
  architecture-overview.html     # canonical topology reference
  superpowers/specs/
    2026-04-16-if-fun-design.md  # this file

pyproject.toml
uv.lock
.pre-commit-config.yaml
CLAUDE.md
README.md
```

### 13.1 Package boundary invariant

The `world/`, `parser/`, and `save/` packages **must not import from `agents/`** or any LLM-calling code. This is the deterministic substrate. Enforce with a pytest that scans imports, or a ruff rule.

## 14. Dependencies

Core runtime:

- `textual` — TUI framework
- `pydantic` v2 — models and validation
- `pydantic-ai` — LLM client with structured outputs (pending OpenRouter compatibility check)
- `langfuse` — observability
- `jinja2` — prompt templates
- `typer` — CLI argument parsing for `if_fun` entry point

Dev:

- `pytest`, `pytest-asyncio`, `pytest-recording`
- `ruff`, `ty`
- `pre-commit`

## 15. MVP Phasing

Four phases, each independently shippable and testable. Each phase ends with a green pre-commit gate and a working `uvx if_fun` for what's been built.

**One implementation plan per phase.** This spec is the overall roadmap; each phase should be turned into its own `docs/superpowers/plans/YYYY-MM-DD-if-fun-phase-<X>-plan.md` by the writing-plans skill when its turn comes. Don't try to plan Phase B until Phase A has surfaced reality.

### Phase A — Walking Skeleton

- `pyproject.toml`, `uv.lock`, pre-commit hook
- `WorldState`, `RoomState`, `Transition`, `StateStore` — full TDD
- Parser with a dozen canonical verbs
- Minimal Textual app: prose pane + input line
- A hardcoded 5-room test world (no LLM involved)
- Save / load
- Deterministic Map Verifier and Solvability Checker, both TDD
- Playable: the hardcoded world can be won via typed commands

**Exit gate:** strict TDD coverage of the substrate. No LLM code yet.

### Phase B — Agentic Generation

- OpenRouter client + model tier registry
- Langfuse wiring (every LLM call traced)
- World Architect → Map Designer → Puzzle Designer → Inhabitant Designer pipeline
- Prose Writer with parallel fanout
- Story Weaver, Sentience Picker (minimum — not yet integrated into play)
- Story Critic, Difficulty Judge, Editor revision loop (3-iteration cap)
- Generated worlds replace the hardcoded test world
- First eval datasets + cassette tests for each agent

**Exit gate:** `small` worlds generate and verify end-to-end. Editor loop tested for both converge and fail-loud paths. `eval_smoke` runs green.

### Phase C — Living World

- Intent Interpreter (cold-path routing)
- Game Master with hot and cold paths
- Narrator
- Reactive Mob Agents
- Memory Curator
- Hint Giver (uses `winning_trace` from Solvability Checker)
- TUI map pane (reveals as player explores)

**Exit gate:** generated worlds are fully playable. Unknown player input handled gracefully via ReAct cold path. Hints escalate correctly.

### Phase D — Polish

- Room Personas (passive and autonomous)
- Planner Mobs (named antagonists)
- Template serialization (save-as-template)
- Larger size tiers (`large`, `xlarge`)
- Eval matrix completion with `eval_full` datasets
- Distribution: `uvx if_fun` from PyPI

**Exit gate:** ships to someone who isn't us and they can play it.

## 16. Open Risks

Not blockers — things to validate early in Phase A / B.

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `pydantic-ai` incompatible with OpenRouter | Medium | High | Test in Phase A spike; fall back to `openai` SDK pointed at OpenRouter if needed. Retain pydantic models either way. |
| Solvability Checker state space blows up on `xlarge` | Low | High | Design puzzle DAGs to keep branching factor bounded. Cap `xlarge` puzzle count. Add a timeout with fail-loud. |
| OpenRouter rate limits bite Prose Writer fan-out | Medium | Low | Start with concurrency=10, tune. Add exponential backoff. |
| Editor revision loop oscillates | Medium | Medium | 3-iteration cap + fail loud. Log all oscillations. |
| Prompt cache hit rate lower than hoped | Medium | Low (cost only) | Measure in Phase B. Consider nested breakpoints in Phase D if needed. |
| Textual's scrollback + live-updating prose plays badly | Low | Medium | Prototype the prose pane in Phase A with a scripted generator. |
| Live-LLM tests too expensive for frequent CI | Medium | Low | `eval_smoke` is small; run nightly not per-PR. Use cheapest models where possible. |

## 17. References

- Anthropic, *Building Effective Agents* — https://www.anthropic.com/research/building-effective-agents
- Anthropic, *Effective Context Engineering for AI Agents* — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* — https://arxiv.org/abs/2210.03629
- Shinn et al., *Reflexion* — https://arxiv.org/abs/2303.11366
- Zheng et al., *MT-Bench / Judging LLM-as-a-Judge* — https://arxiv.org/abs/2306.05685
- Langfuse docs — https://langfuse.com/docs
- pydantic-ai — https://ai.pydantic.dev/
- Textual — https://textual.textualize.io/
- OpenRouter — https://openrouter.ai/
- Model checking — https://en.wikipedia.org/wiki/Model_checking
- Infocom's Z-machine (historical context) — https://en.wikipedia.org/wiki/Z-machine
