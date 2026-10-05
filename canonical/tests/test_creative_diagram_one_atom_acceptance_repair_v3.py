from __future__ import annotations
import json, shutil, tempfile, unittest
from pathlib import Path
from canonical.runtime.verify_creative_diagram_one_atom_acceptance_repair_v3 import VerificationError, verify

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json",
    "canonical/governance/SYNTHESIS_EXPLICIT_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_20261005_V1.json",
    "canonical/governance/SYNTHESIS_HIDDEN_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_V1.json",
    "canonical/governance/OPUS55_TARGET_COVERAGE_DOMAIN_FACTORIZATION_20261005_V1.json",
    "canonical/governance/OPUS55_FIXED_INTERFACE_THINKING_CHANNEL_COUNTEREXAMPLE_20261005_V1.json",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py",
    "canonical/runtime/svg_diagram_render_oracle_v1.py",
    "canonical/governance/CREATIVE_DIAGRAM_ONE_ATOM_ACCEPTANCE_REPAIR_20261005_V3.json",
]

class RepairV3Tests(unittest.TestCase):
    def clone(self):
        td = tempfile.TemporaryDirectory(); root = Path(td.name)
        for rel in FILES:
            dst=root/rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/rel,dst)
        return td, root

    def test_current_tree_passes(self):
        out=verify(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["family_mutations"], 0)
        self.assertEqual(out["creative_new_atoms"], 0)
        self.assertEqual(out["diagram_new_atoms"], 1)
        self.assertEqual(out["projected_if_integrated"], "19_FAMILIES_39_ATOMS_14_PROVED_25_UNRESOLVED")

    def test_active_cut_pointer_tamper_fails(self):
        td,root=self.clone()
        with td:
            p=root/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json"
            p.write_text(p.read_text()+"\n",encoding="utf-8")
            with self.assertRaisesRegex(VerificationError,"ACTIVE_CUT_POINTER_BLOB_DRIFT"):
                verify(root)

    def test_matched_execution_release_fails(self):
        td,root=self.clone()
        with td:
            p=root/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json"
            d=json.loads(p.read_text())
            for g in d["current_information_positive_action_groups"]:
                if "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in g.get("predicates",[]):
                    g["action"]="MATCHED CASE EXECUTION ALLOWED"
            raw=json.dumps(d,indent=2)+"\n"; p.write_text(raw,encoding="utf-8")
            import hashlib
            sha=hashlib.sha1(b"blob "+str(len(raw.encode())).encode()+b"\0"+raw.encode()).hexdigest()
            pp=root/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
            pd=json.loads(pp.read_text()); pd["active_cut"]["git_blob_sha"]=sha; pp.write_text(json.dumps(pd),encoding="utf-8")
            with self.assertRaises(VerificationError): verify(root)

    def test_target_coverage_coupling_fails(self):
        td,root=self.clone()
        with td:
            p=root/"canonical/governance/OPUS55_TARGET_COVERAGE_DOMAIN_FACTORIZATION_20261005_V1.json"
            d=json.loads(p.read_text()); d["current_state_after_factorization"]["target_coverage_proved"]=True
            p.write_text(json.dumps(d),encoding="utf-8")
            with self.assertRaises(VerificationError): verify(root)

    def test_mechanics_scope_widening_fails(self):
        td,root=self.clone()
        with td:
            p=root/"canonical/runtime/html_svg_diagram_mechanics_v1.py"
            p.write_text(p.read_text().replace("Content selection, layout quality, and presentation quality are explicitly outside scope.","All quality covered."),encoding="utf-8")
            with self.assertRaises(VerificationError): verify(root)

    def test_credit_leak_fails(self):
        td,root=self.clone()
        with td:
            p=root/"canonical/governance/CREATIVE_DIAGRAM_ONE_ATOM_ACCEPTANCE_REPAIR_20261005_V3.json"
            d=json.loads(p.read_text()); d["accounting"]["acceptance_credit_delta"]=1
            p.write_text(json.dumps(d),encoding="utf-8")
            with self.assertRaisesRegex(VerificationError,"CANDIDATE_ACCOUNTING_NONZERO"): verify(root)

if __name__=="__main__":
    unittest.main()
