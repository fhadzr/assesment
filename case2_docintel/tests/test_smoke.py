"""Smoke test: proves discovery, per-case venv, and package import work."""

import docintel


def test_package_importable_with_version():
    assert docintel.__version__ == "0.1.0"
