"""Sanity check that the test harness and package import work."""

import if_fun


def test_package_imports() -> None:
    assert if_fun.__name__ == "if_fun"
