"""Local index/cache benchmark with real parsers, not capability admission.

Run: python -m canonical.experiments.benchmark_tree_sitter_cache_v1
JSON goes to stdout; temporary fixture projects are removed on exit.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/tree_sitter_swe'


def benchmark():
    rows = []
    for repeat in range(3):
        with tempfile.TemporaryDirectory(prefix='brain-index-benchmark-') as raw:
            root = Path(raw)
            shutil.copytree(FIXTURE, root / 'src')
            for folder in ['node_modules', 'vendor']:
                base = root / 'src' / folder / 'package'
                base.mkdir(parents=True)
                for number in range(2000):
                    (base / f'ignored_{number}.py').write_text(f'x = {number}\n')
            args = {'source_root': 'src', 'output_path': 'index.json'}
            for mode in ['cold', 'warm', 'one_changed']:
                if mode == 'one_changed':
                    path = root / 'src/python/calc.py'
                    path.write_bytes(path.read_bytes() + b'# one edit\n')
                parses = []
                reads = []
                previous = sys.getprofile()
                def observe(frame, event, arg):
                    if event != 'call':
                        return
                    if frame.f_code is kernel.parse_bytes.__code__:
                        parses.append(frame.f_locals['language'])
                    if (frame.f_code is Path.read_bytes.__code__
                            and root / 'src' in frame.f_locals['self'].parents):
                        reads.append(frame.f_locals['self'])
                try:
                    sys.setprofile(observe)
                    started = time.perf_counter()
                    result = index.run(args, root)
                    elapsed = 1000 * (time.perf_counter() - started)
                finally:
                    sys.setprofile(previous)
                artifact = json.loads((root / 'index.json').read_bytes())
                expected = 11 if mode == 'cold' else 1 if mode == 'one_changed' else 0
                if (result['file_count'] != 11 or len(parses) != expected
                        or len(parses) != result['parsed_file_count'] or len(reads) != 11):
                    raise RuntimeError('BENCHMARK_WORK_MISMATCH')
                rows.append({'repeat': repeat + 1, 'mode': mode, 'elapsed_ms': round(elapsed, 3),
                             'parsed': result['parsed_file_count'], 'reused': result['reused_file_count'],
                             'actual_parser_calls': len(parses), 'actual_source_reads': len(reads),
                             'rows_sha256': kernel.json_sha256(artifact['files'])})
    return {'rows': rows,
            'medians_ms': {mode: statistics.median(r['elapsed_ms'] for r in rows if r['mode'] == mode)
                           for mode in ['cold', 'warm', 'one_changed']},
            'scope': '11 fixture files, 8 languages, 4000 ignored files; profiled timings',
            'independent_verifier_credit': False, 'source_promotion_performed': False}


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2))
