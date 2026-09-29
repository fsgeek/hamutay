import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    'plaza_conftest', ROOT / 'tests' / 'plaza' / 'conftest.py',
)
_m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _m
_spec.loader.exec_module(_m)

write_members = _m.write_members
house = _m.house
house_guests = _m.house_guests
house_unplaza = _m.house_unplaza


def cli(root, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    return subprocess.run(
        [sys.executable, '-B', '-m', 'hamutay.plaza', '--project-root', str(root), *args],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )


def records(cfg):
    if not cfg.plaza.exists():
        return []
    return [json.loads(line) for line in cfg.plaza.read_text().splitlines()]
