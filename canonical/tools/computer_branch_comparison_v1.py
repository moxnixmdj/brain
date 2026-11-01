#!/usr/bin/env python3
"""Compare two real line-count paths on the same files, not consciousness.

Pass a separately prepared source snapshot of the living-agent branch; this
benchmark never downloads or imports historical code into the current process.
The arms have different acquisition interfaces: one receives a demonstration,
the other discovers a tool through its own probes. This is not a one-shot
head-to-head with identical instruction, nor an arbitrary-computer benchmark.
All inputs are fixed known fixtures and all state is disposable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'red\nblue\ngreen\n'
TARGETS = {'different': 'a\nb\nc\nd\ne\n', 'empty': '',
           'repeated': 'x\nx\ny\nx\n', 'unterminated': 'a\nb',
           'long_name': 'north\nsouth\n'}
LONG_NAME = 'a' * 72 + '.txt'
GOAL = "count the lines in '{name}'"


def worker(root: Path, arm: str, phase: str, mode: str, name: str = '') -> dict:
    root.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    if arm == 'living':
        from canonical.runtime.living_agent_v1 import AgentError, LivingAgent
        agent = LivingAgent(root)
        if phase == 'teach':
            agent.computer.write('source.txt', SOURCE)
            demonstrated = agent.computer.run('wc -l < source.txt')
            if not demonstrated.ok or int(demonstrated.stdout) != SOURCE.count('\n'):
                raise RuntimeError('DEMONSTRATION_FAILED')
            skill = agent.learn_shell_skill('count the lines in a file', 'wc -l < source.txt',
                {'path': 'source.txt'}, canary=({'canary.txt': 'a\nb\nc\nd\n'}, '4'),
                postcondition=r'^[0-9]+$')
            (root / 'snapshot.json').write_text(json.dumps(agent.snapshot()))
            return {'admitted': True, 'skill_id': skill.skill_id,
                    'elapsed_ms': round((time.perf_counter() - t) * 1000, 3),
                    'commands': agent.computer.runs}
        if mode == 'warm':
            agent.restore(json.loads((root / 'snapshot.json').read_text()))
        target = root / (LONG_NAME if name == 'long_name' else 'target.txt')
        if name != 'missing':
            target.write_text(TARGETS[name])
        try:
            result = agent.solve(GOAL.format(name=target.name))
            value = result.get('text')
            passed = result.get('status') == 'PASS'
            status = result.get('status')
        except AgentError as exc:
            value, passed, status = None, False, str(exc)
        return {'pass': passed, 'value': value, 'status': status,
                'commands': agent.computer.runs,
                'elapsed_ms': round((time.perf_counter() - t) * 1000, 3)}
    if arm == 'current':
        from canonical.runtime.computer_env_v1 import answer_query
        cache_present = (root / 'state' / 'brain_query_probe_v1.json').is_file()
        target = root / ('source.txt' if phase == 'teach' else
                         LONG_NAME if name == 'long_name' else 'target.txt')
        if phase == 'teach':
            target.write_text(SOURCE)
        elif name != 'missing':
            target.write_text(TARGETS[name])
        result = answer_query(GOAL.format(name=target.name), target, timeout=3)
        row = {'pass': result.get('pass') is True, 'value': result.get('value'),
               'status': result.get('status'), 'from_memory': result.get('from_memory'),
               'query_cache_present_before': cache_present,
               'elapsed_ms': round((time.perf_counter() - t) * 1000, 3)}
        if phase == 'teach':
            row['admitted'] = row['pass'] and row['value'] == str(SOURCE.count('\n'))
        return row
    raise ValueError('UNKNOWN_ARM')


def invoke(living: Path, work: Path, arm: str, phase: str, mode: str, name: str = '') -> dict:
    state = work / 'state'
    state.mkdir(parents=True, exist_ok=True)
    bin_dir = work / 'bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    wc = shutil.which('wc')
    if not wc:
        raise RuntimeError('WC_REQUIRED')
    link = bin_dir / 'wc'
    if not link.exists():
        link.symlink_to(Path(wc).resolve())
    # Current discovery receives only wc on PATH; the living computer constructs
    # its own admitted-binary search path. This difference is reported, not hidden.
    env = dict(os.environ, BRAIN_STATE_DIR=str(state), PATH=str(bin_dir),
               PYTHONPATH=str(living if arm == 'living' else ROOT), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', str(work), arm, phase, mode, name]
    result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True,
                            check=True, timeout=30)
    return json.loads(result.stdout)


def compare(living: Path) -> dict:
    if not (living / 'canonical/runtime/living_agent_v1.py').is_file():
        raise ValueError('LIVING_SOURCE_SNAPSHOT_REQUIRED')
    arms = []
    # Keep paths short: the current query reader rejects output over 64 bytes,
    # including wc's echoed filename, even when the numeric answer is short.
    with tempfile.TemporaryDirectory(prefix='bc_') as td:
        base = Path(td)
        for arm in ('current', 'living'):
            training = base / (arm + '_source')
            lesson = invoke(living, training, arm, 'teach', 'warm')
            rows = []
            for mode in ('cold', 'warm'):
                for name in [*TARGETS, 'missing']:
                    case = base / (arm + '_' + mode + '_' + name)
                    case.mkdir()
                    if mode == 'warm':
                        if arm == 'living':
                            shutil.copy2(training / 'snapshot.json', case / 'snapshot.json')
                        else:
                            shutil.copytree(training / 'state', case / 'state')
                    result = invoke(living, case, arm, 'target', mode, name)
                    expected = None if name == 'missing' else str(TARGETS[name].count('\n'))
                    result.update(case=name, mode=mode, expected=expected,
                                  audited=(not result['pass'] if name == 'missing'
                                           else result['pass'] and result['value'] == expected))
                    rows.append(result)
            arms.append({'arm': arm, 'acquisition': ('probes' if arm == 'current' else 'demonstration'),
                         'lesson': lesson, 'cases': rows})
    living_modules = ('living_agent_v1', 'living_core_v1', 'living_discovery_v1', 'shell_synthesis_v1')
    sources = {name: hashlib.sha256((living / 'canonical/runtime' / (name + '.py')).read_bytes()).hexdigest()
               for name in living_modules}
    sources['current_computer_env_v1'] = hashlib.sha256(
        (ROOT / 'canonical/runtime/computer_env_v1.py').read_bytes()).hexdigest()
    return {'schema': 'BRAIN_COMPUTER_BRANCH_COMPARISON_V1',
            'scope': 'known line-count fixtures; distinct acquisition methods and binary vocabularies; not sentience',
            'source_sha256': sources, 'arms': arms}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--living-source', type=Path)
    p.add_argument('--worker', nargs=5, metavar=('ROOT', 'ARM', 'PHASE', 'MODE', 'NAME'))
    args = p.parse_args()
    if args.worker:
        root, arm, phase, mode, name = args.worker
        print(json.dumps(worker(Path(root), arm, phase, mode, name)))
    elif args.living_source:
        print(json.dumps(compare(args.living_source.resolve()), indent=2))
    else:
        p.error('--living-source is required')


if __name__ == '__main__':
    main()
