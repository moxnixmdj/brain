#!/usr/bin/env python3
"""Research-only control of the pinned historical canary isolation harness.

Explicitly loads historical files supplied by the operator. This is not
repository test infrastructure and must only be run on a trusted snapshot.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from canonical.tools.living_canary_isolation_v1 import evaluate_canary


def sample(**overrides):
    row = {'skill_id': 'count', 'description': 'count lines',
           'template': 'wc -l < {path}', 'slots': {'path': 'source.txt'},
           'postcondition': r'^[0-9]+$', 'canary_input': {'canary.txt': 'a\nb\nc\n'},
           'canary_expected': '3'}
    row.update(overrides)
    return row


def audit(source: Path):
    with tempfile.TemporaryDirectory(prefix='canary_control_', dir='/tmp') as tmp:
        caller_canary = Path(tmp) / 'canary.txt'
        caller_canary.write_text('VISIBLE\n')
        secret = Path(tmp) / 'sentinel'
        secret.write_text('LEAK\n')
        positive = evaluate_canary(source, sample())
        negative = evaluate_canary(source, sample(canary_expected='4'))
        invalid = evaluate_canary(source, sample(canary_input={'../../escape.txt': 'x'}))
        # This quoted sed argument bypasses the historical agent's lexical
        # path check; the bare control actually reads our non-sensitive fixture.
        command = "sed 'r '\"" + str(secret) + "\" canary.txt"
        bare = subprocess.run(command, shell=True, cwd=tmp, capture_output=True,
                              text=True, check=True, timeout=3)
        probe = sample(template=command, slots={}, postcondition=r'^VISIBLE$',
                       canary_input={'canary.txt': 'VISIBLE\n'}, canary_expected='VISIBLE')
        isolated = evaluate_canary(source, probe)
        # A second bypass targets a disposable host file for writing. Prove
        # the bare command modifies it, reset it, then try inside isolation.
        write_command = "sed 'w '\"" + str(secret) + "\" canary.txt"
        subprocess.run(write_command, shell=True, cwd=tmp, capture_output=True,
                       text=True, check=True, timeout=3)
        bare_write_worked = secret.read_text() == 'VISIBLE\n'
        secret.write_text('LEAK\n')
        write_probe = sample(template=write_command, slots={}, postcondition=r'^VISIBLE$',
                             canary_input={'canary.txt': 'VISIBLE\n'}, canary_expected='VISIBLE')
        isolated_write = evaluate_canary(source, write_probe)
        checks = {'normal_canary_pass': positive.get('status') == 'CANARY_PASS',
                  'wrong_expected_refused': negative.get('status') == 'CANARY_FAILED',
                  'escaping_input_refused': invalid.get('status') == 'CANARY_ERROR',
                  'bare_shell_reads_fixture': bare.stdout == 'VISIBLE\nLEAK\n',
                  'isolated_shell_cannot_read_fixture': isolated.get('status') == 'CANARY_PASS',
                  'bare_shell_writes_fixture': bare_write_worked,
                  'isolated_shell_write_refused': isolated_write.get('status') == 'CANARY_FAILED',
                  'caller_canary_preserved': caller_canary.read_text() == 'VISIBLE\n',
                  'caller_sentinel_preserved': secret.read_text() == 'LEAK\n'}
        return {'pass': all(checks.values()), 'checks': checks,
                'results': {'positive': positive, 'negative': negative,
                            'invalid': invalid, 'isolated': isolated,
                            'isolated_write': isolated_write},
                'limitations': 'trusted pinned Python, Linux namespaces; no seccomp or cgroup; host /usr readable; not a production hostile-code sandbox'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--living-source', type=Path, required=True)
    args = parser.parse_args()
    out = audit(args.living_source)
    print(json.dumps(out, indent=2))
    raise SystemExit(0 if out['pass'] else 1)


if __name__ == '__main__':
    main()
