import hashlib
import unittest
from pathlib import Path

from canonical.runtime import saccr_route_specific_terminal_executor_v1 as ex


class SaccrRouteSpecificTerminalExecutorTests(unittest.TestCase):
    def test_static_preflight_matches_frozen_binding(self):
        out = ex.static_preflight(Path("."))
        self.assertTrue(out["pass"], out)

    def test_case_id_and_seed_match_frozen_v2_rule(self):
        cid = ex.case_id(17)
        self.assertEqual(
            cid,
            "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001::SA_CCR_TERMINAL_POPULATION_V1::slot::17",
        )
        raw = (
            b"PROJECT_BRAIN_TERMINAL_V2\0"
            + b"commitment"
            + b"\0"
            + b"beacon"
            + b"\0"
            + cid.encode()
        )
        expected = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        self.assertEqual(ex.derive_seed("commitment", "beacon", cid), expected)

    def test_nonterminal_self_check_passes(self):
        out = ex.dev_self_check()
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["case_count"], 32)
        self.assertTrue(out["all_pass"], out["failures"])

    def test_terminal_count_is_exact_and_index_is_bounded(self):
        self.assertEqual(ex.SAMPLE_COUNT, 2000)
        self.assertTrue(ex.case_id(0).endswith("::slot::0"))
        self.assertTrue(ex.case_id(1999).endswith("::slot::1999"))
        with self.assertRaises(ValueError):
            ex.case_id(2000)


if __name__ == "__main__":
    unittest.main()
