"""Account for every preselected Harbor trial, including missing trials.

Host side, after artifact path checks. A zero from a verifier is a graded
failure. A missing reward, failed producer, or missing Pro patch replay is not
one. Nothing here runs a task or claims an official aggregate score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _object(path: Path) -> dict:
    obj = json.loads(path.read_bytes())
    if not isinstance(obj, dict):
        raise ValueError('expected object')
    return obj


def audit(jobs: Path, ids: list[str], *, pro: bool) -> dict:
    if not ids or len(ids) != len(set(ids)) or any(not i.strip() for i in ids):
        raise ValueError('empty or duplicate selection')
    issues = []
    prefix = 'swebench-pro/' if pro else 'terminal-bench/'

    def trials(job: str) -> dict:
        found = {}
        for path in sorted((jobs / job).glob('*/result.json')):
            try:
                result = _object(path)
                name = result['task_name']
                if not isinstance(name, str) or name not in {prefix + i for i in ids}:
                    raise ValueError('unexpected task name')
                key = name[len(prefix):]
                if key in found:
                    found[key] = None  # ambiguous: neither result is admissible
                    raise ValueError('duplicate task')
                found[key] = (path.parent, result)
            except (OSError, ValueError, KeyError) as exc:
                issues.append(f'{job}/{path.parent.name}: {exc}')
        return found

    producers = trials('brain-pro-smoke' if pro else 'brain-tb4-smoke')
    graders = trials('brain-pro-smoke-regrade') if pro else producers
    rows = []
    for task in ids:
        row = {'task': task, 'reward': None}
        rows.append(row)
        try:
            if not producers.get(task) or not graders.get(task):
                raise ValueError('missing or ambiguous trial')
            src, producer = producers[task]
            dst, grader = graders[task]
            if producer.get('exception_info') or grader.get('exception_info'):
                raise ValueError('Harbor trial exception')
            trace = _object(src / 'agent/brain_epistemic_trace.json')
            row.update(agent_status=trace['status'], cycles=trace.get('cycles'))
            if trace.get('external_harbor_vm_eval_status') != 'EXPERIMENTAL_DISPATCH__UNVERIFIED':
                raise ValueError('missing experimental producer dispatch')
            if pro:
                patch = src / 'agent/model.patch'
                row['patch_bytes'] = patch.stat().st_size
                replay = _object(dst / 'agent/replay.json')
                if trace.get('patch_emitted') is not True:
                    raise ValueError('no producer patch')
                if row['patch_bytes']:
                    if replay.get('apply_rc') != 0 or Path(replay['patch']).resolve() != patch.resolve():
                        raise ValueError('patch not replayed')
                elif replay['patch'] is not None:
                    raise ValueError('empty patch replay mismatch')
            reward = grader['verifier_result']['rewards']['reward']
            if type(reward) not in (int, float) or not 0 <= reward <= 1:
                raise ValueError('invalid verifier reward')
            row['reward'] = reward
        except (ValueError, KeyError, OSError, TypeError) as exc:
            row['ungraded_reason'] = str(exc)
            issues.append(f'{task}: {exc}')
    return {'selected_count': len(ids), 'rows': rows, 'issues': issues,
            'note': 'Experimental cold-store slice only; not a leaderboard score.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jobs', type=Path)
    args = parser.parse_args()
    incomplete = False
    for pro, selection, output, title in (
        (True, 'selected_hard51_ids.txt', 'smoke_audit.json', 'HARBOR_SMOKE_AUDIT'),
        (False, 'selected_tb41_ids.txt', 'tb4_audit.json', 'HARBOR_TB4_AUDIT'),
    ):
        report = audit(args.jobs, (args.jobs / selection).read_text().splitlines(), pro=pro)
        (args.jobs / output).write_text(json.dumps(report, indent=2) + '\n')
        message = json.dumps(report, separators=(',', ':')).replace('%', '%25')
        print(f'::warning title={title}::{message}')
        incomplete |= bool(report['issues'])
    raise SystemExit(1 if incomplete else 0)
