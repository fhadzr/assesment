"""Smoke test: proves discovery, per-case venv, and package import work."""

import rag


def test_package_importable_with_version():
    assert rag.__version__ == "0.1.0"
