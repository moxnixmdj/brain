"""End-to-end verification of the 3-Pillar Autonomous SWE upgrades.

All tests execute real code, real subprocesses, and real AST/test oracles with
zero mocks, zero model calls (K3 = 0), and zero bytecode leakage.
"""
from __future__ import annotations

import pathlib
import runpy

from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as egraph_engine
from canonical.swe_kernel import incremental_semantic_graph_v1 as sem_graph
from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as closed_loop
from canonical.swe_kernel import verified_skill_crystallizer_v1 as skills
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle


def test_coupled_two_file_saddle_plateau_repair_and_no_bytecode(tmp_path: pathlib.Path) -> None:
    """Two coupled files mask each other on single-file edits; closed-loop pair search solves both."""
    pkg = tmp_path / "pkg"
    tests = tmp_path / "tests"
    pkg.mkdir()
    tests.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    # Bug 1: encoder strips both ends instead of leading null bytes (`strip` -> `lstrip`)
    (pkg / "encoder.py").write_text(
        'def pack_uint(n: int) -> bytes:\n'
        '    return n.to_bytes(4, "big").strip(b"\\x00")\n',
        encoding="utf-8",
    )
    # Bug 2: service subtracts checksum offset instead of adding (`-` -> `+`)
    (pkg / "service.py").write_text(
        'from pkg.encoder import pack_uint\n\n'
        'def frame_length(n: int, header: int) -> int:\n'
        '    return len(pack_uint(n)) - header\n',
        encoding="utf-8",
    )
    # Single test checks BOTH behaviors together in one test method so neither 1-file fix passes alone!
    (tests / "test_frame.py").write_text(
        'import unittest\n'
        'from pkg.service import frame_length\n\n'
        'class FrameTests(unittest.TestCase):\n'
        '    def test_coupled_protocol(self):\n'
        '        assert frame_length(256, 3) == 5 and frame_length(1, 3) == 4\n',
        encoding="utf-8",
    )

    res = closed_loop.solve_repository_closed_loop(
        tmp_path,
        goal="Fix frame_length and pack_uint protocol framing bug",
        apply_to_source=True,
        timeout_s=30.0,
    )
    assert res["ok"] is True and res["verified"] is True, res
    assert set(res["changed_files"]) == {"pkg/encoder.py", "pkg/service.py"}
    assert not list(tmp_path.rglob("*.pyc"))
    assert not list(tmp_path.rglob("__pycache__"))


def test_ast_anchored_pure_insertion_crystallization_and_multisite_recall(tmp_path: pathlib.Path) -> None:
    """Pure guard insertion crystallizes compactly, preserves nested indentation, and recalls across sites."""
    teach_dir = tmp_path / "teach"
    teach_dir.mkdir()
    filler = "\n\n".join(
        f"def helper_{i}(x):\n    \"\"\"Helper {i}.\"\"\"\n    return x + {i}\n"
        for i in range(40)
    )
    before_src = (
        filler
        + "\n\ndef stream_batches(iterable, n):\n"
        + '    """Yield chunks of width n."""\n'
        + "    it = iter(iterable)\n"
        + "    for item in it:\n"
        + "        yield (item, n)\n"
    )
    after_src = (
        filler
        + "\n\ndef stream_batches(iterable, n):\n"
        + '    """Yield chunks of width n."""\n'
        + "    if n < 0:\n"
        + "        raise ValueError('n must be at least 0')\n"
        + "    if n == 0:\n"
        + "        return\n"
        + "    it = iter(iterable)\n"
        + "    for item in it:\n"
        + "        yield (item, n)\n"
    )
    (teach_dir / "mod.py").write_text(before_src, encoding="utf-8")
    (teach_dir / "test_mod.py").write_text(
        "import unittest\nfrom mod import stream_batches\n"
        "class T(unittest.TestCase):\n"
        "    def test_zero_unconsumed(self):\n"
        "        s = iter([1, 2])\n"
        "        self.assertEqual(list(stream_batches(s, 0)), [])\n"
        "        self.assertEqual(list(s), [1, 2])\n"
        "    def test_neg(self):\n"
        "        with self.assertRaisesRegex(ValueError, 'n must be at least 0'):\n"
        "            list(stream_batches([1], -1))\n",
        encoding="utf-8",
    )
    contract = {
        "schema_version": 1,
        "scope_id": "unit/zero_guard/v1",
        "verification_kind": "TEST_SUITE",
        "dependencies": {},
        "preconditions": {},
    }
    oracle_teach = ProjectTestOracle(teach_dir, "mod.py", ["test_mod.py"], contract["scope_id"])
    db_path = tmp_path / "skills.sqlite"
    store = skills.VerifiedSkillStore(db_path, seed=False)
    taught = store.crystallize_code_fix(
        before_snippet=before_src,
        after_snippet=after_src,
        language="python",
        contract=contract,
        training_verifier=oracle_teach,
    )
    assert taught["crystallized"] is True, taught
    assert taught["hole_count"] <= 6

    # Held-out module has TWO matching generator functions: site #1 is a decoy that MUST NOT change,
    # site #2 (`windowed_pairs`) is the broken target! Multi-site recall must skip site #1 and verify site #2.
    held_dir = tmp_path / "held"
    held_dir.mkdir()
    held_src = (
        "def untouched_eager(seq, width):\n"
        '    """Site 1 intentionally consumes first element on width 0 in its own contract."""\n'
        "    cur = iter(seq)\n"
        "    if width == 0:\n"
        "        next(cur, None)\n"
        "        return\n"
        "    for v in cur:\n"
        "        yield v\n\n"
        "class Streamer:\n"
        "    @staticmethod\n"
        "    def windowed_pairs(items, size):\n"
        '        """Indented method target (site 2)."""\n'
        "        cursor = iter(items)\n"
        "        for elem in cursor:\n"
        "            yield (elem, size)\n"
    )
    (held_dir / "target.py").write_text(held_src, encoding="utf-8")
    (held_dir / "test_target.py").write_text(
        "import unittest\nfrom target import untouched_eager, Streamer\n"
        "class T(unittest.TestCase):\n"
        "    def test_site1_preserved(self):\n"
        "        s = iter([9, 10])\n"
        "        self.assertEqual(list(untouched_eager(s, 0)), [])\n"
        "        self.assertEqual(list(s), [10])\n"
        "    def test_site2_repaired(self):\n"
        "        s = iter([4, 5])\n"
        "        self.assertEqual(list(Streamer.windowed_pairs(s, 0)), [])\n"
        "        self.assertEqual(list(s), [4, 5])\n"
        "        with self.assertRaisesRegex(ValueError, 'n must be at least 0'):\n"
        "            list(Streamer.windowed_pairs([1], -2))\n",
        encoding="utf-8",
    )
    oracle_held = ProjectTestOracle(held_dir, "target.py", ["test_target.py"], contract["scope_id"])
    recalled = store.recall_and_apply_verified(
        source_text=held_src,
        language="python",
        verifier=oracle_held,
        required_verification_kind="TEST_SUITE",
        scope_id=contract["scope_id"],
        context={"dependencies": {}, "preconditions": {}},
    )
    assert recalled is not None
    assert "        if size < 0:\n            raise ValueError('n must be at least 0')" in recalled["patched_source"]


