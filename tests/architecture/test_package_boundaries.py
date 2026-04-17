import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DETERMINISTIC_PACKAGES = ["if_fun/world", "if_fun/parser", "if_fun/save"]
FORBIDDEN_PREFIXES = ("if_fun.agents",)


def _imports_in(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("package", DETERMINISTIC_PACKAGES)
def test_deterministic_package_has_no_forbidden_imports(package: str) -> None:
    offences: list[str] = []
    pkg_path = REPO_ROOT / package
    for py_file in pkg_path.rglob("*.py"):
        for imp in _imports_in(py_file):
            if imp.startswith(FORBIDDEN_PREFIXES):
                offences.append(f"{py_file.relative_to(REPO_ROOT)}: imports {imp}")
    assert not offences, "forbidden imports found:\n" + "\n".join(offences)
