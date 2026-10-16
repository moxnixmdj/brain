"""Promoted extended capabilities: reproducible, import-safe, and reachable from plain goals."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import autonomous_capability_inventory_v1 as inventory  # noqa: E402
from canonical.runtime import extended_capability_promoter_v1 as promoter  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_extended_capability_promoter_v1"
REL = WORK.relative_to(ROOT).as_posix()
STATE = ROOT / "canonical/astra_runtime/state"
HAS_SYMPY = importlib.util.find_spec("sympy") is not None
BATCH = "bytes_research_tools"


def _extended() -> dict:
    return json.loads(promoter.EXTENDED.read_text(encoding="utf-8"))["capabilities"]


def _report() -> dict:
    return json.loads(promoter.report_path(BATCH).read_text(encoding="utf-8"))


class PromoterTests(unittest.TestCase):
    def setUp(self):
        if WORK.exists():
            shutil.rmtree(WORK)
        WORK.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, WORK, True)

    def _solve(self, goal: str, tag: str) -> dict:
        task_id = "TEST_PROMOTER_%s_%d" % (tag, os.getpid())
        try:
            return adm.solve({"task_id": task_id, "goal": goal})
        finally:
            for p in STATE.glob(task_id + "__*"):
                p.unlink()

    def test_check_mode_reproduces_registry_and_report(self):
        self.assertEqual(promoter.main(["--batch", BATCH, "--check"]), 0)

    def test_registry_holds_exactly_the_reported_promotions(self):
        report = _report()
        promoted = {o["capability_id"] for o in report["outcomes"] if o["outcome"] == "PROMOTED"}
        self.assertEqual(len(promoted), report["promoted_count"])
        self.assertGreaterEqual(len(promoted), 1)
        verified = {cid for cid, e in _extended().items() if e.get("status") == "VERIFIED_BOUND_CAPABILITY"}
        self.assertEqual(verified, promoted)
        live = load_verified_registry(include_extended=True)
        for cid in promoted:
            self.assertIn(cid, live)
            entry = live[cid]
            self.assertGreater(entry["verification"]["positive_cases_passed"], 0)
            self.assertGreater(entry["verification"]["bad_inputs_failed_closed"], 0)
            self.assertTrue((ROOT / entry["source"]["adapter_path"]).is_file())
        rejected = [o for o in report["outcomes"] if o["outcome"] != "PROMOTED"]
        for outcome in rejected:
            self.assertNotIn(outcome["capability_id"], live)

    def test_every_batch_file_is_accounted_for_and_inventory_stays_unexecutable(self):
        report = _report()
        files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / report["directory"]).glob("*.py"))
        self.assertEqual(sorted(report["files"]), files)
        extended = _extended()
        for rel, row in report["files"].items():
            entry = extended.get(rel + ".auto.v1")
            self.assertIsNotNone(entry, rel)
            self.assertEqual(entry["status"], "UNVERIFIED_INVENTORY")
            self.assertEqual(entry.get("promoted_to", []), row["promoted_to"])
        live = load_verified_registry(include_extended=True)
        self.assertFalse([cid for cid in live if cid.endswith(".auto.v1")])

    def test_loader_refuses_files_with_import_time_effects_without_running_them(self):
        sentinel = WORK / "sentinel.txt"
        tool = WORK / "effectful_tool.py"
        tool.write_text("from pathlib import Path\nPath(%r).write_text('ran')\n\ndef helper():\n    return 1\n" % str(sentinel), encoding="utf-8")
        with self.assertRaises(loader.ResearchToolUnsafe):
            loader.load_symbol(ROOT, REL + "/effectful_tool.py", "helper")
        self.assertFalse(sentinel.exists())
        clean = WORK / "clean_tool.py"
        clean.write_text("PIN = 'abc'\n\ndef helper():\n    return 41 + 1\n", encoding="utf-8")
        self.assertEqual(loader.load_symbol(ROOT, REL + "/clean_tool.py", "helper")(), 42)
        with self.assertRaises(loader.ResearchToolUnsafe):
            loader.load_symbol(ROOT, "../outside.py", "helper")

    def test_plain_goals_reach_promoted_capabilities(self):
        (WORK / "tree/pkg").mkdir(parents=True)
        (WORK / "tree/a.py").write_text("A = 1\n", encoding="utf-8")
        (WORK / "tree/pkg/b.py").write_text('"""Doc."""\ndef f():\n    """F doc."""\n    return 1\n', encoding="utf-8")
        (WORK / "doc.json").write_text('{"b": 1, "a": [1, 2]}', encoding="utf-8")
        cases = [
            ("python.source_tree.manifest.sha256",
             f"Compute the sha256 manifest of the python source tree {REL}/tree and save it to {REL}/manifest.json.", "manifest.json"),
            ("python.source.docstrings.strip",
             f"Strip the docstrings from the python file {REL}/tree/pkg/b.py and save it to {REL}/b_nodoc.py.", "b_nodoc.py"),
            ("structured.document.semantic_digest.sha256",
             f"Compute the semantic digest of the json document {REL}/doc.json and save it to {REL}/digest.json.", "digest.json"),
        ]
        for cid, goal, artifact in cases:
            with self.subTest(cid=cid):
                res = self._solve(goal, cid.split(".")[0].upper())
                self.assertIs(res["pass"], True, res.get("status"))
                self.assertEqual(res["selected_plan"], [cid])
                self.assertTrue((WORK / artifact).is_file())
        self.assertNotIn('"""', (WORK / "b_nodoc.py").read_text(encoding="utf-8"))
        manifest = json.loads((WORK / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([i["path"] for i in manifest["items"]], ["a.py", "pkg/b.py"])

    def test_two_promoted_capabilities_chain_in_one_goal(self):
        (WORK / "tree").mkdir()
        (WORK / "tree/a.py").write_text("A = 1\n", encoding="utf-8")
        goal = (f"Compute the sha256 manifest of the python source tree {REL}/tree and save it to {REL}/m.json. "
                f"Then compute the semantic digest of the json document {REL}/m.json and save it to {REL}/m_digest.json.")
        res = self._solve(goal, "DAG")
        self.assertIs(res["pass"], True, res.get("status"))
        self.assertEqual(res["selected_plan"], ["python.source_tree.manifest.sha256", "structured.document.semantic_digest.sha256"])
        digest = json.loads((WORK / "m_digest.json").read_text(encoding="utf-8"))
        self.assertEqual(digest["input_path"], REL + "/m.json")

    @unittest.skipUnless(HAS_SYMPY, "SymPy not installed; the capability fails closed without it")
    def test_plain_goal_reaches_exact_symbolic_compute(self):
        (WORK / "cases.json").write_text(json.dumps({"cases": [{"op": "hilbert_det", "p": [3]}, {"op": "binomial_identity", "p": [10]}]}), encoding="utf-8")
        res = self._solve(f"Run the exact symbolic sympy cases in {REL}/cases.json and save the results to {REL}/sym.json.", "SYM")
        self.assertIs(res["pass"], True, res.get("status"))
        self.assertEqual(res["selected_plan"], ["math.exact_symbolic.compute.sympy"])
        results = json.loads((WORK / "sym.json").read_text(encoding="utf-8"))["results"]
        self.assertEqual([r["result_text"] for r in results], ["1/2160", "1024"])

    def test_reinventory_keeps_promoted_entries_and_links(self):
        old = {"capabilities": {
            "promoted.cap": {"status": "VERIFIED_BOUND_CAPABILITY", "verification": {"verified": True}},
            "canonical/x.py.auto.v1": {"status": "UNVERIFIED_INVENTORY", "promoted_to": ["promoted.cap"]},
            "canonical/gone.py.auto.v1": {"status": "UNVERIFIED_INVENTORY"},
        }}
        fresh = {"schema": inventory.SCHEMA, "capabilities": {
            "canonical/x.py.auto.v1": {"status": "UNVERIFIED_INVENTORY"},
            "canonical/new.py.auto.v1": {"status": "UNVERIFIED_INVENTORY"},
        }}
        merged = inventory.merge_preserving_promotions(fresh, old)["capabilities"]
        self.assertEqual(sorted(merged), ["canonical/new.py.auto.v1", "canonical/x.py.auto.v1", "promoted.cap"])
        self.assertEqual(merged["canonical/x.py.auto.v1"]["promoted_to"], ["promoted.cap"])
        self.assertEqual(merged["promoted.cap"], old["capabilities"]["promoted.cap"])


if __name__ == "__main__":
    unittest.main()
