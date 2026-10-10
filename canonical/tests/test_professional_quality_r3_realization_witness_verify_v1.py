import base64
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from canonical.runtime import professional_quality_r3_realization_witness_verify_v1 as v
from canonical.runtime import professional_step_binding_authority_v1 as step_auth

def h(b):
    return sha256(b).hexdigest()

def witness():
    source=b"%PDF-source"
    output=b"%PDF-output"
    sv=b"png-source"
    ov=b"png-output"
    goal="bounded goal"
    payload={"behavior_id":v.BEHAVIOR_ID,"claim_scope":"BOUNDED_R3_V7_REALIZATION_WITNESS","format":"pdf","seed":73103,"edit":{"kind":"x"},"output_sha256":h(output)}
    paths=[{"role":"source_artifact","sha256":h(source)},{"role":"output_artifact","sha256":h(output)}]
    hard="NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1"
    triggers=[]
    d={
        "schema":v.WITNESS_SCHEMA,"date":"2026-10-10",
        "subject_kind":v.SUBJECT_KIND,"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,
        "subject_git_blob_sha":v.SUBJECT_BLOB,"profile_git_blob_sha":v.PROFILE_BLOB,
        "behavior_id":v.BEHAVIOR_ID,"step_id":v.STEP_ID,"format":"pdf","seed":73103,
        "goal":goal,"decision_payload":payload,"artifact_paths":paths,
        "hard_defect_profile_id":hard,"detected_triggers":triggers,
        "run_context_sha256":step_auth.run_context_digest(goal=goal,decision_payload=payload,artifact_paths=paths,hard_defect_profile_id=hard,detected_triggers=triggers),
        "source_artifact_sha256":h(source),"output_artifact_sha256":h(output),
        "source_audience_view_png_sha256":h(sv),"output_audience_view_png_sha256":h(ov),
        "source_artifact_b64":base64.b64encode(source).decode(),"output_artifact_b64":base64.b64encode(output).decode(),
        "source_audience_view_png_b64":base64.b64encode(sv).decode(),"output_audience_view_png_b64":base64.b64encode(ov).decode(),
        "structural_verdict":{"pass":True,"reason":"PASS"},
        "render_verdict":{"pass":True,"reason":"PASS","page_count":1,"changed_page_count":1,"max_pixel_fraction":0.001,"max_bbox_fraction":0.01},
        "render_stack":{
            "predecessor_verified_libreoffice_core":v.PREDECESSOR_RENDER_STACK["libreoffice_core"],
            "predecessor_verified_poppler_utils":v.PREDECESSOR_RENDER_STACK["poppler_utils"],
            "version_transport_claimed":False,"current_stack_requires_fresh_replay":True,
            **v.CURRENT_RENDER_STACK,
        },
        "scope":{"bounded_generated_explicit_low_level_text_edit_only":True,"arbitrary_semantic_target_correctness":False,
                 "whole_contract_scope_equivalence":False,"global_r3_root_closure":False,
                 "quality_authority":False,"terminal_authority":False},
    }
    d["evidence_sha256"]=h(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode())
    return d

class TestR3Witness(unittest.TestCase):
    def test_valid_bounded_witness_passes_zero_authority(self):
        out=v.verify_witness(witness())
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["root_subject_binding_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertTrue(out["public_replay_still_required"])
    def test_artifact_tamper_fails(self):
        d=witness(); d["output_artifact_b64"]=base64.b64encode(b"tamper").decode()
        self.assertEqual(v.verify_witness(d)["reason"],"CONTENT_ADDRESS_MISMATCH:output_artifact_b64")
    def test_view_tamper_fails(self):
        d=witness(); d["output_audience_view_png_b64"]=base64.b64encode(b"tamper").decode()
        self.assertEqual(v.verify_witness(d)["reason"],"CONTENT_ADDRESS_MISMATCH:output_audience_view_png_b64")
    def test_run_context_drift_fails(self):
        d=witness(); d["goal"]="different"
        core=dict(d); core.pop("evidence_sha256"); d["evidence_sha256"]=h(json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode())
        self.assertEqual(v.verify_witness(d)["reason"],"RUN_CONTEXT_DIGEST_MISMATCH")
    def test_render_stack_transport_is_forbidden(self):
        d=witness(); d["render_stack"]["version_transport_claimed"]=True
        core=dict(d); core.pop("evidence_sha256"); d["evidence_sha256"]=h(json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode())
        self.assertEqual(v.verify_witness(d)["reason"],"VERSION_TRANSPORT_BOUNDARY_INVALID")
    def test_global_r3_overclaim_fails(self):
        d=witness(); d["scope"]["global_r3_root_closure"]=True
        core=dict(d); core.pop("evidence_sha256"); d["evidence_sha256"]=h(json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode())
        self.assertEqual(v.verify_witness(d)["reason"],"WITNESS_SCOPE_OVERCLAIM:global_r3_root_closure")

if __name__=="__main__":
    unittest.main()
