from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime.terminal_route_execution_plan_validator import validate


PLAN="canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json"


class TerminalRouteExecutionPlanValidatorTests(unittest.TestCase):
    def live(self):
        root=Path(__file__).resolve().parents[2]
        plan=json.loads((root/PLAN).read_text(encoding="utf-8"))
        return root,plan

    def test_live_plan_passes_without_generating_cases(self):
        root,plan=self.live()
        with mock.patch("canonical.runtime.cad_t0_geometry_population.generate_post_freeze",side_effect=AssertionError("terminal generator called"),create=True):
            out=validate(root,plan)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["validated_contract_count"],12)
        self.assertEqual(out["direct_population_count"],6)
        self.assertEqual(out["multiplex_instrumentation_count"],6)
        self.assertFalse(out["terminal_case_generation_performed"])
        self.assertFalse(out["launch_authority"])

    def test_global_sample_shortcut_is_rejected(self):
        root,plan=self.live()
        bad=copy.deepcopy(plan)
        bad["multiplex_instrumentation"][0]["sample_count"]=12
        out=validate(root,bad)
        self.assertFalse(out["pass"])
        self.assertIn("MULTIPLEX_STANDALONE_SAMPLE_COUNT_FORBIDDEN:SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",out["errors"])

    def test_direct_sample_count_change_is_rejected(self):
        root,plan=self.live()
        bad=copy.deepcopy(plan)
        bad["direct_populations"][0]["sample_count"]=12
        out=validate(root,bad)
        self.assertFalse(out["pass"])
        self.assertIn("DIRECT_SAMPLE_COUNT_MISMATCH:CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",out["errors"])

    def test_duplicate_behavior_is_rejected(self):
        root,plan=self.live()
        bad=copy.deepcopy(plan)
        bad["multiplex_instrumentation"][0]["behavior_id"]=bad["direct_populations"][0]["behavior_id"]
        out=validate(root,bad)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("DUPLICATE_BEHAVIOR:") for x in out["errors"]))

    def test_blob_change_is_rejected(self):
        root,plan=self.live()
        bad=copy.deepcopy(plan)
        bad["direct_populations"][0]["generator"]["blob_sha"]="0"*40
        out=validate(root,bad)
        self.assertFalse(out["pass"])
        self.assertIn("BINDING_BLOB_MISMATCH:CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001:generator",out["errors"])

    def test_plan_cannot_self_authorize(self):
        root,plan=self.live()
        bad=copy.deepcopy(plan)
        bad["launch_authority"]=True
        out=validate(root,bad)
        self.assertFalse(out["pass"])
        self.assertIn("PLAN_MUST_NOT_SELF_AUTHORIZE_LAUNCH",out["errors"])


if __name__=="__main__":
    unittest.main(verbosity=2)
