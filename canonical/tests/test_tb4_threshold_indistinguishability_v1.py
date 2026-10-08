from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import tb4_threshold_indistinguishability_v1 as cut


class TB4ThresholdIndistinguishabilityV1Tests(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj):
        p=root/rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")

    def _fixture(self, root: Path, *, k=1, t=219, c=220):
        self._write(root,cut.FRONTIER_PATH,{
            "predicate":"CODING_TB4_GE_66_4",
            "current_empirical_route":{
                "current_certified_success_slots":k,
                "required_success_slots":t,
                "current_creditable_slot_capacity":c,
                "capacity_is_not_observed_success":True,
            },
            "stronger_proof_frontier":{
                "remaining_load_bearing_premises":[
                    "AT_LEAST_218_ADDITIONAL_DISTINCT_CERTIFIED_SUCCESS_SLOTS_OR_STRONGER_CERTIFICATE"
                ]
            },
        })
        self._write(root,cut.EVIDENCE_SCAN_PATH,{
            "arithmetic":{
                "existing_certified_success_slots":k,
                "required_success_slots":t,
            },
            "conclusion":{"existing_internal_evidence_shortcut_exhausted":True},
        })
        self._write(root,cut.PARAMETRICITY_PATH,{
            "falsified_shortcut":{"verdict":"NOT_ENTAILED_BY_THE_FROZEN_HARNESS"},
            "legal_reuse":{"forbidden":["MULTIPLY_ONE_EMPIRICAL_SUCCESS_RECEIPT_BY_FIVE"]},
        })

    def test_constructs_pass_and_fail_worlds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self._fixture(root)
            out=cut.certify(repo_root=root)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["information_theoretic_indistinguishability_proved"])
        self.assertFalse(out["fail_world"]["threshold_met"])
        self.assertTrue(out["pass_world"]["threshold_met"])
        self.assertEqual(out["minimum_additional_successes_for_pass_world"],218)

    def test_fails_if_threshold_already_met(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self._fixture(root,k=219,t=219,c=220)
            out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])

    def test_fails_if_capacity_cannot_reach_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self._fixture(root,k=1,t=219,c=200)
            out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])

    def test_fails_without_exhausted_existing_evidence_search(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self._fixture(root)
            p=root/cut.EVIDENCE_SCAN_PATH
            o=json.loads(p.read_text())
            o["conclusion"]["existing_internal_evidence_shortcut_exhausted"]=False
            p.write_text(json.dumps(o))
            out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
