"""Reuse the existing plaza fixtures without changing their package."""

import sys
from pathlib import Path

# The pytest entry point does not add the repository root as python -m pytest does.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.plaza.conftest import house, house_guests  # noqa: E402, F401
