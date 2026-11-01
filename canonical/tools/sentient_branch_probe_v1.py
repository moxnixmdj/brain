#!/usr/bin/env python3
"""Bounded non-executing probe of a supplied historical agent snapshot.

Runs historical code in fresh interpreters. The unrelated goal is only passed
to apply_pattern; it is never executed. This is not a test for consciousness.
The supplied snapshot must be trusted: Python import is not OS-sandboxed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

TRAIN = '''import json,sys
from canonical.runtime.sentient_computer_agent_v1 import SentientComputerAgent, apply_pattern
a=SentientComputerAgent(repo_root=sys.argv[1])
r=a.learn_instantly([{'goal':'archive docs/report.txt to dist/report.tar.gz','plan':[{'capability_id':'archive.create'}]}])
a.memorize({'goal':'archive docs/report.txt','success':True})
print(json.dumps({'lesson':r,'unrelated_path_control':apply_pattern(r,'delete private/secret.txt'),'stats':a.stats()}))
'''
RESTART = '''import json,sys
from canonical.runtime.sentient_computer_agent_v1 import SentientComputerAgent
a=SentientComputerAgent(repo_root=sys.argv[1])
print(json.dumps(a.stats()))
'''


def probe(snapshot: Path) -> dict:
    module = snapshot / 'canonical/runtime/sentient_computer_agent_v1.py'
    if not module.is_file():
        raise ValueError('AGENT_SNAPSHOT_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='brain_sentient_probe_') as tmp:
        env = dict(os.environ, PYTHONPATH=str(snapshot), PYTHONDONTWRITEBYTECODE='1')
        outputs = []
        for code in (TRAIN, RESTART):
            p = subprocess.run([sys.executable, '-c', code, tmp], cwd=snapshot, env=env,
                               capture_output=True, text=True, timeout=20, check=True)
            outputs.append(json.loads(p.stdout))
    return {'schema': 'BRAIN_SENTIENT_BRANCH_PROBE_V1',
            'scope': 'one non-executed unrelated goal and fresh-instance restart; not a sentience test',
            'source_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
            'trained': outputs[0], 'fresh_instance': outputs[1]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--branch-source', type=Path, required=True)
    print(json.dumps(probe(p.parse_args().branch_source.resolve()), indent=2))


if __name__ == '__main__':
    main()
