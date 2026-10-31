"""Local, real-execution benchmark; no admission or independent-verifier credit.

Run with: python -m canonical.experiments.benchmark_candidate_rendering_reuse_v1
Prints JSON only. Temporary projects and their counters are removed on exit.
The bounded-search case deliberately exhausts; it is not a successful repair.
"""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch
from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as strict


def benchmark():
    text = ''.join(f'def f{i}(x): return x < {i+3}\n' for i in range(600))
    stages = []
    searches = []
    for _ in range(3):
        started = time.perf_counter()
        tree = ast.parse(text)
        renderer = patch._CandidateRenderer(text, tree)
        outputs = []
        for key, descriptor, replace in itertools.islice(
                patch._candidate_specs(tree, [0, 3, 9999], []), 128):
            candidate = renderer.render(key, replace)
            outputs.append({'mutation': descriptor,
                            'sha256': hashlib.sha256(candidate.encode()).hexdigest()})
        elapsed = 1000 * (time.perf_counter() - started)
        stages.append({'elapsed_ms': round(elapsed, 3), 'candidate_count': len(outputs),
                       'sequence_sha256': hashlib.sha256(
                           json.dumps(outputs, sort_keys=True).encode()).hexdigest()})
        with tempfile.TemporaryDirectory(prefix='brain-render-benchmark-') as raw:
            root = Path(raw)
            source_root = root / 'src'
            source_root.mkdir()
            source = source_root / 'm.py'
            source.write_text(text)
            counter = root / 'calls.txt'
            test = source_root / 'test_m.py'
            test.write_text(
                'import unittest\nfrom pathlib import Path\nfrom m import f599\n'
                f'p=Path({str(counter)!r})\n'
                "with p.open('a') as stream: stream.write('ran\\n')\n"
                'class T(unittest.TestCase):\n'
                ' def test_target(self): self.assertEqual(f599(0),9999)\n'
                'if __name__=="__main__": unittest.main()\n')
            args = {'source_root': 'src', 'test_paths': ['src/test_m.py'],
                    'test_argv': [sys.executable, str(test)], 'output_path': 'report.json',
                    'timeout_s': 5, 'max_rounds': 1, 'max_files': 1,
                    'max_candidates_per_file': 16, 'max_total_candidates': 16}
            started = time.perf_counter()
            result = strict.run(args, root)
            elapsed = 1000 * (time.perf_counter() - started)
            if (result['pass'] is not False or result['source_restored'] is not True
                    or source.read_bytes() != text.encode()
                    or result['tested_candidate_count'] != 16
                    or len(counter.read_text().splitlines()) != 17):
                raise RuntimeError('BENCHMARK_WORK_OR_RESTORATION_MISMATCH')
            searches.append({'elapsed_ms': round(elapsed, 3), 'status': result['status'],
                             'tested_candidate_count': result['tested_candidate_count'],
                             'actual_suite_executions': len(counter.read_text().splitlines())})
    return {'render_stage': stages, 'real_bounded_search': searches,
            'render_median_ms': statistics.median(r['elapsed_ms'] for r in stages),
            'search_median_ms': statistics.median(r['elapsed_ms'] for r in searches),
            'independent_verifier_credit': False, 'source_promotion_performed': False}


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2))
