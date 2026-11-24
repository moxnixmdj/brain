"""Reproduce five read-only issue localization and adapter-refusal probes.

Run: python3 -m canonical.tools.measure_swe_real_localization_v1 OUTPUT.json
The rows come from a pinned third-party mirror. Source tarballs are requested by
base commit but are not git-object verified. No task code or solver is run;
this is neither a repair gate nor an official benchmark score.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from canonical.tools.swebench_issue_localizer_v1 import localize_issue
from canonical.tools import swebench_verified_epistemic_adapter_v1 as adapter

IDS = ('astropy__astropy-12907', 'astropy__astropy-13033', 'astropy__astropy-13236',
       'astropy__astropy-13398', 'astropy__astropy-13453')
MIRROR_COMMIT = '7548222e5f33b4e760b3cbeb193e5403f8e2e6cc'


def _row(iid: str) -> dict[str, str]:
    location = f'problems/swe/swebench-verified/{iid}.yaml'
    data = subprocess.run(
        ['gh', 'api', f'repos/hyang0129/onlycodes/contents/{location}?ref={MIRROR_COMMIT}',
         '--jq', '.content'], capture_output=True, text=True, check=True, timeout=60,
    ).stdout
    raw = base64.b64decode(data).decode('utf-8')
    fields = {}
    for name in ('instance_id', 'repo', 'base_commit', 'problem_statement'):
        match = re.search(r'^' + name + r': (.*)$', raw, re.M)
        if not match:
            raise ValueError('ROW_FIELD_MISSING:' + name)
        value = match.group(1)
        fields[name] = json.loads(value) if value.startswith('"') else value.strip("'")
    if (fields['instance_id'] != iid or fields['repo'] != 'astropy/astropy'
            or not re.fullmatch('[0-9a-f]{40}', fields['base_commit'])):
        raise ValueError('ROW_INVALID')
    return fields


def _copy_archive(url: str, archive: Path, root: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as dst:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > 150_000_000:
                raise ValueError('ARCHIVE_SIZE_LIMIT')
            digest.update(block)
            dst.write(block)
    count = 0
    expanded = 0
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            count += 1
            if count > 30_000:
                raise ValueError('ARCHIVE_ENTRY_LIMIT')
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            rel = parts[1:]
            if member.name.startswith('/') or any(part in ('', '.', '..') for part in rel):
                raise ValueError('ARCHIVE_PATH_INVALID')
            path = root.joinpath(*rel)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                expanded += member.size
                if member.size > 20_000_000 or expanded > 500_000_000:
                    raise ValueError('ARCHIVE_EXPANSION_LIMIT')
                path.parent.mkdir(parents=True, exist_ok=True)
                stream = tar.extractfile(member)
                if stream is None:
                    raise ValueError('ARCHIVE_FILE_MISSING')
                # Preserve entry count, but localizer only consumes Python bytes.
                if path.suffix == '.py':
                    path.write_bytes(stream.read())
                else:
                    path.touch()
            # Symlinks, hardlinks and other special members are not materialized.
    return digest.hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m canonical.tools.measure_swe_real_localization_v1 OUTPUT.json')
    localizer_path = Path(__file__).with_name('swebench_issue_localizer_v1.py')
    out = {
        'schema': 'LOCAL_SWE_REAL_ISSUE_LOCALIZATION_AND_REFUSAL_V1',
        'source': 'https://github.com/hyang0129/onlycodes', 'source_commit': MIRROR_COMMIT,
        'localizer_sha256': hashlib.sha256(localizer_path.read_bytes()).hexdigest(),
        'adapter_sha256': hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),
        'note': ('Read-only localization and adapter refusal only; no repair, test, receipt, or score. '
                 'Rows from a pinned third-party mirror. Source archives requested by base commit but '
                 'not git-object verified. No gold/test fields passed to localizer or adapter. '
                 'Non-Python regular files are empty placeholders; symlinks and special files omitted.'),
        'instances': [],
    }
    for iid in IDS:
        row = _row(iid)
        url = 'https://codeload.github.com/' + row['repo'] + '/tar.gz/' + row['base_commit']
        with tempfile.TemporaryDirectory(prefix='real_swe_localize_') as tmp:
            temp = Path(tmp)
            root = temp / 'tree'
            root.mkdir()
            archive_hash = _copy_archive(url, temp / 'repo.tar.gz', root)
            result = localize_issue(row['problem_statement'], root)

            def forbidden_solver(*args, **kwargs):
                raise AssertionError('SOLVER_MUST_NOT_RUN')

            prediction, trace = adapter.solve_one(
                row, solve_fn=forbidden_solver, repos_root=temp, workdir=temp,
                model_name=adapter.DEFAULT_MODEL_NAME, mode='EPISTEMIC',
            )
            if trace['outcome'] != 'ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK' or prediction['model_patch']:
                raise RuntimeError('EXPECTED_ADAPTER_REFUSAL_MISSING')
            out['instances'].append({
                'instance_id': iid, 'repo': row['repo'], 'base_commit': row['base_commit'],
                'problem_statement_sha256': hashlib.sha256(row['problem_statement'].encode()).hexdigest(),
                'source_archive_sha256': archive_hash, 'localization': result,
                'prediction': prediction, 'adapter_trace': trace,
            })
            ranked = result.get('ranked_candidates', {})
            print(iid, 'scan_complete=', ranked.get('scan_complete'),
                  'targets=', len(ranked.get('target_paths', [])),
                  'tests=', len(ranked.get('test_targets', [])), trace['outcome'], flush=True)
    out.update(count=len(out['instances']), repair_runs=0, verified_patches=None)
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
