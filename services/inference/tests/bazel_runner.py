"""Entry point so Bazel's py_test can drive the vendored pytest suite."""

import sys
from pathlib import Path

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).resolve().parent), "-v"]))
