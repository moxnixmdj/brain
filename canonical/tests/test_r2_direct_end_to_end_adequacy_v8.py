from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime import r2_direct_end_to_end_adequacy_v7 as v7
from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as v8
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed


ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "governance" / "H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"


def _goal():
    return (
        "Using the OEWN-bound typed finance UNLESS case at "
        "canonical/tmp/oewn_case.json, select and independently verify the "
        "applicable branch and save it to canonical/tmp/oewn_out.json."
    )


class R2DirectEndToEndAdequacyV8Tests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        ctx = {
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {"result": {"type": "BOOL", "value": True}},
        }
        case = {
            "schema": "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_CASE_V1",
            "source_id": "router-oewn",
            "source_text": (
                "The policy concerns a consequence effect outcome from a previous event. "
                "Apply Rule A unless upshot is true."
            ),
            "target_field": "result",
            "typed_context": ctx,
            "typed_context_sha256": typed_context_sha256(ctx),
            "knowledge_path": "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json",
        }
        p = self.root / "canonical/tmp/oewn_case.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(case), encoding="utf-8")
        kp = self.root / case["knowledge_path"]
        kp.parent.mkdir(parents=True, exist_ok=True)
        kp.write_bytes(PINNED.read_bytes())

    def tearDown(self):
        self.td.cleanup()

    def test_route_inventory_is_v7_plus_exactly_one(self):
        self.assertEqual(
            set(v8.ROUTES),
            set(v7.ROUTES) | {v8.FINANCE_OEWN_SYNONYM_ROUTE_ID},
        )
        self.assertEqual(len(v8.ROUTES), len(v7.ROUTES) + 1)

    def test_matching_request_uses_new_route(self):
        req = {"task_id": "v8-match", "goal": _goal()}
        pf = v8.preflight(req, repo_root=self.root)
        self.assertTrue(pf["matched"], pf)
        self.assertEqual(pf["route_id"], v8.FINANCE_OEWN_SYNONYM_ROUTE_ID)
        out = v8.run(req, repo_root=self.root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route_id"], v8.FINANCE_OEWN_SYNONYM_ROUTE_ID)

    def test_nonmatching_preflight_delegates_exactly_to_v7(self):
        req = {"task_id": "v8-no", "goal": "Explain this unrelated request."}
        self.assertEqual(
            v8.preflight(req, repo_root=self.root),
            v7.preflight(req, repo_root=self.root),
        )

    def test_nonmatching_run_delegates_exactly_to_v7(self):
        req = {"task_id": "v8-no-run", "goal": "Explain this unrelated request."}
        self.assertEqual(
            v8.run(req, repo_root=self.root),
            v7.run(req, repo_root=self.root),
        )

    def test_fixed_point_uses_v8_router(self):
        self.assertIs(fixed.direct_adequacy, v8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
