"""Real-execution tests for the Canonical Unified Polyglot SWE Spine,
front-door wiring, Option A/B proposer-behind-verifier boundary, O(1) law
crystallization/deletion, and Capability Consolidation Auditor.

All tests execute real tools (`pytest`, `gcc -fsanitize=address`, `node`) on
isolated temporary repositories without mocks or stdlib monkeypatching.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import unittest

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.swe_kernel import canonical_swe_spine_v1 as spine
from canonical.tools import capability_consolidation_audit_v1 as audit_tool


class _MaliciousAndValidProposer:
    """Deterministic untrusted proposer used to verify the Option-A verifier boundary."""

    def __init__(self, proposals: list[dict[str, str]], witness: str | None = None) -> None:
        self._proposals = proposals
        self._witness = witness
        self.patch_calls = 0
        self.witness_calls = 0

    def propose_witness(self, *, repo_root, issue_text, language, baseline_output):
        self.witness_calls += 1
        return self._witness

    def propose_patches(self, *, repo_root, issue_text, language, failure_output, candidate_files):
        self.patch_calls += 1
        return list(self._proposals)


class TestCanonicalSweSpineV1(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory(prefix="canonical_swe_spine_")
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_fail_closed_on_green_suite_leaves_workspace_byte_identical(self) -> None:
        (self.root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (self.root / "test_calc.py").write_text(
            "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )
        before_bytes = (self.root / "calc.py").read_bytes()

        res = spine.solve_repository_task(
            self.root,
            test_file="test_calc.py",
            issue_text="Make the module cleaner somehow.",
            timeout_s=20.0,
        )
        self.assertFalse(res["solved"])
        self.assertEqual(res["status"], "FAIL_CLOSED")
        self.assertEqual(res["reason"], "NO_DEFECT_EVIDENCE_GREEN_SUITE")
        self.assertEqual(res["model_calls"], 0)
        self.assertEqual(res["modified_files"], [])
        self.assertEqual((self.root / "calc.py").read_bytes(), before_bytes)

    def test_02_python_zero_model_fail_to_pass_and_on_disk_verification(self) -> None:
        (self.root / "bounds.py").write_text(
            "def clamp_nonneg(value, limit):\n"
            "    if value < 0:\n"
            "        return 0\n"
            "    if value < limit:\n"
            "        return limit\n"
            "    return value\n",
            encoding="utf-8",
        )
        (self.root / "test_bounds.py").write_text(
            "from bounds import clamp_nonneg\n\n"
            "def test_within_limit():\n"
            "    assert clamp_nonneg(3, 10) == 3\n\n"
            "def test_above_limit():\n"
            "    assert clamp_nonneg(15, 10) == 10\n\n"
            "def test_negative():\n"
            "    assert clamp_nonneg(-2, 10) == 0\n",
            encoding="utf-8",
        )

        res = spine.solve_repository_task(
            self.root,
            test_file="test_bounds.py",
            timeout_s=25.0,
        )
        self.assertTrue(res["solved"], res)
        self.assertEqual(res["status"], "PASS_VERIFIED_ON_DISK")
        self.assertEqual(res["model_calls"], 0)
        self.assertEqual(res["authority"], "NONE_SANDBOX")
        self.assertIn("bounds.py", res["modified_files"])
        ns: dict[str, object] = {}
        exec((self.root / "bounds.py").read_text(encoding="utf-8"), ns)
        fn = ns["clamp_nonneg"]
        self.assertEqual(fn(3, 10), 3)
        self.assertEqual(fn(15, 10), 10)
        self.assertEqual(fn(-2, 10), 0)
        self.assertEqual(fn(10, 10), 10)

    def test_03_multifile_zipper_repairs_relocated_symbol_import(self) -> None:
        pkg = self.root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "_old.py").write_text("def stay():\n    return 'ok'\n", encoding="utf-8")
        (pkg / "_new_home.py").write_text("def relocated_helper(x):\n    return x * 2\n", encoding="utf-8")
        (pkg / "consumer.py").write_text(
            "from ._old import stay, relocated_helper\n\n"
            "def compute(n):\n"
            "    return f'{stay()}:{relocated_helper(n)}'\n",
            encoding="utf-8",
        )
        (self.root / "test_pkg.py").write_text(
            "from pkg.consumer import compute\n\n"
            "def test_compute():\n"
            "    assert compute(21) == 'ok:42'\n",
            encoding="utf-8",
        )

        res = spine.solve_repository_task(
            self.root,
            test_file="test_pkg.py",
            timeout_s=25.0,
        )
        self.assertTrue(res["solved"], res)
        self.assertEqual(res["reason"], "SOLVED_BY_MULTI_FILE_ZIPPER")
        self.assertEqual(res["model_calls"], 0)
        self.assertIn("pkg/consumer.py", res["modified_files"])
        consumer_txt = (pkg / "consumer.py").read_text(encoding="utf-8")
        self.assertIn("from ._new_home import relocated_helper", consumer_txt)
        self.assertIn("from ._old import stay", consumer_txt)

    def test_04_option_a_untrusted_proposer_rejects_bad_patches_and_crystallizes_o1_law(self) -> None:
        # Multi-line semantic bug outside simple single-op mutations
        buggy_src = (
            "def normalize_tag(raw, prefix):\n"
            "    text = raw.strip()\n"
            "    return prefix + ':' + text\n"
        )
        fixed_src = (
            "def normalize_tag(raw, prefix):\n"
            "    text = '_'.join(raw.strip().lower().split())\n"
            "    return prefix.lower() + ':' + text\n"
        )
        # 1. Test tampering (must be rejected)
        # 2. Input-dependency dropping (drops `prefix` param -> rejected by dep_gate)
        # 3. Wrong logic (rejected by real pytest)
        # 4. Valid patch (independently verified & crystallized)
        bad_drop_param = (
            "def normalize_tag(raw, prefix):\n"
            "    return 'env:hello_world'\n"
        )
        bad_logic = (
            "def normalize_tag(raw, prefix):\n"
            "    return prefix + ':' + raw.strip().upper()\n"
        )
        test_src = (
            "from tags import normalize_tag\n\n"
            "def test_normalize():\n"
            "    assert normalize_tag('  Hello   World ', 'ENV') == 'env:hello_world'\n"
            "    assert normalize_tag('Foo\\tBar', 'TAG') == 'tag:foo_bar'\n"
        )

        repo1 = self.root / "repo1"
        repo1.mkdir()
        (repo1 / "tags.py").write_text(buggy_src, encoding="utf-8")
        (repo1 / "test_tags.py").write_text(test_src, encoding="utf-8")

        store_path = self.root / "law_store.json"
        store = spine.CanonicalLawStore(store_path)

        # First: verify purely malicious proposer fails closed & leaves disk untouched
        bad_proposer = _MaliciousAndValidProposer(
            proposals=[
                {"test_tags.py": "def test_normalize():\n    assert True\n"},
                {"tags.py": bad_drop_param},
                {"tags.py": bad_logic},
            ]
        )
        bad_res = spine.solve_repository_task(
            repo1,
            test_file="test_tags.py",
            timeout_s=20.0,
            proposer=bad_proposer,
            law_store=store,
        )
        self.assertFalse(bad_res["solved"])
        self.assertEqual(bad_res["status"], "FAIL_CLOSED")
        self.assertEqual(len(bad_res["proposer_rejections"]), 3)
        self.assertTrue(any("TEST_FILE_TAMPERING_BLOCKED" in r for r in bad_res["proposer_rejections"]))
        self.assertTrue(any("INPUT_DEPENDENCY_LOST" in r for r in bad_res["proposer_rejections"]))
        self.assertTrue(any("VERIFIER_TESTS_FAILED" in r for r in bad_res["proposer_rejections"]))
        self.assertEqual((repo1 / "tags.py").read_text(encoding="utf-8"), buggy_src)

        # Second: valid proposer succeeds behind verifier and crystallizes law into O(1) store
        good_proposer = _MaliciousAndValidProposer(
            proposals=[
                {"tags.py": bad_logic},
                {"tags.py": fixed_src},
            ]
        )
        ok_res = spine.solve_repository_task(
            repo1,
            test_file="test_tags.py",
            timeout_s=20.0,
            proposer=good_proposer,
            law_store=store,
        )
        self.assertTrue(ok_res["solved"], ok_res)
        self.assertEqual(ok_res["reason"], "SOLVED_BY_VERIFIED_PROPOSER")
        self.assertEqual(ok_res["model_calls"], 1)
        self.assertIsNotNone(ok_res["crystallized_law_id"])
        self.assertEqual(store.count(), 1)

        # Third: fresh second repo solved via O(1) law recall with ZERO model calls
        repo2 = self.root / "repo2"
        repo2.mkdir()
        (repo2 / "tags.py").write_text(buggy_src, encoding="utf-8")
        (repo2 / "test_tags.py").write_text(test_src, encoding="utf-8")

        reloaded_store = spine.CanonicalLawStore(store_path)
        recall_res = spine.solve_repository_task(
            repo2,
            test_file="test_tags.py",
            timeout_s=20.0,
            proposer=None,
            law_store=reloaded_store,
        )
        self.assertTrue(recall_res["solved"], recall_res)
        self.assertEqual(recall_res["reason"], "SOLVED_BY_O1_LAW_STORE_RECALL")
        self.assertEqual(recall_res["model_calls"], 0)

        # Fourth: O(1) exact deletion removes law with 0 residual hits
        law_id = str(ok_res["crystallized_law_id"])
        self.assertTrue(reloaded_store.delete(law_id))
        self.assertEqual(reloaded_store.count(), 0)
        self.assertEqual(reloaded_store.lookup("python", "AssertionError"), [])

    def test_05_c_gcc_asan_real_null_or_uaf_repair(self) -> None:
        if shutil.which("gcc") is None:
            self.skipTest("gcc not installed")
        (self.root / "uaf.c").write_text(
            "#include <stdlib.h>\n"
            "#include <stdio.h>\n"
            "int main(void) {\n"
            "    int *p = (int *)malloc(sizeof(int));\n"
            "    *p = 42;\n"
            "    free(p);\n"
            "    int v = *p;\n"
            "    printf(\"%d\\n\", v);\n"
            "    return (v == 42) ? 0 : 1;\n"
            "}\n",
            encoding="utf-8",
        )
        res = spine.solve_repository_task(
            self.root,
            c_sources=["uaf.c"],
            language="c",
            timeout_s=25.0,
        )
        self.assertTrue(res["solved"], res)
        self.assertEqual(res["language"], "c")
        self.assertEqual(res["model_calls"], 0)

    def test_06_javascript_node_real_repair(self) -> None:
        if shutil.which("node") is None:
            self.skipTest("node not installed")
        (self.root / "math_util.js").write_text(
            "function isAdult(age) {\n"
            "  return age > 18;\n"
            "}\n"
            "module.exports = { isAdult };\n",
            encoding="utf-8",
        )
        (self.root / "test_math_util.js").write_text(
            "const assert = require('assert');\n"
            "const { isAdult } = require('./math_util');\n"
            "assert.strictEqual(isAdult(18), true);\n"
            "assert.strictEqual(isAdult(21), true);\n"
            "assert.strictEqual(isAdult(17), false);\n",
            encoding="utf-8",
        )
        res = spine.solve_repository_task(
            self.root,
            test_file="test_math_util.js",
            language="javascript",
            timeout_s=25.0,
        )
        self.assertTrue(res["solved"], res)
        self.assertEqual(res["language"], "javascript")
        self.assertEqual(res["model_calls"], 0)

    def test_07_front_door_unified_model_wires_canonical_swe_spine(self) -> None:
        (self.root / "check.py").write_text(
            "def is_positive(x):\n"
            "    return x < 0\n",
            encoding="utf-8",
        )
        (self.root / "test_check.py").write_text(
            "from check import is_positive\n\n"
            "def test_pos():\n"
            "    assert is_positive(5) is True\n"
            "    assert is_positive(-3) is False\n",
            encoding="utf-8",
        )
        model = bum.open_model()
        out = model.act_or_learn(
            "Repair failing python repo tests via canonical SWE spine",
            inputs={
                "swe_repo_task": {
                    "repo_root": str(self.root),
                    "test_file": "test_check.py",
                    "timeout_s": 25.0,
                }
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["operation"], "SOLVE_SWE_REPO")
        self.assertTrue(out["canonical_swe_spine"]["solved"])
        self.assertEqual(out["canonical_swe_spine"]["model_calls"], 0)

    def test_08_capability_consolidation_audit_reports_fresh_truth(self) -> None:
        report = audit_tool.run_audit()
        self.assertEqual(report["authority"], "NONE_SANDBOX")
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["true_capabilities"]["specs_total"], 11)
        self.assertEqual(report["true_capabilities"]["in_ledger_count"], 11)
        self.assertEqual(report["true_capabilities"]["stale_count"], 0)
        self.assertEqual(report["coq_formal_certificates"]["qed_theorems"], 99)
        self.assertTrue(report["coq_formal_certificates"]["zero_admitted"])
        self.assertTrue(report["swe_kernel_consolidation"]["spine_wired_into_front_door"])
        tiers = report["unified_model_registry_truth"]["tier_counts"]
        self.assertEqual(sum(tiers.values()), report["unified_model_registry_truth"]["total_named_in_unified_model"])
        q_paths = {row["path"] for row in report["quarantined_receipts"]}
        self.assertIn("canonical/verification/AST_IR_ANTI_UNIFICATION_ABLATION_20261124_V1.json", q_paths)


if __name__ == "__main__":
    unittest.main()
