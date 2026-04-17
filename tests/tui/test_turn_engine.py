from pathlib import Path

import pytest

from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


def test_describe_current_room_returns_start_description() -> None:
    eng = TurnEngine(build_five_room_world())
    text = eng.describe_current_room()
    assert "antechamber" in text.lower()


def test_submit_move_east_then_take_key() -> None:
    eng = TurnEngine(build_five_room_world())
    out1 = eng.submit("east")
    assert "vault" in out1.lower()
    eng.submit("take brass_key")
    assert "brass_key" in eng.world.player.inventory


def test_submit_look_returns_current_room_description() -> None:
    eng = TurnEngine(build_five_room_world())
    text = eng.submit("look")
    assert text == eng.describe_current_room()


def test_submit_inventory_lists_held_items() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    text = eng.submit("inventory")
    assert "brass_key" in text


def test_submit_illegal_returns_friendly_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("north")  # locked without brass_key
    assert "can't" in out.lower() or "cannot" in out.lower()


def test_submit_parse_error_returns_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("hovercraft eels")
    assert "don't" in out.lower() or "unknown" in out.lower()


def test_submit_quit_returns_sentinel() -> None:
    eng = TurnEngine(build_five_room_world())
    assert eng.submit("quit") == "__QUIT__"


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    eng.save("slot1")

    eng2 = TurnEngine(build_five_room_world())
    eng2.load("slot1")
    assert eng2.world == eng.world


def test_winning_adds_win_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = ""
    for cmd in [
        "east",
        "take brass_key",
        "west",
        "south",
        "take silver_key",
        "take crystal",
        "north",
        "north",
        "north",
    ]:
        out = eng.submit(cmd)
    assert "won" in out.lower()
    assert eng.world.is_won()
