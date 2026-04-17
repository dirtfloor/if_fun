"""Tests for the canonical verb grammar table and lookup."""

import pytest

from if_fun.parser.grammar import CANONICAL_VERBS, MetaVerb, canonical_verb


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("take", "take"),
        ("get", "take"),
        ("pick", "take"),
        ("drop", "drop"),
        ("examine", "examine"),
        ("x", "examine"),
        ("look", "look"),
        ("l", "look"),
        ("inventory", "inventory"),
        ("i", "inventory"),
        ("open", "open"),
        ("unlock", "unlock"),
        ("use", "use"),
        ("wait", "wait"),
        ("z", "wait"),
    ],
)
def test_canonical_verb_from_alias(token: str, expected: str) -> None:
    assert canonical_verb(token) == expected


def test_canonical_verb_unknown_returns_none() -> None:
    assert canonical_verb("hovercraft") is None


def test_canonical_verbs_has_a_dozen_entries() -> None:
    assert len(CANONICAL_VERBS) >= 12


def test_meta_verb_values_are_stable() -> None:
    assert MetaVerb.SAVE.value == "save"
    assert MetaVerb.LOAD.value == "load"
    assert MetaVerb.QUIT.value == "quit"
    assert MetaVerb.HELP.value == "help"
