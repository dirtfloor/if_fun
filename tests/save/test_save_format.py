from pathlib import Path

import pytest

from if_fun.ids import RoomId
from if_fun.save.paths import save_path, saves_dir
from if_fun.save.save_format import (
    SaveFormatError,
    SchemaVersionMismatch,
    read_save,
    write_save,
)
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState


def _tiny_world() -> WorldState:
    return WorldState(
        rooms={
            RoomId("r1"): RoomState(id=RoomId("r1"), description="A room."),
        },
        player=PlayerState(location=RoomId("r1")),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "r1"}),
    )


def test_saves_dir_resolves_under_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    assert saves_dir() == tmp_path / "saves"


def test_save_path_joins_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    assert save_path("slot1") == tmp_path / "saves" / "slot1.json"


def test_write_and_read_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    w = _tiny_world()
    write_save("slot1", w)
    restored = read_save("slot1")
    assert restored == w


def test_read_save_future_version_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    p = save_path("future")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 9999}')
    with pytest.raises(SchemaVersionMismatch):
        read_save("future")


def test_read_save_garbage_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    p = save_path("garbage")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("this is not json")
    with pytest.raises(SaveFormatError):
        read_save("garbage")
