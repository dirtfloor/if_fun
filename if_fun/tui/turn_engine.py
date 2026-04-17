"""Turn engine: parser + state store + save/load. No UI, no LLM."""

from typing import assert_never

from if_fun.parser.grammar import MetaVerb
from if_fun.parser.parser import DirectionCommand, MetaCommand, ParseError, parse
from if_fun.save.save_format import read_save, write_save
from if_fun.world.state import WorldState
from if_fun.world.store import IllegalAction, apply_action, apply_direction
from if_fun.world.transitions import Action

WIN_MESSAGE = "\n** You have won. **"
QUIT_SENTINEL = "__QUIT__"


class TurnEngine:
    def __init__(self, world: WorldState) -> None:
        self._world = world

    @property
    def world(self) -> WorldState:
        return self._world

    def describe_current_room(self) -> str:
        room = self._world.rooms[self._world.player.location]
        exits = ", ".join(d.value for d in room.exits) or "none"
        items = ", ".join(room.items_present) or "none"
        return f"[{room.id}]\n{room.description}\n\nExits: {exits}\nItems: {items}"

    def submit(self, raw_input: str) -> str:
        cmd = parse(raw_input)

        if isinstance(cmd, ParseError):
            return f"I don't understand that. ({cmd.message})"

        if isinstance(cmd, MetaCommand):
            return self._handle_meta(cmd)

        if isinstance(cmd, DirectionCommand):
            try:
                self._world = apply_direction(self._world, cmd.direction)
            except IllegalAction:
                return "You can't go that way."
            return self._post_turn()

        if isinstance(cmd, Action):
            if cmd.verb == "look" and cmd.direct_object is None:
                return self.describe_current_room()
            if cmd.verb == "inventory" and cmd.direct_object is None:
                items = ", ".join(self._world.player.inventory) or "nothing"
                return f"You carry: {items}"

            try:
                self._world = apply_action(self._world, cmd)
            except IllegalAction:
                return "You can't do that."
            return self._post_turn()

        # Static exhaustiveness over ParsedCommand: if the union grows, ty
        # flags this call site before runtime.
        assert_never(cmd)

    def save(self, slot: str) -> None:
        write_save(slot, self._world)

    def load(self, slot: str) -> None:
        self._world = read_save(slot)

    def _handle_meta(self, cmd: MetaCommand) -> str:
        if cmd.verb is MetaVerb.QUIT:
            return QUIT_SENTINEL
        if cmd.verb is MetaVerb.HELP:
            return (
                "Verbs: look, take <item>, drop <item>, use <item>, open, unlock, "
                "examine <item>, inventory, wait.\n"
                "Directions: n, s, e, w, u, d (or 'go north' etc.).\n"
                "Meta: save <slot>, load <slot>, quit."
            )
        if cmd.verb is MetaVerb.SAVE:
            if cmd.arg is None:
                return "Usage: save <slot>"
            self.save(cmd.arg)
            return f"Saved to slot {cmd.arg!r}."
        if cmd.verb is MetaVerb.LOAD:
            if cmd.arg is None:
                return "Usage: load <slot>"
            self.load(cmd.arg)
            return f"Loaded slot {cmd.arg!r}.\n\n" + self.describe_current_room()
        raise AssertionError(f"unhandled meta verb: {cmd.verb!r}")  # pragma: no cover

    def _post_turn(self) -> str:
        text = self.describe_current_room()
        if self._world.is_won():
            text += WIN_MESSAGE
        return text
