"""Save read/write with schema versioning."""

import json
from pathlib import Path

from pydantic import ValidationError

from if_fun.save.paths import save_path
from if_fun.save.schema_migrations import CURRENT_SCHEMA_VERSION, MIGRATIONS
from if_fun.world.state import WorldState


class SaveFormatError(Exception):
    """Raised when a save file is malformed or unreadable."""


class SchemaVersionMismatch(SaveFormatError):
    """Raised when a save file's schema_version is newer than we understand."""


def write_save(slot: str, world: WorldState) -> Path:
    """Serialize ``world`` to the slot's JSON file, creating the saves dir.

    Returns the path written. Filesystem failures are translated to
    ``SaveFormatError`` so callers only need to handle one exception type.
    """
    p = save_path(slot)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(world.model_dump_json(indent=2))
    except OSError as exc:
        raise SaveFormatError(f"save {slot!r} could not be written: {exc}") from exc
    return p


def read_save(slot: str) -> WorldState:
    """Load a slot's JSON file, running forward-only schema migrations.

    All I/O, JSON, migration, and pydantic validation failures surface as
    ``SaveFormatError``; a save with a schema_version newer than this build
    understands surfaces as ``SchemaVersionMismatch``.
    """
    p = save_path(slot)
    try:
        raw = p.read_text()
    except FileNotFoundError as exc:
        raise SaveFormatError(f"save not found: {slot!r}") from exc
    except OSError as exc:
        raise SaveFormatError(f"save {slot!r} could not be read: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SaveFormatError(f"save {slot!r} is not valid JSON") from exc

    version = data.get("schema_version", 1)
    while version != CURRENT_SCHEMA_VERSION:
        if version > CURRENT_SCHEMA_VERSION:
            raise SchemaVersionMismatch(
                f"save {slot!r} has schema_version={version}, "
                f"but this build understands up to {CURRENT_SCHEMA_VERSION}"
            )
        if version not in MIGRATIONS:
            raise SaveFormatError(f"no migration registered for schema version {version}")
        target, migrate = MIGRATIONS[version]
        data = migrate(data)
        version = target

    try:
        return WorldState.model_validate(data)
    except ValidationError as exc:
        raise SaveFormatError(f"save {slot!r} failed validation: {exc}") from exc
