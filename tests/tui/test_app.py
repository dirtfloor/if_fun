import pytest
from textual.widgets import Input

from if_fun.tui.app import IfFunApp
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


@pytest.mark.asyncio
async def test_app_starts_and_shows_initial_prose() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "antechamber" in app.last_output.lower()


@pytest.mark.asyncio
async def test_app_accepts_input_and_updates_prose() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#command-input", Input)
        input_widget.value = "east"
        await pilot.press("enter")
        await pilot.pause()
        assert "vault" in app.last_output.lower()


@pytest.mark.asyncio
async def test_app_exits_on_quit() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#command-input", Input)
        input_widget.value = "quit"
        await pilot.press("enter")
        await pilot.pause()
        assert app.return_value is None  # app exits cleanly
