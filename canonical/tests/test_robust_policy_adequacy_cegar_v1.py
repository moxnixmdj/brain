import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.robust_policy_adequacy_cegar_v1 as kernel


class RobustPolicyAdequacyCegarV1Tests(unittest.TestCase):
    def setUp(self):
        self.old_root=kernel.ROOT
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        kernel.ROOT=self.root
        (self.root/"canonical/governance").mkdir(parents=True)
        (self.root/"canonical/verification").mkdir(parents=True)

    def tearDown(self):
        kernel.ROOT=self.old_root
        self.tmp.cleanup()

    def bind(self,pid,condition):
        g=self.root/"canonical/governance"/f"{pid}.json"
        v=self.root/"canonical/verification"/f"{pid}.json"
        g.write_text(json.dumps({
            "schema":kernel.ADEQUACY_SCHEMA,"policy_id":pid,
            "policy_condition_sha256":kernel._condition_sha256(condition),
            "adequacy_proved":True,"brain_owned":True,
            "load_bearing_constraints_preserved":True},sort_keys=True))
        gb=kernel._git_blob_sha(g)
        v.write_text(json.dumps({
            "schema":kernel.VERIFY_SCHEMA,"policy_id":pid,
            "subject_git_blob_sha":gb,"pass":True},sort_keys=True))
        return {
            "adequacy_certificate_path":f"canonical/governance/{pid}.json",
            "adequacy_certificate_blob_sha":gb,
            "independent_verification_path":f"canonical/verification/{pid}.json",
            "independent_verification_blob_sha":kernel._git_blob_sha(v)}

    def test_common_policy_first(self):
        x={"op":"ATOM","id":"x"}
        out=kernel.solve({
            "decision_basis":["x"],
            "formal_source_constraints":[x],
            "proposed_refinements":[x],
            "policy_conditions":{"p":x},
            "policy_adequacy_bindings":{"p":self.bind("p",x)}})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS")
        self.assertEqual(out["selected_policy_id"],"p")

    def test_policy_cover_hole_returns_exact_uncovered_model(self):
        x={"op":"ATOM","id":"x"}; y={"op":"ATOM","id":"y"}
        out=kernel.solve({
            "decision_basis":["x","y"],
            "policy_conditions":{"px":x,"py":y},
            "policy_adequacy_bindings":{"px":self.bind("px",x),"py":self.bind("py",y)},
            "discriminators":[
                {"discriminator_id":"observe_x","formula":x,"cost_units":1},
                {"discriminator_id":"observe_y","formula":y,"cost_units":1}]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"AUTHENTICATED_POLICY_COVER_INCOMPLETE")
        self.assertEqual(out["detail"]["uncovered_models"],[
            {"model_id":"00","valuation":{"x":False,"y":False}}])

    def test_minimum_discriminator_only_when_every_model_has_policy(self):
        x={"op":"ATOM","id":"x"}; nx={"op":"NOT","arg":x}
        out=kernel.solve({
            "decision_basis":["x"],
            "policy_conditions":{"pt":x,"pf":nx},
            "policy_adequacy_bindings":{"pt":self.bind("pt",x),"pf":self.bind("pf",nx)},
            "discriminators":[{"discriminator_id":"observe_x","formula":x,"cost_units":1}]})
        self.assertEqual(out["status"],"UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED")
        self.assertEqual(out["selected_discriminator"]["discriminator_id"],"observe_x")

    def test_missing_authentication_fails_closed(self):
        x={"op":"ATOM","id":"x"}
        out=kernel.solve({"decision_basis":["x"],"policy_conditions":{"p":x}})
        self.assertEqual(out["reason"],"NO_AUTHENTICATED_POLICY_ADEQUACY")

    def test_unproved_refinement_does_not_shrink_top(self):
        x={"op":"ATOM","id":"x"}; nx={"op":"NOT","arg":x}
        out=kernel.solve({
            "decision_basis":["x"],
            "formal_source_constraints":[],
            "proposed_refinements":[x],
            "policy_conditions":{"pt":x,"pf":nx},
            "policy_adequacy_bindings":{"pt":self.bind("pt",x),"pf":self.bind("pf",nx)},
            "discriminators":[{"discriminator_id":"observe_x","formula":x,"cost_units":1}]})
        self.assertEqual(out["surviving_model_count"],2)
        self.assertEqual(len(out["semantic_state"]["rejected_refinements"]),1)


if __name__=="__main__":
    unittest.main()
