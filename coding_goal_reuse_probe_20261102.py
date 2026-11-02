#!/usr/bin/env python3
"""Compare a plain-goal entry and explicitly configured retained repair.

Research probe, not an autonomous agent or capability certification. It copies the
current canonical tree into a disposable directory because the live route can
write several default state files even when an explicit R3 state path is supplied.
All target projects, learned state, reports, and imports use the disposable copy.
It executes repository code and generated tests: run only on a trusted checkout.

    python3 coding_goal_reuse_probe_20261102.py

The two routes have different inputs and admission policies; this is not a fair
capability comparison. Its purpose is to locate a wiring/admission boundary.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent

WORKER = r"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
from canonical.tests.retained_repair_curriculum_v1 import build_case, execute, audit
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import inspect, BoundExecutionError
try:
    inspect('python.software.repair.apply.verified.v1')
    repair_bound_gate = None
except BoundExecutionError as exc:
    repair_bound_gate = str(exc)

RAW_CHILD = '''import json, os, sys
from canonical.runtime.unified_cognitive_fabric_v1 import run
if os.environ.get('PROBE_NO_TYPED_PLAN') == '1':
    from canonical.runtime import swe_typed_plan_v1
    swe_typed_plan_v1.build_plan = lambda *args, **kwargs: None
out = run(json.loads(sys.argv[1]))
print(json.dumps({'pid':os.getpid(), 'output':out}, default=str))
'''
root = Path.cwd()
base = root / 'canonical/astra_runtime/tmp/coding_goal_reuse_probe'
base.mkdir(parents=True)
rows = []
state = base / 'fabric_state.json'
gap_state = Path(str(state) + '.ignorance.json')
def gap_digest():
    return hashlib.sha256(gap_state.read_bytes()).hexdigest() if gap_state.is_file() else None
for role, learn in [('teaching', True), ('cold', False), ('warm', True)]:
    gap_before = gap_digest()
    case = build_case(base / 'raw', 'floor_boundary', role)
    rel = case['project'].relative_to(root).as_posix()
    report = (base / 'raw' / ('raw_' + role + '.json')).relative_to(root).as_posix()
    goal = 'Fix the failing tests in the python source root ' + rel + ' and write the report to ' + report
    before = case['target'].read_bytes()
    test_before = case['test'].read_bytes()
    audit_before = audit(case)['returncode'] == 0
    start = time.monotonic()
    request = {'mode':'RAW_GOAL', 'payload':{'task_id':'probe-' + role, 'goal':goal},
               'options':{'state_path':str(state), 'learn':learn, 'auto_repair':False,
                          'self_improvement_max_actions':1}}
    child = subprocess.run([sys.executable, '-c', RAW_CHILD, json.dumps(request)],
                           capture_output=True, text=True, check=True, timeout=90)
    response = json.loads(child.stdout)
    out = response['output']
    result = out.get('result') or {}
    live = result.get('_live_runtime') or {}
    learning = live.get('learning') or {}
    rows.append({'role':role, 'learning_enabled':learn, 'worker_pid':response['pid'],
                 'fabric_status':out.get('status'), 'fabric_reason':out.get('reason'),
                 'status':result.get('status'), 'pass':result.get('pass') is True,
                 'semantic_acceptance_complete':result.get('semantic_acceptance_complete'),
                 'selected_capability':result.get('compiled_capability_id'),
                 'reason':result.get('reason'), 'reuse_first':live.get('reuse_first'),
                 'learning_status':learning.get('status'),
                 'knowledge_gap':result.get('knowledge_gap'),
                 'gap_count':len(json.loads(gap_state.read_text()).get('gaps', {})) if gap_state.is_file() else 0,
                 'gap_store_unchanged':gap_before == gap_digest(),
                 'permanent_reuse_authorized':learning.get('permanent_reuse_authorized'),
                 'elapsed_s':round(time.monotonic()-start, 3),
                 'source_changed':case['target'].read_bytes() != before,
                 'tests_unchanged':case['test'].read_bytes() == test_before,
                 'separate_audit_pass_before':audit_before,
                 'separate_audit_pass':audit(case)['returncode'] == 0})

# Additional fresh-process controls. A copied checkout is isolation from project
# state, not a security sandbox. All code and generated tests must be trusted.
controls = []
for role in ('alternate_repair', 'already_correct', 'audit', 'run_failing_tests',
             'question', 'unrelated', 'typed_plan_unavailable', 'explicit_audit'):
    case = build_case(base / 'controls', 'floor_boundary', role)
    if role == 'already_correct':
        result = execute('apply', base / 'controls', case)['result']
        assert result.get('pass') and audit(case)['returncode'] == 0
    rel = case['project'].relative_to(root).as_posix()
    report = (base / 'controls' / (role + '.json')).relative_to(root).as_posix()
    goals = {
        'alternate_repair': 'Repair the Python source root ' + rel + ' so that the tests pass and write the report to ' + report,
        'already_correct': 'Fix the failing tests in the python source root ' + rel + ' and write the report to ' + report,
        'audit': 'Audit the tests in the python source root ' + rel + ' and write the report to ' + report,
        'run_failing_tests': 'Run the failing tests in the python source root ' + rel + ' and write the report to ' + report,
        'question': 'Why are the failing tests in the python source root ' + rel + ' failing?',
        'unrelated': 'Calibrate the neutrino interferometer phase drift.',
        'typed_plan_unavailable': 'Fix the failing tests in the python source root ' + rel + ' and write the report to ' + report,
        'explicit_audit': 'Fix the failing tests in the python source root ' + rel + ' using python.tests.audit.unittest and write the report to ' + report,
    }
    before = case['target'].read_bytes()
    test_before = case['test'].read_bytes()
    audit_before = audit(case)['returncode'] == 0
    request = {'mode':'RAW_GOAL', 'payload':{'task_id':'control-' + role, 'goal':goals[role]},
               'options':{'state_path':str(state), 'learn':False, 'auto_repair':False}}
    env = dict(os.environ)
    if role == 'typed_plan_unavailable':
        env['PROBE_NO_TYPED_PLAN'] = '1'
    child = subprocess.run([sys.executable, '-c', RAW_CHILD, json.dumps(request)], env=env,
                           capture_output=True, text=True, check=True, timeout=90)
    response = json.loads(child.stdout)
    result = response['output'].get('result') or {}
    controls.append({'role':role, 'worker_pid':response['pid'],
                     'status':result.get('status'), 'pass':result.get('pass') is True,
                     'selected_capability':result.get('compiled_capability_id'),
                     'refused_capability':result.get('refused_capability'),
                     'reason':result.get('reason'),
                     'source_changed':case['target'].read_bytes() != before,
                     'tests_unchanged':case['test'].read_bytes() == test_before,
                     'report_exists':(root / report).exists(),
                     'separate_audit_pass_before':audit_before,
                     'separate_audit_pass':audit(case)['returncode'] == 0})

# The first apply discovers the repair via production fallback and attempts to
# teach a skill. The other two start fresh worker processes on the same held-out
# defect, with only retained-learning explicitly switched off in the cold arm.
direct = base / 'direct'
first = build_case(direct, 'floor_boundary', 'teaching')
cold = build_case(direct, 'floor_boundary', 'cold')
warm = build_case(direct, 'floor_boundary', 'warm')
cold['args']['retained_learning']['enabled'] = False
for role, case in [('teaching', first), ('cold', cold), ('warm', warm)]:
    before = case['target'].read_bytes()
    frozen = case['test'].read_bytes(), case['audit'].read_bytes()
    audit_before = audit(case)['returncode'] == 0
    x = execute('apply', direct, case)
    r = x['result']; memory = r.get('retained_learning') or {}
    teaching = memory.get('teaching') or {}
    rows.append({'role':'direct_' + role, 'worker_pid':x['pid'],
                 'status':r.get('status'), 'pass':r.get('pass') is True,
                 'retained_enabled':memory.get('enabled'), 'retained_hit':memory.get('hit'),
                 'crystallized':teaching.get('crystallized'),
                 'teaching_reason':teaching.get('reason'),
                 'search_invocations':r.get('repair_search_invocations'),
                 'process_wall_s':round(x['process_wall_s'],3),
                 'source_changed':case['target'].read_bytes() != before,
                 'tests_unchanged':(case['test'].read_bytes(), case['audit'].read_bytes()) == frozen,
                 'separate_audit_pass_before':audit_before,
                 'separate_audit_pass':audit(case)['returncode'] == 0})
print(json.dumps({'schema':'BRAIN_CODING_GOAL_REUSE_PROBE_V1',
                  'scope':'seeded defect in a pinned upstream module with authored tests; '
                          'the held-out defect is a different literal in the same module',
                  'process_note':'each raw and direct call runs in a fresh worker; raw teaching and warm share the fabric state file',
                  'repair_bound_gate':repair_bound_gate, 'rows':rows, 'controls':controls}))
"""


def main() -> None:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="brain_coding_goal_probe_") as tmp:
        copy = Path(tmp)
        shutil.copytree(ROOT, copy, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache",
                                                      "*.pyc", "tmp", ".venv", "node_modules"))
        # Prevent ambient PYTHONPATH or a user-specific store from escaping the copy.
        env = dict(os.environ, PYTHONPATH=str(copy), PYTHONDONTWRITEBYTECODE="1")
        env.pop("PROBE_NO_TYPED_PLAN", None)
        for key in list(env):
            if key.startswith("BRAIN_"):
                del env[key]
        proc = subprocess.run([sys.executable, "-c", WORKER], cwd=copy, env=env,
                              text=True, capture_output=True, timeout=180)
        if proc.returncode:
            raise RuntimeError("probe worker failed:\n" + proc.stderr[-8000:])
        result = json.loads(proc.stdout)
        result['total_wall_s_including_copy'] = round(time.monotonic() - start, 3)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
