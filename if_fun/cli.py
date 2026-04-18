"""CLI entry point. Phase A: only `if_fun play` is implemented."""

import typer

from if_fun.tui.app import IfFunApp
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world

app = typer.Typer(help="Interactive Fiction game (Phase A walking skeleton).")


@app.callback()
def _main() -> None:
    """Force Typer into explicit-subcommand dispatch.

    Without this, a single @app.command() makes Typer treat `play` as the
    default and reject it when named — so `if_fun play` fails while bare
    `if_fun` silently launches the TUI. The no-op callback flips the app
    into subcommand mode so `if_fun play` works and `if_fun` alone prints
    help.
    """


@app.command()
def play() -> None:
    """Launch the Textual TUI on the hardcoded 5-room world."""
    engine = TurnEngine(build_five_room_world())
    IfFunApp(engine).run()


if __name__ == "__main__":
    app()
