"""Tests for the deterministic parser."""

import pytest

from if_fun.ids import Direction, ItemId
from if_fun.parser.grammar import MetaVerb
from if_fun.parser.parser import (
    DirectionCommand,
    MetaCommand,
    ParsedCommand,
    ParseError,
    parse,
)
from if_fun.world.transitions import Action


def _unwrap(cmd: ParsedCommand) -> ParsedCommand:
    assert not isinstance(cmd, ParseError), cmd.message
    return cmd


@pytest.mark.parametrize(
    ("raw", "direction"),
    [
        ("n", Direction.NORTH),
        ("north", Direction.NORTH),
        ("go north", Direction.NORTH),
        ("walk south", Direction.SOUTH),
        ("u", Direction.UP),
    ],
)
def test_parse_direction_words(raw: str, direction: Direction) -> None:
    cmd = _unwrap(parse(raw))
    assert isinstance(cmd, DirectionCommand)
    assert cmd.direction is direction


def test_parse_single_verb_action() -> None:
    cmd = _unwrap(parse("look"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "look"
    assert cmd.direct_object is None


def test_parse_verb_object_action() -> None:
    cmd = _unwrap(parse("take brass_key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_verb_alias_normalized() -> None:
    cmd = _unwrap(parse("get brass_key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"


def test_parse_multi_word_object_joined_with_underscore() -> None:
    cmd = _unwrap(parse("take brass key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_two_word_verb_alias() -> None:
    cmd = _unwrap(parse("look at brass_key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "examine"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_two_word_verb_with_multi_word_object() -> None:
    cmd = _unwrap(parse("look at brass key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "examine"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_meta_save_with_slot() -> None:
    cmd = _unwrap(parse("save slot1"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.SAVE
    assert cmd.arg == "slot1"


def test_parse_meta_load_with_slot() -> None:
    cmd = _unwrap(parse("load slot1"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.LOAD
    assert cmd.arg == "slot1"


def test_parse_meta_quit() -> None:
    cmd = _unwrap(parse("quit"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.QUIT
    assert cmd.arg is None


def test_parse_empty_is_error() -> None:
    cmd = parse("")
    assert isinstance(cmd, ParseError)


def test_parse_unknown_verb_is_error() -> None:
    cmd = parse("hovercraft eels")
    assert isinstance(cmd, ParseError)
