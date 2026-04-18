from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world

WINNING_SCRIPT = [
    "east",  # entry_hall → vault
    "take brass_key",
    "west",  # vault → entry_hall
    "south",  # entry_hall → library
    "take silver_key",
    "take crystal",
    "north",  # library → entry_hall
    "north",  # entry_hall → ritual_chamber (requires brass_key)
    "north",  # ritual_chamber → treasury (requires silver_key)
]


def test_scripted_playthrough_wins() -> None:
    eng = TurnEngine(build_five_room_world())
    last = ""
    for cmd in WINNING_SCRIPT:
        last = eng.submit(cmd)
    assert eng.world.is_won(), f"final state not won; last output: {last}"
    assert "won" in last.lower()


def test_scripted_playthrough_fails_without_brass_key() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("north")  # locked without brass_key
    assert "can't" in out.lower()
    assert not eng.world.is_won()
