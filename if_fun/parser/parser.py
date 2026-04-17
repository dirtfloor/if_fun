"""Deterministic Phase A parser. Input string → ParsedCommand."""

from dataclasses import dataclass

from if_fun.ids import Direction, ItemId
from if_fun.parser.grammar import MetaVerb, canonical_verb
from if_fun.world.transitions import Action


@dataclass(frozen=True)
class DirectionCommand:
    direction: Direction


@dataclass(frozen=True)
class MetaCommand:
    verb: MetaVerb
    arg: str | None = None


@dataclass(frozen=True)
class ParseError:
    message: str


ParsedCommand = Action | DirectionCommand | MetaCommand | ParseError


_META_VERBS = {v.value for v in MetaVerb}


def parse(raw: str) -> ParsedCommand:
    """Normalize a raw input string into a ParsedCommand.

    Recognizes meta commands (save/load/quit/help), bare and "go"-prefixed
    direction words, single-word verbs, and verb-object pairs. Two-word
    verb aliases (e.g. "look at") are tried before single-word lookup so
    the grammar's multi-word aliases resolve correctly.
    """
    tokens = raw.strip().lower().split()
    if not tokens:
        return ParseError("empty input")

    # Meta commands (save / load / quit / help) with optional single arg.
    if tokens[0] in _META_VERBS:
        meta = MetaVerb(tokens[0])
        arg = tokens[1] if len(tokens) >= 2 else None
        return MetaCommand(verb=meta, arg=arg)

    # Bare direction word: "n", "north".
    if len(tokens) == 1:
        d = Direction.from_token(tokens[0])
        if d is not None:
            return DirectionCommand(direction=d)
        # Bare "go" (or any alias of it) is nonsense — it has no generic
        # verb-object meaning; fail fast rather than fall through to the
        # single-word verb branch which would return Action(verb="go").
        if canonical_verb(tokens[0]) == "go":
            return ParseError("'go' requires a direction")

    # "go north" / "walk south". If the second token is not a direction,
    # reject rather than fall through to the generic verb-object tail,
    # which would silently produce Action(verb="go", direct_object=...).
    if len(tokens) == 2 and canonical_verb(tokens[0]) == "go":
        d = Direction.from_token(tokens[1])
        if d is not None:
            return DirectionCommand(direction=d)
        return ParseError(f"unknown direction: {tokens[1]!r}")

    # Two-word verb alias (e.g. "look at ..."): try before single-word lookup.
    if len(tokens) >= 2:
        two_word = canonical_verb(" ".join(tokens[:2]))
        if two_word is not None:
            if len(tokens) == 2:
                return Action(verb=two_word)
            obj_token = "_".join(tokens[2:])
            return Action(verb=two_word, direct_object=ItemId(obj_token))

    # Single-word verb: "look", "inventory", "wait".
    if len(tokens) == 1:
        verb = canonical_verb(tokens[0])
        if verb is not None:
            return Action(verb=verb)
        return ParseError(f"unknown verb: {tokens[0]!r}")

    # Verb + one-or-more-token object: join object tokens with underscore.
    verb = canonical_verb(tokens[0])
    if verb is None:
        return ParseError(f"unknown verb: {tokens[0]!r}")
    obj_token = "_".join(tokens[1:])
    return Action(verb=verb, direct_object=ItemId(obj_token))
