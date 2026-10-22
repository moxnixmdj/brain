from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate

def protocols():
    return {"protocols":[
        {"family":"OWNED","proof_mode":"THEORETICAL_CEILING","status":"PASS"},
        {"family":"MATCHED","proof_mode":"MATCHED_DIRECT_NONINFERIORITY","status":"DEFINED_RESULT_OPEN"},
        {"family":"PUBLIC","proof_mode":"PUBLIC_FIXED_BAR","status":"DEFINED_RESULT_OPEN"},
        {"family":"MIXED","proof_mode":"PUBLIC_FIXED_BAR_PLUS_SCOPE_AUDIT","status":"DEFINED_RESULT_OPEN"},
    ]}

def ev(**kw):
    x={"id":"E1","family":"MATCHED","mode":"UNIVERSAL","verified":True,"independent":True,
       "contamination_clean":True,"binds_frozen_protocol":True,"scope_relation":"EXACT",
       "closes_entire_protocol":True,
       "result":{"all_admissible_inputs_proved":True,"formal_completeness":True}}
    x.update(kw); return x

class Tests(unittest.TestCase):
    def row(self,out,name): return next(r for r in out["families"] if r["family"]==name)

    def test_owned_preserved(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[]}),"OWNED")["result_status"],"PASS")

    def test_universal_closes(self):
        r=self.row(evaluate(protocols(),{"evidence":[ev()]}),"MATCHED")
        self.assertEqual((r["result_status"],r["closure_mode"]),("PASS","UNIVERSAL"))

    def test_behavioral_never_closes(self):
        e=ev(mode="BEHAVIORAL_ONLY",result={"all_admissible_inputs_proved":True,"formal_completeness":True})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_partial_scope_never_closes(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[ev(scope_relation="PARTIAL")]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_unverified_never_closes(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[ev(verified=False)]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def scope(self):
        return {"verified":True,"independent":True,"basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
                "all_admissible_target_inputs_proved":True,"formal_completeness":True,
                "receipt":"canonical/verification/test_scope_complete.json"}

    def test_absolute_ceiling(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",scope_completeness=self.scope(),
             result={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0})
        r=self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")
        self.assertEqual((r["result_status"],r["witness_reason"]),("PASS","THEORETICAL_CEILING_DOMINANCE"))

    def test_bound_squeeze(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",scope_completeness=self.scope(),
             result={"direction":"higher","brain_lower_bound":0.94,"target_upper_bound":0.91})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"PASS")

    def test_lower_floor(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",scope_completeness=self.scope(),
             result={"direction":"lower","brain_upper_bound":0.0,"theoretical_lower_bound":0.0})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"PASS")

    def test_finite_perfect_sample_without_scope_completeness_does_not_close(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",
             result={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0})
        r=self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")
        self.assertEqual(r["result_status"],"DEFINED_RESULT_OPEN")
        self.assertIn("ABSOLUTE_SCOPE_COMPLETENESS_MISSING",
                      r["rejections"][0]["reasons"])

    def test_unverified_scope_completeness_does_not_close(self):
        s=self.scope(); s["verified"]=False
        e=ev(mode="ABSOLUTE_DOMINANCE",scope_completeness=s,
             result={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],
                         "DEFINED_RESULT_OPEN")

    def test_partial_public_bar_does_not_close_composite(self):
        e=ev(id="M",family="MIXED",mode="PUBLIC_FIXED_BAR",closes_entire_protocol=False,result={"threshold_pass":True})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MIXED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_bad_evidence_shape_fails_closed(self):
        self.assertEqual(evaluate(protocols(),{"evidence":"bad"})["status"],"FAIL_CLOSED")

    def test_live_repo_grants_no_closure_of_its_own(self):
        """The transmuter must never close a family on its own authority.

        This used to pin the literal tuple ``(19, 2, 17)``. That constant was
        wrong on two counts. It measured the wrong thing -- it counted families
        that arrived in the tracked protocol file *already* marked ``PASS`` as
        though the transmuter had closed them -- and it went stale the moment
        that file legitimately recorded more passing families, which is exactly
        what happened: the file records four ``PASS`` protocols, so the honest
        count is ``(19, 4, 15)``.

        The property that actually has to hold is independent of how many
        families have passed so far: closed == already-passing, every closure is
        labelled as such, and no witness is silently swallowed -- one either
        closes its family or is rejected with a named reason. Asserting that
        keeps the guard live without going red every time the repo improves.
        """
        root=Path(__file__).resolve().parents[2]
        pp_path=root/"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
        ep_path=root/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
        if not pp_path.exists() or not ep_path.exists(): self.skipTest("integration fixtures absent")
        pp=json.loads(pp_path.read_text()); ep=json.loads(ep_path.read_text())
        out=evaluate(pp,ep)

        already_pass={p["family"] for p in pp["protocols"] if p.get("status")=="PASS"}
        closed_rows=[r for r in out["families"] if r["result_status"]=="PASS"]
        closed={r["family"] for r in closed_rows}

        # the transmuter grants no closure of its own authority
        self.assertEqual(closed,already_pass)
        self.assertEqual(out["closed_family_count"],len(already_pass))
        self.assertEqual(out["open_family_count"],out["family_count"]-len(already_pass))
        self.assertEqual(out["family_count"],len(out["families"]))
        # and it never disguises where a closure came from
        self.assertTrue(all(r["closure_mode"]=="ALREADY_PASS" for r in closed_rows))

        # the guard has teeth: a witness either closes its family or is rejected
        # with a reason. One that is neither honoured nor rejected means the
        # transmuter is swallowing evidence it was told to evaluate.
        for e in ep.get("evidence") or []:
            fam=e.get("family")
            row=next((r for r in out["families"] if r["family"]==fam),None)
            self.assertIsNotNone(row,f"evidence {e.get('id')} names unknown family {fam}")
            if row["result_status"]!="PASS":
                self.assertTrue(
                    row["rejections"],
                    f"witness for {fam} neither closed the family nor was rejected with a reason",
                )

if __name__=="__main__":
    unittest.main(verbosity=2)
