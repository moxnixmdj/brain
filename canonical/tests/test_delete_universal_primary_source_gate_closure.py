#!/usr/bin/env python3
from __future__ import annotations
import pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"

class DeleteUniversalPrimaryGateClosure(unittest.TestCase):
    def test_frontend_preserves_primary_as_optional_metadata(self):
        s=FRONT.read_text()
        self.assertIn('"primary_source_gate_required":False',s)
        self.assertIn("MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_V1",s)
        self.assertNotIn(
            '"next_required_capability":("MODEL_INDEPENDENT_PRIMARY_SOURCE',
            s,
        )

    def test_astra_identity_ready_path_requires_relevance_not_primary(self):
        s=ASTRA.read_text()
        marker="OPEN_ENDED_RESEARCH_SOURCE_IDENTITY_READY__"
        i=s.index(marker)
        window=s[i:i+700]
        self.assertIn("OBJECTIVE_RELEVANCE_VERIFICATION_REQUIRED",window)
        self.assertNotIn("PRIMARY_SOURCE_RELEVANCE_VERIFICATION_REQUIRED",window)

    def test_package_acquisition_remains_after_fail_closed_source_frontier(self):
        s=ASTRA.read_text()
        i=s.index("OPEN_ENDED_RESEARCH_SOURCE_IDENTITY_READY__")
        j=s.index("_load_auto_capability_acquisition()",i)
        self.assertLess(i,j)
        window=s[i-2400:j]
        self.assertIn('"capability_acquisition_attempted":False',window)

if __name__=="__main__": unittest.main(verbosity=2)
