import copy
import unittest

from execution_guard.terminal_progress_enforcement import (
    POINTER_PATH,
    ROOT_STATE_PATH,
    TOURNAMENT_PATH,
    CONTROL_LOOP_PATH,
    TerminalProgressEnforcementError,
    compile_canonical_state,
    evaluate_postchange,
)
from canonical.runtime import terminal_progress_delta_gate_v1 as gate

A40="a"*40
B40="b"*40

ATOMIC=[
    "A_ROOT2_ONLY","B_ROOT3_ONLY","C_MIXED"
]
META=[
    "CYBERSECURITY","LONG_CONTEXT","CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"
]

def docs():
    pointer={
        "exact_state":{
            "unresolved_atomic":3,
            "meta_envelope_open_count":3,
            "total_open_truth_obligations":6,
        },
        "current_shared_causal_interfaces":["I1","I2"],
        "meta_dormant_wake_only":["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"],
    }
    root={
        "current_residual_root_partition":{
            "unresolved_total":3,
            "root1_only":[],
            "root2_only":["A_ROOT2_ONLY"],
            "root3_only":["B_ROOT3_ONLY"],
            "root2_and_root3":["C_MIXED"],
        }
    }
    tournament={
        "proposals":[{
            "interface":"BEHAVIORAL_QUOTIENT_AND_TRANSFER",
            "target_obligations":["CYBERSECURITY","LONG_CONTEXT"],
        }]
    }
    loop={
        "claims":[
            {"id":"C0","status":"PROVED","depends_on":[]},
            {"id":"C1","status":"ACTIVE","depends_on":["C0"]},
            {"id":"C2","status":"ACTIVE","depends_on":["C1"]},
        ]
    }
    return {
        POINTER_PATH:pointer,
        ROOT_STATE_PATH:root,
        TOURNAMENT_PATH:tournament,
        CONTROL_LOOP_PATH:loop,
    }

def bound_receipt(before,after,targets,effect,path="canonical/verification/receipt.json",blob=A40):
    target_sha=gate.sha256_json(sorted(targets))
    doc={
        "before_state_sha256":before["state_sha256"],
        "after_state_sha256":after["state_sha256"],
        "target_truth_obligations_sha256":target_sha,
        "effect_kind":effect,
    }
    row={"path":path,"git_blob_sha":blob,**doc}
    return row,doc

