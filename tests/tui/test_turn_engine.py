from pathlib import Path

import pytest

from if_fun.ids import RoomId
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


def test_describe_current_room_returns_start_description() -> None:
    eng = TurnEngine(build_five_room_world())
    text = eng.describe_current_room()
    assert "antechamber" in text.lower()


def test_describe_current_room_annotates_locked_exits() -> None:
    # From entry_hall without the brass_key, north is locked but east/south are open.
    eng = TurnEngine(build_five_room_world())
    text = eng.describe_current_room()
    # Find the exits line.
    exits_line = next(line for line in text.splitlines() if line.startswith("Exits:"))
    assert "north (locked)" in exits_line
    assert "east" in exits_line
    # The unlocked directions must not carry a suffix.
    assert "east (locked)" not in exits_line
    assert "south (locked)" not in exits_line


def test_describe_current_room_unlocks_exit_after_guard_passes() -> None:
    # Once the player holds brass_key, north from entry_hall is no longer locked.
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    eng.submit("west")
    text = eng.describe_current_room()
    exits_line = next(line for line in text.splitlines() if line.startswith("Exits:"))
    assert "(locked)" not in exits_line


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
    assert "brass key" in text


def test_submit_blocked_locked_direction_says_locked() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("north")  # locked without brass_key
    assert "locked" in out.lower()
    # It should name the direction so players orient themselves.
    assert "north" in out.lower()


def test_submit_blocked_wall_direction_says_cant_go_that_way() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")  # enter vault (only exit: west)
    out = eng.submit("north")
    assert "locked" not in out.lower()
    assert "can't" in out.lower() or "cannot" in out.lower()


def test_submit_parse_error_returns_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("hovercraft eels")
    assert "don't" in out.lower() or "unknown" in out.lower()


def test_submit_quit_returns_sentinel() -> None:
    eng = TurnEngine(build_five_room_world())
    assert eng.submit("quit") == "__QUIT__"


def test_help_advertises_only_implemented_verbs() -> None:
    """Help must match reality — no verbs listed that the engine rejects."""
    eng = TurnEngine(build_five_room_world())
    help_text = eng.submit("help").lower()
    # Implemented verbs — must appear
    for verb in ("look", "take", "drop", "examine", "open", "unlock", "inventory"):
        assert verb in help_text, f"help should list {verb!r}"
    # Unimplemented verbs — must not appear
    for verb in (" use ", " wait", "close", " lock "):
        assert verb not in help_text, f"help must not list unimplemented {verb!r}"


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    eng.save("slot1")

    eng2 = TurnEngine(build_five_room_world())
    eng2.load("slot1")
    assert eng2.world == eng.world


def test_open_locked_direction_reports_locked() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("open north")
    assert "locked" in out.lower()
    # Player must not have moved.
    assert eng.world.player.location == "entry_hall"


def test_open_open_direction_reports_nothing_special() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("open east")  # east is a plain unlocked exit
    assert "locked" not in out.lower()
    assert eng.world.player.location == "entry_hall"


def test_open_wall_direction_reports_nothing_to_open() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")  # enter vault, no exit north
    out = eng.submit("open north")
    assert "locked" not in out.lower()
    assert "nothing" in out.lower() or "no" in out.lower()


def test_unlock_locked_direction_reports_locked_and_suggests_key() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("unlock north").lower()
    assert "locked" in out
    assert "key" in out
    assert eng.world.player.location == "entry_hall"


def test_unlock_open_direction_reports_not_locked() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("unlock east").lower()
    assert "locked" not in out or "isn't locked" in out or "not locked" in out


def test_open_without_direction_is_friendly_error() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("open").lower()
    assert "direction" in out or "what" in out or "can't" in out


def test_drop_held_item_moves_it_to_current_room() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    assert "brass_key" in eng.world.player.inventory

    out = eng.submit("drop brass_key").lower()
    assert "dropped" in out or "drop" in out
    assert "brass_key" not in eng.world.player.inventory
    assert "brass_key" in eng.world.rooms[RoomId("vault")].items_present


def test_drop_item_not_held_returns_friendly_error() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("drop brass_key").lower()
    assert "aren't" in out or "not" in out or "don't" in out
    assert "brass_key" not in eng.world.rooms[eng.world.player.location].items_present


def test_drop_without_item_is_friendly_error() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("drop").lower()
    assert "what" in out or "drop" in out


def test_take_emits_narration_hint() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    out = eng.submit("take brass_key").lower()
    assert "taken" in out


def test_examine_item_in_room_shows_short_description() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")  # vault holds brass_key
    out = eng.submit("examine brass_key").lower()
    assert "tarnished" in out  # from the registered short_description


def test_examine_item_held_shows_short_description() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    eng.submit("west")
    out = eng.submit("examine brass_key").lower()
    assert "tarnished" in out


def test_examine_unknown_item_says_not_visible() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("examine xyzzy").lower()
    assert "don't see" in out or "no " in out or "nothing" in out


def test_examine_item_not_here_says_not_visible() -> None:
    # brass_key is in vault, not entry_hall.
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("examine brass_key").lower()
    assert "don't see" in out or "not here" in out


def test_examine_multiword_name_matches() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    out = eng.submit("examine brass key").lower()
    assert "tarnished" in out


def test_examine_without_object_is_friendly_error() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("examine").lower()
    assert "what" in out or "examine" in out


def test_items_rendered_with_display_names() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")  # vault with brass_key
    text = eng.describe_current_room()
    items_line = next(line for line in text.splitlines() if line.startswith("Items:"))
    assert "brass_key" not in items_line
    assert "brass key" in items_line
    # Article should appear.
    assert "a brass key" in items_line


def test_inventory_rendered_with_display_names() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    out = eng.submit("inventory")
    assert "brass_key" not in out
    assert "brass key" in out


def test_drop_multiword_item_name_works() -> None:
    # "drop brass key" should match "brass_key" just like take does.
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass key")
    out = eng.submit("drop brass key").lower()
    assert "dropped" in out or "drop" in out
    assert "brass_key" not in eng.world.player.inventory


def test_post_win_input_is_rejected_with_game_over_message() -> None:
    eng = TurnEngine(build_five_room_world())
    for cmd in [
        "east",
        "take brass_key",
        "west",
        "south",
        "take silver_key",
        "north",
        "north",
        "north",
    ]:
        eng.submit(cmd)
    assert eng.world.is_won()

    before_location = eng.world.player.location
    out = eng.submit("south").lower()
    assert "game is over" in out or "game over" in out
    # Must not have moved or otherwise advanced state.
    assert eng.world.player.location == before_location


def test_post_win_quit_still_works() -> None:
    eng = TurnEngine(build_five_room_world())
    for cmd in [
        "east",
        "take brass_key",
        "west",
        "south",
        "take silver_key",
        "north",
        "north",
        "north",
    ]:
        eng.submit(cmd)
    assert eng.world.is_won()

    assert eng.submit("quit") == "__QUIT__"


def test_post_win_save_still_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    eng = TurnEngine(build_five_room_world())
    for cmd in [
        "east",
        "take brass_key",
        "west",
        "south",
        "take silver_key",
        "north",
        "north",
        "north",
    ]:
        eng.submit(cmd)
    out = eng.submit("save won").lower()
    assert "saved" in out


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
