# PROJECT_BRAIN
"""Independent real gates sharing an output directory must not share scratch."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sys
import threading

import pytest

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as test_gate
from canonical.runtime.bound_capabilities import python_review_diff_coverage_gate as coverage_gate
from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as mutation_gate
from canonical.runtime.bound_capabilities import python_review_diff_perf_gate as perf_gate


@pytest.mark.parametrize("module", [test_gate, coverage_gate, mutation_gate, perf_gate],
                         ids=["test-gate", "coverage-gate", "mutation-gate", "perf-gate"])
@pytest.mark.parametrize("run_number", range(4))
def test_concurrent_identical_diffs_have_independent_scratch(tmp_path, monkeypatch, module, run_number):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    if module is coverage_gate:
        pytest.importorskip("coverage", reason="verified coverage requires coverage.py")
    anchor = tmp_path / "anchor"
    (anchor / "tests").mkdir(parents=True)
    (anchor / "subject.py").write_text("def compute():\n    return 1\n")
    (anchor / "bench.py").write_text("from subject import compute\ndef bench():\n"
                                    "    for _ in range(1000):\n        compute()\n")
    (anchor / "tests/test_subject.py").write_text(
        "from subject import compute\ndef test_compute():\n    assert compute() == 2\n")
    (tmp_path / "change.diff").write_text(
        "--- a/subject.py\n+++ b/subject.py\n@@ -1,2 +1,2 @@\n"
        " def compute():\n-    return 1\n+    return 2\n")
    # Both outputs are different, but their parent and diff are the same.
    barrier = threading.Barrier(2)

    def work(label):
        barrier.wait(timeout=30)
        args = {"anchor_path": "anchor", "diff_path": "change.diff",
                "output_path": f"out/{run_number}-{label}.json",
                "python_executable": sys.executable, "timeout_s": 30}
        if module is perf_gate:
            args.update(bench_path="bench.py", repeats=3, tolerance=1.0)
        return module.run(args, tmp_path)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(work, label) for label in ("a", "b")]
        results = [future.result() for future in futures]
    assert all(result["output_verified"] for result in results)
    if module in (test_gate, coverage_gate, mutation_gate):
        assert all(result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE" for result in results)
        assert all(result["local_gate"] == "PASS" and not result["verified"] for result in results)
    else:
        # Concurrent host timing is noisy; this test is about independent
        # execution/cleanup, not a performance verdict.
        assert all(result["gate"] in {"PASS", "FAIL", "UNCLEAR"} for result in results)
    assert {result["output_path"] for result in results} == {
        f"out/{run_number}-a.json", f"out/{run_number}-b.json"}
    assert not any(p.name.startswith(("_gate_tree_", "_cov_tree_", "_mut_tree_", "_perf_"))
                   for p in (tmp_path / "out").iterdir())
