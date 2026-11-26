"""A discovered surface must be reachable, executable, and never admitted by accident.

The failure this guards against is not "the census is wrong" -- it is "the census
is right and nothing acts on it".  Each assertion below is an oracle for one way
that can happen: the surface set is empty, the model cannot see it, the runtime
cannot resolve it, execution produces no evidence, or execution quietly promotes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import harvested_capability_runtime_v1 as runtime  # noqa: E402

MODEL = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


class HarvestedSurfaceIsReachable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = runtime.surfaces(ROOT)

    def test_the_tree_carries_executable_surfaces_no_registry_declares(self):
        self.assertGreater(len(self.rows), 400, f"only {len(self.rows)} hidden surfaces")
        kinds = {row["kind"] for row in self.rows}
        self.assertEqual(kinds, {"contract", "cli"})
        self.assertTrue(all(row["entrypoint"] for row in self.rows))

    def test_the_artefact_lists_them_and_claims_nothing_about_them(self):
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        harvested = model["harvested_capabilities"]
        self.assertEqual(len(harvested), int(model["counts"]["harvested_capabilities"]))
        self.assertTrue(all(row["admitted"] is False for row in harvested))
        self.assertTrue(all(row["capability"] is False for row in harvested))
        self.assertTrue(all(row["admission_state"] == "DISCOVERED_NOT_ADMITTED"
                            for row in harvested))
        self.assertTrue(all(row["triggers"] for row in harvested))
        self.assertEqual(int(model["counts"]["harvested_admitted"]), 0)

    def test_the_artefact_rows_are_disjoint_from_admitted_capability(self):
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        admitted_ids = {row["id"] for row in model["capabilities"]}
        admitted_paths = {
            row["provenance"].get(key)
            for row in model["capabilities"]
            for key in ("source_path", "adapter_path")
            if row["provenance"].get(key)
        }
        for row in model["harvested_capabilities"]:
            self.assertNotIn(row["id"], admitted_ids)
            self.assertNotIn(row["path"], admitted_paths)

    def test_the_runtime_resolves_one_by_id_and_refuses_a_fabricated_one(self):
        row = next(r for r in self.rows if r["path"].endswith("jq_query.py"))
        self.assertEqual(runtime.describe(row["id"], ROOT)["path"], row["path"])
        refused = runtime.run({"capability_id": "no.such.surface.hidden.v1"}, ROOT)
        self.assertEqual(refused["status"], "REFUSED")
        self.assertEqual(refused["refusal"], "HARVESTED_SURFACE_UNKNOWN_OR_ALREADY_DECLARED")

    def test_execution_returns_a_result_and_issues_evidence_without_promoting(self):
        row = next(r for r in self.rows if r["path"].endswith("jq_query.py"))
        workdir = Path(tempfile.mkdtemp(prefix="HARVEST_JQ_", dir=ROOT / "canonical/astra_runtime/tmp"))
        source = workdir / "in.json"
        source.write_text('{"repos":[{"name":"a","stars":3},{"name":"b","stars":9}]}\n', encoding="utf-8")
        out = runtime.run({
            "capability_id": row["id"],
            "args": {
                "input_path": source.relative_to(ROOT).as_posix(),
                "filter": ".repos | map(select(.stars > 5)) | .[0].name",
                "output_path": (workdir / "out.json").relative_to(ROOT).as_posix(),
            },
        }, ROOT)
        self.assertEqual(out["status"], "EXECUTED", out.get("refusal"))
        self.assertTrue(out["executed"])
        self.assertEqual(out["observed"].get("output_verified"), True)
        self.assertEqual((workdir / "out.json").read_text(encoding="utf-8").strip(), "b")
        # Execution is evidence, not promotion.
        self.assertFalse(out["admitted"])
        self.assertEqual(out["admission"], "NOT_ADMITTED")
        self.assertEqual(out["model_calls"], 0)
        receipt = ROOT / out["receipt_path"]
        self.assertTrue(receipt.is_file())
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1")
        self.assertIsNone(payload["independent_verifier"])
        self.assertEqual(int(payload["model_dependency_count"]), 0)
        self.assertEqual(payload["module_sha256"], row["sha256"])

    def test_a_surface_that_needs_inputs_refuses_instead_of_inventing_them(self):
        row = next(r for r in self.rows
                   if r["path"].endswith("python_test_corpus_discovery_v1.py"))
        out = runtime.run({"capability_id": row["id"], "args": {}}, ROOT)
        self.assertIn(out["status"], {"EXECUTED", "REFUSED"})
        if out["status"] == "REFUSED":
            self.assertEqual(out["refusal"],
                             "HARVESTED_SURFACE_DID_NOT_RUN__NO_STRUCTURED_RESULT")
            self.assertFalse(out["executed"])

    def test_the_cli_lists_the_surface_without_importing_the_runtime(self):
        proc = subprocess.run(
            [sys.executable, "canonical/runtime/harvested_capability_runtime_v1.py", "--list"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        payload = json.loads(proc.stdout)
        self.assertGreater(payload["count"], 400)


if __name__ == "__main__":
    unittest.main()
