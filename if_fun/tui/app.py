"""Minimal Textual app for Phase A: prose pane + input line."""

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog

from if_fun.tui.turn_engine import QUIT_SENTINEL, TurnEngine


class IfFunApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    RichLog { height: 1fr; border: solid grey; }
    Input { dock: bottom; }
    """

    def __init__(self, engine: TurnEngine) -> None:
        super().__init__()
        self._engine = engine
        self.last_output: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(id="prose", wrap=True, markup=False, highlight=False)
            yield Input(id="command-input", placeholder="What do you do?")

    def on_mount(self) -> None:
        self._append(self._engine.describe_current_room())
        self.query_one("#command-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        event.input.value = ""
        if not raw.strip():
            return
        self._append(f"> {raw}")
        result = self._engine.submit(raw)
        if result == QUIT_SENTINEL:
            self.exit()
            return
        self._append(result)

    def _append(self, text: str) -> None:
        self.last_output = text
        self.query_one("#prose", RichLog).write(text)
