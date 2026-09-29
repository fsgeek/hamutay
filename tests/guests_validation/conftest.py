import json
import os
import subprocess
import sys
from pathlib import Path

from tests.plaza.conftest import house, house_guests, house_unplaza, write_members

ROOT = Path(__file__).resolve().parents[2]


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
