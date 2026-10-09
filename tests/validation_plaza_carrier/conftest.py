"""Use established plaza house fixtures; keep all new utilities local."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.plaza.conftest import house, house_guests  # noqa: E402, F401
