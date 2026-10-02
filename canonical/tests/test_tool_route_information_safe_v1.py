import inspect
import unittest

import canonical.runtime.tool_route_information_safe_candidate_v1 as candidate
from canonical.runtime.tool_route_information_safe_proof_v1 import (
    generate_case, public_task, run_candidate,
)


class ToolRouteInformationSafeTests(unittest.TestCase):
    def test_candidate_has_no_oracle_import(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("tool_route_information_safe_proof_v1",src)
        self.assertNotIn("_oracle",src)

    def test_public_payload_hides_capabilities(self):
        public=public_task(generate_case(11))
        self.assertNotIn("_oracle",public)
        for row in public["public"]["tools"]:
            self.assertNotIn("capable",row)
            self.assertNotIn("capabilities",row)

    def test_hidden_capability_discovery_and_least_cost_selection(self):
        for seed in range(11,41):
            case=generate_case(seed)
            out=run_candidate(case,candidate)
            self.assertTrue(out["pass"],(seed,out,case["_oracle"]))
            self.assertEqual(out["records"][1]["probe_count"],0)

    def test_catalog_change_invalidates_stale_capability_memory(self):
        for seed in (51,52,53,54):
            case=generate_case(seed,change_epoch=True)
            out=run_candidate(case,candidate)
            self.assertTrue(out["pass"],(seed,out,case["_oracle"]))
            self.assertGreater(out["records"][1]["probe_count"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
