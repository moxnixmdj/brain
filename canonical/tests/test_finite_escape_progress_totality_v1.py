import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.finite_escape_progress_totality_v1 as totality


class FiniteEscapeProgressTotalityV1Tests(unittest.TestCase):
    def setUp(self):
        self.old_root=totality.ROOT
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        totality.ROOT=self.root
        (self.root/"canonical/governance").mkdir(parents=True)
        (self.root/"canonical/verification").mkdir(parents=True)

    def tearDown(self):
        totality.ROOT=self.old_root
        self.tmp.cleanup()

    def bind(self,pid,condition):
        g=self.root/"canonical/governance"/f"{pid}.json"
        v=self.root/"canonical/verification"/f"{pid}.json"
        g.write_text(json.dumps({
            "schema":totality.ADEQUACY_SCHEMA,"policy_id":pid,
            "policy_condition_sha256":totality._condition_sha256(condition),
            "adequacy_proved":True,"brain_owned":True,
            "load_bearing_constraints_preserved":True},sort_keys=True))
        gb=totality._git_blob_sha(g)
        v.write_text(json.dumps({
            "schema":totality.VERIFY_SCHEMA,"policy_id":pid,
            "subject_git_blob_sha":gb,"pass":True},sort_keys=True))
        return {
            "adequacy_certificate_path":f"canonical/governance/{pid}.json",
            "adequacy_certificate_blob_sha":gb,
            "independent_verification_path":f"canonical/verification/{pid}.json",
            "independent_verification_blob_sha":totality._git_blob_sha(v)}

    def test_one_bit_partition_closes_structurally(self):
        x={"op":"ATOM","id":"x"}; nx={"op":"NOT","arg":x}
        out=totality.solve({
            "decision_basis":["x"],
            "policy_conditions":{"pt":x,"pf":nx},
            "policy_adequacy_bindings":{"pt":self.bind("pt",x),"pf":self.bind("pf",nx)},
            "discriminators":[{"discriminator_id":"observe_x","formula":x,"cost_units":1}]})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS__FINITE_ESCAPE_PROGRESS_TOTALITY_STRUCTURALLY_CLOSED")
        self.assertEqual(out["root_model_count"],2)
        self.assertEqual(out["unsplittable_leaves"],[])
        self.assertTrue(out["all_refinement_edges_strictly_decrease_rank"])
        self.assertFalse(out["progress_authority"])

    def test_two_policy_cover_hole_isolated_to_singleton_00(self):
        x={"op":"ATOM","id":"x"}; y={"op":"ATOM","id":"y"}
        out=totality.solve({
            "decision_basis":["x","y"],
            "policy_conditions":{"px":x,"py":y},
            "policy_adequacy_bindings":{"px":self.bind("px",x),"py":self.bind("py",y)},
            "discriminators":[
                {"discriminator_id":"observe_x","formula":x,"cost_units":1},
                {"discriminator_id":"observe_y","formula":y,"cost_units":1}]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__UNSPLITTABLE_POLICY_COVER_OBSTRUCTION")
        self.assertEqual(out["unsplittable_leaves"],[
            {"model_count":1,"models":[{"model_id":"00","valuation":{"x":False,"y":False}}]}])
        self.assertTrue(out["all_refinement_edges_strictly_decrease_rank"])

    def test_true_policy_terminalizes_top_without_refinement(self):
        t={"op":"TRUE"}
        out=totality.solve({
            "decision_basis":["x","y"],
            "policy_conditions":{"p":t},
            "policy_adequacy_bindings":{"p":self.bind("p",t)},
            "discriminators":[]})
        self.assertTrue(out["pass"])
        self.assertEqual(out["tree"]["kind"],"TERMINAL_POLICY")
        self.assertEqual(out["tree"]["selected_policy_id"],"p")

    def test_missing_authentication_fails_closed(self):
        x={"op":"ATOM","id":"x"}
        out=totality.solve({"decision_basis":["x"],"policy_conditions":{"p":x},"discriminators":[]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"NO_AUTHENTICATED_POLICY_ADEQUACY")

    def test_non_splitting_discriminator_cannot_fake_progress(self):
        x={"op":"ATOM","id":"x"}
        out=totality.solve({
            "decision_basis":["x"],
            "formal_source_constraints":[x],
            "policy_conditions":{"p":{"op":"FALSE"}},
            "policy_adequacy_bindings":{"p":self.bind("p",{"op":"FALSE"})},
            "discriminators":[{"discriminator_id":"observe_x","formula":x,"cost_units":0}]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__UNSPLITTABLE_POLICY_COVER_OBSTRUCTION")
        self.assertEqual(out["unsplittable_leaves"][0]["model_count"],1)


if __name__=="__main__":
    unittest.main()