def test_zero_hint_semantic_graph_symptom_localization_and_sound_sum_opt(tmp_path: pathlib.Path) -> None:
    """Zero-file-hint symptom localizes impacted test out of 7 suites; egraph sum opt is fast & sound."""
    repo = tmp_path / "repo"
    (repo / "core").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "core" / "__init__.py").write_text("", encoding="utf-8")
    for idx in range(6):
        (repo / "core" / f"mod_{idx}.py").write_text(f"def ok_{idx}(x):\n    return x + {idx}\n", encoding="utf-8")
        (repo / "tests" / f"test_mod_{idx}.py").write_text(
            f"import unittest\nfrom core.mod_{idx} import ok_{idx}\n"
            f"class T{idx}(unittest.TestCase):\n    def test_ok(self): self.assertEqual(ok_{idx}(1), {1 + idx})\n",
            encoding="utf-8",
        )
    (repo / "core" / "ledger.py").write_text(
        "def compute_rebate(cents: int, rate_bps: int) -> int:\n    return (cents * rate_bps) - 10000\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_ledger.py").write_text(
        "import unittest\nfrom core.ledger import compute_rebate\n"
        "class TLedger(unittest.TestCase):\n"
        "    def test_rebate(self):\n"
        "        self.assertEqual(compute_rebate(20000, 500), 1000)\n"
        "        self.assertEqual(compute_rebate(10000, 250), 250)\n",
        encoding="utf-8",
    )
    loc = sem_graph.localize_symptom_and_impacted_tests(repo, "Bug in compute_rebate basis-points division")
    assert loc["localized_files"][0] == "core/ledger.py"
    assert loc["impacted_tests"] == ["tests/test_ledger.py"]
    assert loc["total_tests_in_scope"] == 7

    solved = closed_loop.solve_repository_closed_loop(
        repo,
        goal="Fix compute_rebate calculation",
        apply_to_source=True,
        timeout_s=25.0,
    )
    assert solved["ok"] is True and solved["verified"] is True

    # Verify marshal-guarded C sum fast path is both measurably faster AND exact on floats/custom __radd__
    util = tmp_path / "util.py"
    util.write_text("def total(xs):\n    out = 0\n    for x in xs:\n        out += x\n    return out\n", encoding="utf-8")
    opt = egraph_engine.egraph_optimize_function(util, "total")
    assert opt["verified"] is True, opt
    assert opt["speedup_ratio"] > 1.0
    fn = runpy.run_path(str(util))["total"]
    assert fn([1e16, 1.0, -1e16]) == 0.0
    calls = 0

    class CustomAdd:
        def __radd__(self, other: int) -> int:
            nonlocal calls
            calls += 1
            return other + 7

    assert fn([CustomAdd(), CustomAdd()]) == 14
    assert calls == 2
