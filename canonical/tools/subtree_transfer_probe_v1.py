"""Offline, source-only memory ablation. Never runs target code or reads a gold edit.

One previously generated Brain repair is the teacher. For each product-source
root in file order, each arm gets the same source and a single proposal per
file. The first proposal (if any) is frozen for a separate grader; no choice
by verifier reward. Run with --help for required inputs. Output is scratch.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import time
import tokenize

from canonical.swe_kernel.petri_cow_splicing_engine_v1 import AdmissionFilteredSkillStore

TEACHER = '05f6fd0df4ecbd104eb7a229f9f185c2484dee69'
PARENT_FILE_HASH = 'cb242cbfa3190e729829ceb9292cdc5ab1856ef5ee014c501ffb110fcd3f574f'
EVIDENCE = Path(__file__).resolve().parents[1] / 'verification'
ARMS = ('empty', 'raw_traces', 'generalized')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def teach(parent: Path, destination: Path) -> dict:
    start = time.perf_counter()
    source = parent.read_bytes()
    if digest(source) != PARENT_FILE_HASH:
        raise ValueError('wrong teacher parent source')
    receipt = EVIDENCE / 'MULTI_PRODUCER_NORMALIZATION_20261124_V9.json'
    replay = EVIDENCE / 'INDEPENDENT_REPLAY_FIVE_20261124_V1.json'

    def row(path: Path) -> dict:
        found, = (r for r in json.loads(path.read_bytes())['rows'] if r['sha'] == TEACHER)
        if found.get('verified') is not True:
            raise ValueError('no recorded passing teacher')
        return found

    episode, check = row(receipt), row(replay)
    if check['returncode'] != 0 or check['passed'] < 1 or check['errors'] or check['failed']:
        raise ValueError('teacher check incomplete')
    store = AdmissionFilteredSkillStore(destination)
    ok, skill = store.try_admit_subtree(
        domain='swe_python', concrete_before=source.decode(), concrete_after=episode['candidate'],
        verified=True, goal_relevant=True, probes_before_success=episode['evaluations'] - 1,
        raw_episode_bytes=len(source) + len(episode['candidate'].encode()),
        source_fingerprint=digest(source), witness_inputs=[{'repo': episode['repo'], 'commit': TEACHER}],
        revalidation_probe={'test_target': 'tests/test_arguments.py', 'replay_record': replay.name},
    )
    if not ok:
        raise ValueError(skill)
    r = store.records[skill]
    return {'commit': TEACHER, 'parent_source_sha256': digest(source), 'teacher_candidate_sha256':
            digest(episode['candidate'].encode()), 'skill_id': skill, 'observations': 1,
            'schema_bytes': len(r.lhs_ir_sexpr.encode()) + len(r.rhs_ir_sexpr.encode()),
            'raw_window_bytes': len((r.concrete_before + r.concrete_after).encode()),
            'store_file_bytes': destination.stat().st_size, 'prior_teacher_tests_passed': check['passed'],
            'teach_seconds': round(time.perf_counter() - start, 4)}


def probe(root: Path, store_file: Path, scratch: Path) -> dict:
    if not root.is_dir():
        raise ValueError(f'missing product tree: {root}')
    # Reload from disk for each treatment. The empty arm contains no records;
    # the raw arm has the same witness window but no identifier substitution.
    stores = {mode: AdmissionFilteredSkillStore(None if mode == 'empty' else store_file,
              mode='generalized' if mode == 'empty' else mode) for mode in ARMS}
    rows = {mode: {'files_with_proposal': 0, 'first_candidate': None} for mode in ARMS}
    paths = sorted(root.rglob('*.py'))
    if not paths:
        raise ValueError('no Python product source')
    errors = []
    manifest = hashlib.sha256()
    lookup = dict.fromkeys(ARMS, 0.0)
    started = time.monotonic()
    for path in paths:
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append([rel, 'symlink_not_read'])
            continue
        try:
            manifest.update(rel.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
            with tokenize.open(path) as f:
                text = f.read()
            ast.parse(text)  # name compatibility failures; do not drop from denominator
        except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
            errors.append([rel, type(exc).__name__])
            continue
        for mode, store in stores.items():
            at = time.perf_counter()
            hits = store.retrieve_for_subtree(text, max_matches=1)
            lookup[mode] += time.perf_counter() - at
            if not hits:
                continue
            row = rows[mode]
            row['files_with_proposal'] += 1
            if row['first_candidate'] is None:
                data = hits[0][0].encode()
                out = scratch / mode / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                row['first_candidate'] = {'path': rel, 'sha256': digest(data)}
    for mode in ARMS:
        rows[mode]['lookup_seconds'] = round(lookup[mode], 4)
    return {'files': len(paths), 'parsed_files': len(paths) - len(errors), 'unreadable': errors,
            'source_manifest_sha256': manifest.hexdigest(), 'arms': rows,
            'probe_seconds': round(time.monotonic() - started, 3)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True, help='original Click parent core.py')
    parser.add_argument('--product-root', type=Path, action='append', required=True,
                        help='directory of input sources only; exclude tests and later revisions')
    parser.add_argument('--scratch', type=Path, required=True, help='new directory for a store and proposals')
    args = parser.parse_args()
    args.scratch.mkdir(exist_ok=False)
    memory = args.scratch / 'store.json'
    result = {'teacher': teach(args.parent, memory), 'targets': [
        probe(root, memory, args.scratch / str(i)) for i, root in enumerate(args.product_root)]}
    print(json.dumps(result, indent=2))
