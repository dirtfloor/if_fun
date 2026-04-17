"""Save schema migration registry. Empty for v1."""

from collections.abc import Callable

CURRENT_SCHEMA_VERSION = 1

# Mapping: version_from -> (version_to, migrate_fn).
# migrate_fn takes a dict and returns a dict.
MIGRATIONS: dict[int, tuple[int, Callable[[dict], dict]]] = {}