class Tests(unittest.TestCase):
    def test_compile_state_is_canonical_and_exact(self):
        s=compile_canonical_state(
            pointer=docs()[POINTER_PATH],
            root_state=docs()[ROOT_STATE_PATH],
            tournament=docs()[TOURNAMENT_PATH],
            control_loop=docs()[CONTROL_LOOP_PATH],
        )
        self.assertEqual(s["open_truth_obligations"],sorted(ATOMIC+META))
        self.assertEqual(s["active_causal_interfaces"],["I1","I2"])
        self.assertEqual(s["open_prerequisites"],["C1"])
        self.assertEqual(s["max_open_causal_depth"],2)
        self.assertEqual(s["open_proof_node_count"],2)

    def test_atomic_count_mismatch_fails_closed(self):
        d=docs(); d[POINTER_PATH]["exact_state"]["unresolved_atomic"]=4
        with self.assertRaisesRegex(TerminalProgressEnforcementError,"ATOMIC_OPEN_COUNT_MISMATCH"):
            compile_canonical_state(
                pointer=d[POINTER_PATH],root_state=d[ROOT_STATE_PATH],
                tournament=d[TOURNAMENT_PATH],control_loop=d[CONTROL_LOOP_PATH],
            )

    def test_meta_count_mismatch_fails_closed(self):
        d=docs(); d[POINTER_PATH]["exact_state"]["meta_envelope_open_count"]=4
        with self.assertRaisesRegex(TerminalProgressEnforcementError,"META_OPEN_COUNT_MISMATCH"):
            compile_canonical_state(
                pointer=d[POINTER_PATH],root_state=d[ROOT_STATE_PATH],
                tournament=d[TOURNAMENT_PATH],control_loop=d[CONTROL_LOOP_PATH],
            )

    def test_progress_uses_derived_states_not_branch_supplied_numbers(self):
        before_docs=docs()
        after_docs=copy.deepcopy(before_docs)
        after_docs[CONTROL_LOOP_PATH]["claims"][2]["status"]="PROVED"
        before=compile_canonical_state(
            pointer=before_docs[POINTER_PATH],root_state=before_docs[ROOT_STATE_PATH],
            tournament=before_docs[TOURNAMENT_PATH],control_loop=before_docs[CONTROL_LOOP_PATH],
        )
        after=compile_canonical_state(
            pointer=after_docs[POINTER_PATH],root_state=after_docs[ROOT_STATE_PATH],
            tournament=after_docs[TOURNAMENT_PATH],control_loop=after_docs[CONTROL_LOOP_PATH],
        )
        targets=["C_MIXED"]
        row,receipt_doc=bound_receipt(before,after,targets,"DEPTH_CONTRACTION")
        def resolver(path):
            self.assertEqual(path,row["path"])
            return receipt_doc,A40
        out=evaluate_postchange(
            work_class="PROGRESS_CANDIDATE",
            target_truth_obligations=targets,
            before_documents=before_docs,
            after_documents=after_docs,
            evidence_record={"evidence_receipts":[row]},
            resolve_receipt=resolver,
        )
        self.assertEqual(out["gate_result"]["status"],"ADMIT_TERMINAL_CONTRACTING_PROGRESS")

    def test_unrelated_receipt_blob_fails_closed(self):
        before_docs=docs(); after_docs=copy.deepcopy(before_docs)
        after_docs[CONTROL_LOOP_PATH]["claims"][2]["status"]="PROVED"
        before=compile_canonical_state(
            pointer=before_docs[POINTER_PATH],root_state=before_docs[ROOT_STATE_PATH],
            tournament=before_docs[TOURNAMENT_PATH],control_loop=before_docs[CONTROL_LOOP_PATH],
        )
        after=compile_canonical_state(
            pointer=after_docs[POINTER_PATH],root_state=after_docs[ROOT_STATE_PATH],
            tournament=after_docs[TOURNAMENT_PATH],control_loop=after_docs[CONTROL_LOOP_PATH],
        )
        targets=["C_MIXED"]
        row,receipt_doc=bound_receipt(before,after,targets,"DEPTH_CONTRACTION")
        def resolver(path):
            return receipt_doc,B40
        with self.assertRaisesRegex(TerminalProgressEnforcementError,"BLOB_MISMATCH"):
            evaluate_postchange(
                work_class="PROGRESS_CANDIDATE",target_truth_obligations=targets,
                before_documents=before_docs,after_documents=after_docs,
                evidence_record={"evidence_receipts":[row]},resolve_receipt=resolver,
            )

    def test_receipt_file_must_contain_same_transition_binding(self):
        before_docs=docs(); after_docs=copy.deepcopy(before_docs)
        after_docs[CONTROL_LOOP_PATH]["claims"][2]["status"]="PROVED"
        before=compile_canonical_state(
            pointer=before_docs[POINTER_PATH],root_state=before_docs[ROOT_STATE_PATH],
            tournament=before_docs[TOURNAMENT_PATH],control_loop=before_docs[CONTROL_LOOP_PATH],
        )
        after=compile_canonical_state(
            pointer=after_docs[POINTER_PATH],root_state=after_docs[ROOT_STATE_PATH],
            tournament=after_docs[TOURNAMENT_PATH],control_loop=after_docs[CONTROL_LOOP_PATH],
        )
        targets=["C_MIXED"]
        row,receipt_doc=bound_receipt(before,after,targets,"DEPTH_CONTRACTION")
        receipt_doc=dict(receipt_doc); receipt_doc["effect_kind"]="FAKE"
        with self.assertRaisesRegex(TerminalProgressEnforcementError,"CONTENT_BINDING_MISMATCH"):
            evaluate_postchange(
                work_class="PROGRESS_CANDIDATE",target_truth_obligations=targets,
                before_documents=before_docs,after_documents=after_docs,
                evidence_record={"evidence_receipts":[row]},
                resolve_receipt=lambda path:(receipt_doc,A40),
            )

    def test_truth_repair_is_admitted_but_zero_progress(self):
        before_docs=docs(); after_docs=copy.deepcopy(before_docs)
        # Add a new active claim without deleting terminal truth: truth repair may expand proof work.
        after_docs[CONTROL_LOOP_PATH]["claims"].append(
            {"id":"C3","status":"ACTIVE","depends_on":[]}
        )
        before=compile_canonical_state(
            pointer=before_docs[POINTER_PATH],root_state=before_docs[ROOT_STATE_PATH],
            tournament=before_docs[TOURNAMENT_PATH],control_loop=before_docs[CONTROL_LOOP_PATH],
        )
        after=compile_canonical_state(
            pointer=after_docs[POINTER_PATH],root_state=after_docs[ROOT_STATE_PATH],
            tournament=after_docs[TOURNAMENT_PATH],control_loop=after_docs[CONTROL_LOOP_PATH],
        )
        targets=["C_MIXED"]
        row,receipt_doc=bound_receipt(before,after,targets,"TRUTH_REPAIR")
        out=evaluate_postchange(
            work_class="TRUTH_REPAIR",target_truth_obligations=targets,
            before_documents=before_docs,after_documents=after_docs,
            evidence_record={"countermodel_receipts":[row]},
            resolve_receipt=lambda path:(receipt_doc,A40),
        )
        self.assertEqual(out["gate_result"]["status"],"ADMIT_TRUTH_REPAIR_NOT_PROGRESS")
        self.assertFalse(out["gate_result"]["counts_as_progress"])

if __name__=="__main__":
    unittest.main(verbosity=2)
