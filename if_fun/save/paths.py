"""Filesystem paths for saves, templates, and logs."""

import os
from pathlib import Path

from platformdirs import user_state_dir


def state_dir() -> Path:
    """Return the if_fun state directory, respecting IF_FUN_STATE_DIR for tests."""
    override = os.environ.get("IF_FUN_STATE_DIR")
    if override:
        return Path(override)
    return Path(user_state_dir("if_fun", appauthor=False))


def saves_dir() -> Path:
    return state_dir() / "saves"


def save_path(slot: str) -> Path:
    return saves_dir() / f"{slot}.json"
