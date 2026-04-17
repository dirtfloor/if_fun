"""Canonical verb grammar for the Phase A parser.

Aliases are lowercased strings matched exactly against caller-supplied tokens.
Some aliases span multiple words (currently "look at") — callers must try
two-word alias lookups before falling back to single-token lookup; a naive
split-on-whitespace-then-match will miss these.
"""

from enum import StrEnum

CANONICAL_VERBS: dict[str, frozenset[str]] = {
    "take": frozenset({"take", "get", "grab", "pick"}),
    "drop": frozenset({"drop", "put"}),
    "examine": frozenset({"examine", "x", "look at"}),
    "look": frozenset({"look", "l"}),
    "inventory": frozenset({"inventory", "i", "inv"}),
    "open": frozenset({"open"}),
    "close": frozenset({"close", "shut"}),
    "unlock": frozenset({"unlock"}),
    "lock": frozenset({"lock"}),
    "use": frozenset({"use"}),
    "wait": frozenset({"wait", "z"}),
    "go": frozenset({"go", "walk", "move"}),
}


class MetaVerb(StrEnum):
    SAVE = "save"
    LOAD = "load"
    QUIT = "quit"
    HELP = "help"


_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: verb for verb, aliases in CANONICAL_VERBS.items() for alias in aliases
}


def canonical_verb(token: str) -> str | None:
    """Return the canonical verb for a lowercased alias, or None if unknown."""
    return _ALIAS_TO_CANONICAL.get(token.strip().lower())
