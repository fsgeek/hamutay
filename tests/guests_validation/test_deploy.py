"""Only disposable git houses; all service calls are intercepted on PATH."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest

from hamutay.assembly.binding import load_members
from hamutay.plaza.read import read_rows
from .conftest import ROOT, cli

DOORS = ('heartbeat', 'fable', 'elder', 'qwen')


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def executable(path, body):
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def deployment(tmp_path):
    root = tmp_path / 'house'
    root.mkdir()
    (root / 'deploy').mkdir()
    # Opaque copies for execution, never inspected as implementation evidence.
    for script in ('check-plaza.sh', 'migrate-plaza.sh'):
        shutil.copy2(ROOT / 'deploy' / script, root / 'deploy' / script)
    members = root / 'community/plaza/members.json'
    members.parent.mkdir(parents=True)
    body = {'ledger': 'community/plaza/assembly.jsonl', 'plaza': 'community/plaza/plaza.jsonl',
            'members': {door: {'session': f'community/{door}/session.jsonl',
                               'events': f'community/{door}/session.jsonl.events.jsonl'} for door in DOORS}}
    members.write_text(json.dumps(body))
    for door in DOORS:
        (root / 'community' / door).mkdir()
    (root / '.gitignore').write_text(
        'community/plaza/*.jsonl\ncommunity/plaza/*.lock\n'
        'community/plaza/members.json.*\ncommunity/*/*.events.jsonl\ncommunity/*/*.lock\n')
    python = shlex.quote(sys.executable)
    executable(root / 'deploy/ayllu-plaza', f'#!/bin/sh\nexec {python} -B -m hamutay.plaza --project-root "$GUEST_TEST_ROOT" "$@"\n')
    executable(root / 'deploy/ayllu-gpu', '#!/bin/sh\necho free\n')
    git(root, 'init', '-q')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Independent validation', '-c', 'user.email=validation@example.invalid',
        'commit', '--no-gpg-sign', '-qm', 'disposable house')
    head = git(root, 'rev-parse', 'HEAD')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
               PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               GUEST_TEST_ROOT=str(root), GUEST_TEST_HEAD=head,
               GUEST_TEST_LOG=str(tmp_path / 'services.jsonl'), GUEST_TEST_CONTROL=str(tmp_path / 'control.json'),
               GUEST_TEST_MARKER=str(tmp_path / 'window.json'))
    Path(env['GUEST_TEST_CONTROL']).write_text('{}')
    shebang = '#!' + sys.executable + '\n'
    executable(bin_dir / 'systemctl', shebang + '''import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
with open(os.environ['GUEST_TEST_LOG'], 'a') as out:
    out.write(json.dumps(args) + '\\n')
control = json.loads(pathlib.Path(os.environ['GUEST_TEST_CONTROL']).read_text())
if 'show' in args:
    print('InvocationID=validation-invocation')
if 'start' in args and control.get('window'):
    marker = pathlib.Path(os.environ['GUEST_TEST_MARKER'])
    root = pathlib.Path(os.environ['GUEST_TEST_ROOT'])
    admitted = json.loads((root / 'community/plaza/members.json').read_text()).get('guests', [])
    if not marker.exists() and 'levadura' in admitted:
        text = marker.with_suffix('.txt')
        text.write_text('accepted during activation')
        # Force the directed event to remain pending, without obstructing the
        # migration's earlier idle check. Repair must survive admission removal.
        blocked = root / 'community/elder/session.jsonl.events.jsonl'
        blocked.mkdir()
        outcomes = []
        for recipient in ['plaza', 'elder']:
            result = subprocess.run([sys.executable, '-B', '-m', 'hamutay.plaza',
                '--project-root', str(root), 'send', '--by', 'guest:levadura',
                '--to', recipient, '--text-file', str(text), '--key', recipient],
                capture_output=True, text=True)
            outcomes.append(dict(code=result.returncode, out=result.stdout, err=result.stderr))
        marker.write_text(json.dumps(outcomes))
''')
    executable(bin_dir / 'journalctl', shebang + '''import json, os, pathlib, sys
control = json.loads(pathlib.Path(os.environ['GUEST_TEST_CONTROL']).read_text())
body = json.loads((pathlib.Path(os.environ['GUEST_TEST_ROOT']) / 'community/plaza/members.json').read_text())
door = next((arg.split('@', 1)[1].removesuffix('.service') for arg in sys.argv if 'hamutay-heartbeat@' in arg), 'heartbeat')
print('source: commit ' + os.environ['GUEST_TEST_HEAD'] + ' clean')
print('assembly: member ' + door + ' bound; ledger l')
if not control.get('omit_plaza'):
    count = len(body.get('guests', []))
    if control.get('wrong_count') and door == 'qwen':
        count += 1
    print(f'plaza: door {door} may send; log p; guests {count}')
''')
    # Keep temporary repositories independent of package installation/network.
    executable(bin_dir / 'uv', shebang + '''import os, sys
args = sys.argv[1:]
if args and args[0] == 'run':
    args.pop(0)
if args and args[0] in ('python', 'python3'):
    os.execv(sys.executable, [sys.executable, '-B', *args[1:]])
raise SystemExit('unexpected uv invocation: ' + repr(args))
''')
    executable(bin_dir / 'sleep', '#!/bin/sh\nexit 0\n')
    return root, head, env


def run(deployment, script, *args):
    root, _, env = deployment
    return subprocess.run(['bash', str(root / 'deploy' / script), *args], cwd=root, env=env,
                          capture_output=True, text=True, timeout=90)


def control(deployment, **settings):
    Path(deployment[2]['GUEST_TEST_CONTROL']).write_text(json.dumps(settings))


def calls(deployment):
    path = Path(deployment[2]['GUEST_TEST_LOG'])
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def migrate(deployment, *extra):
    root, head, _ = deployment
    return run(deployment, 'migrate-plaza.sh', '--guests', 'levadura,yupi', '--root', str(root), '--merge', head, *extra)


@pytest.mark.parametrize('script', ['check-plaza.sh', 'migrate-plaza.sh'])
def test_unknown_flag_is_usage_error(deployment, script):
    out = run(deployment, script, '--guests-redy')
    assert out.returncode == 2, out.stdout + out.stderr
    assert not any('stop' in c or 'start' in c for c in calls(deployment))


def test_guests_ready_still_checks_plaza_binding_key_and_status(deployment):
    out = run(deployment, 'check-plaza.sh', '--guests-ready', '--merge', deployment[1])
    for door in DOORS:
        assert f'ok   unit {door} plaza bound' in out.stdout, out.stdout + out.stderr
    assert 'members.json has the plaza key' in out.stdout
    assert 'plaza status valid' in out.stdout
    control(deployment, omit_plaza=True)
    broken = run(deployment, 'check-plaza.sh', '--guests-ready', '--merge', deployment[1])
    assert broken.returncode != 0
    assert 'FAIL unit' in broken.stdout and 'plaza bound' in broken.stdout
    # A missing key and a malformed ledger must each fail their own check.
    root = deployment[0]
    path = root / 'community/plaza/members.json'
    original = path.read_bytes()
    body = json.loads(original)
    del body['plaza']
    path.write_text(json.dumps(body))
    control(deployment)
    disabled = run(deployment, 'check-plaza.sh', '--guests-ready', '--merge', deployment[1])
    assert 'FAIL members.json has the plaza key' in disabled.stdout
    path.write_bytes(original)
    (path.parent / 'plaza.jsonl').write_text('{"record_type":"invalid"}\n')
    malformed = run(deployment, 'check-plaza.sh', '--guests-ready', '--merge', deployment[1])
    assert 'FAIL plaza status valid' in malformed.stdout


def test_guests_install_verifies_each_units_count(deployment):
    out = migrate(deployment)
    assert out.returncode == 0, out.stdout + out.stderr
    root = deployment[0]
    assert load_members(root).guests == ('levadura', 'yupi')
    for door in DOORS:
        assert f'{door}: guests 2' in out.stdout
    assert not (root / 'community/plaza/members.json.previous').exists()


def test_guests_dry_run_changes_no_house_file_or_service(deployment):
    root = deployment[0]
    def snapshot():
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
                if p.is_file() and '.git' not in p.relative_to(root).parts}
    before = snapshot()
    out = migrate(deployment, '--dry-run')
    assert out.returncode == 0, out.stdout + out.stderr
    assert 'dry run' in out.stdout.lower()
    assert snapshot() == before
    assert not any(set(c).intersection({'stop', 'start', 'restart'}) for c in calls(deployment))


def test_failed_count_verification_restores_config_but_guest_write_and_repair_stand(deployment):
    root, _, env = deployment
    path = root / 'community/plaza/members.json'
    before = path.read_bytes()
    control(deployment, window=True, wrong_count=True)
    out = migrate(deployment)
    assert out.returncode != 0, out.stdout + out.stderr
    assert 'rolling back' in (out.stdout + out.stderr).lower()
    outcomes = json.loads(Path(env['GUEST_TEST_MARKER']).read_text())
    assert all(item['code'] == 0 for item in outcomes), outcomes
    assert path.read_bytes() == before
    cfg = load_members(root)
    rows = read_rows(cfg)
    assert len(rows) == 2 and all(r['from'] == 'guest:levadura' for r in rows)
    assert rows[0]['truth'] == {'state': 'post'}
    assert rows[1]['truth']['state'] != 'landed'
    blocked = root / 'community/elder/session.jsonl.events.jsonl'
    blocked.rmdir()
    repaired = cli(root, 'pass')
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert read_rows(load_members(root))[1]['truth']['state'] == 'landed'
    retry = cli(root, 'send', '--by', 'guest:levadura', '--to', 'plaza',
                '--text-file', str(Path(env['GUEST_TEST_MARKER']).with_suffix('.txt')), '--key', 'plaza')
    assert retry.returncode == 2 and 'not admitted' in retry.stderr
    assert len(read_rows(load_members(root))) == 2
