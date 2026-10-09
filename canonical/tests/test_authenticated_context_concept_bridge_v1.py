import json
import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime.authenticated_context_concept_bridge_v1 import CONTEXT_AUTHORITY_SCHEMA, resolve
from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context

SCOPE="finance:test-sense"

def registry(same=False):
    a={"action":"SAME"} if same else {"action":"PROFIT"}
    b={"action":"SAME"} if same else {"action":"COLLATERAL"}
    return {
        "schema":universe.REGISTRY_SCHEMA,"registry_id":"finance-margin-v1","scope_id":SCOPE,
        "bounded_finite_registry":True,
        "concepts":[
            {"concept_id":"PROFIT_MARGIN","surfaces":["margin"],"attributes":{"phase":"income_statement","domain":"finance"},"terminal_signature_complete":True,"terminal_signature":a},
            {"concept_id":"COLLATERAL_MARGIN","surfaces":["margin"],"attributes":{"phase":"collateral","domain":"finance"},"terminal_signature_complete":True,"terminal_signature":b},
        ],
        "observations":[{"observation_id":"CHECK_PHASE","outcome_map_complete":True,"outcomes":{"PROFIT_MARGIN":"income_statement","COLLATERAL_MARGIN":"collateral"},"cost_units":1}],
    }

def reg_verify(reg):
    checked=universe._validate_registry(reg)
    def verify(_):
        return {"pass":True,"schema":universe.AUTHORITY_SCHEMA,"registry_sha256":checked["registry_sha256"],
                "registry_id":reg["registry_id"],"scope_id":reg["scope_id"],
                "scope_completeness_authenticated":True,"concept_semantics_authenticated":True,
                "verification_authority_mutated":False,"receipt_sha256":"a"*64}
    return verify

def raw(phase="collateral",include_phase=True):
    fields={"domain":{"type":"STRING","value":"finance"}}
    if include_phase: fields["phase"]={"type":"STRING","value":phase}
    return json.dumps({"schema_id":"finance-case-v1","fields":fields},sort_keys=True)

def ctx_verify(source,projection):
    c=compile_typed_context(source,source_id="case.json")
    def verify(_):
        return {"pass":True,"schema":CONTEXT_AUTHORITY_SCHEMA,"scope_id":SCOPE,"source_id":"case.json",
                "raw_source_sha256":c["raw_source_sha256"],"typed_context_sha256":c["typed_context_sha256"],
                "source_authorized_for_scope":True,"field_semantics_authenticated":True,
                "verification_authority_mutated":False,"attribute_projection":projection,"receipt_sha256":"b"*64}
    return verify

def phase_projection(kind="STRING"):
    return [{"registry_attribute":"phase","field_name":"phase","field_type":kind}]

def domain_projection():
    return [{"registry_attribute":"domain","field_name":"domain","field_type":"STRING"}]

class Tests(unittest.TestCase):
    def test_two_authorities_bind_unique_concept(self):
        reg=registry(); source=raw()
        out=resolve(registry=reg,raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg),
            context_authority_receipt={"x":1},context_authority_verifier=ctx_verify(source,phase_projection()))
        self.assertTrue(out["pass"],out); self.assertTrue(out["concept_binding_proved"])
        self.assertEqual(out["concept_id"],"COLLATERAL_MARGIN")

    def test_context_cannot_self_authorize(self):
        reg=registry()
        out=resolve(registry=reg,raw_context_source=raw(),context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg))
        self.assertFalse(out["pass"]); self.assertFalse(out["context_source_authorized"])
        self.assertEqual(out["status"],"OPEN__AUTHENTICATED_CONTEXT_SOURCE_REQUIRED")

    def test_registry_cannot_self_authorize(self):
        source=raw()
        out=resolve(registry=registry(),raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            context_authority_receipt={"x":1},context_authority_verifier=ctx_verify(source,phase_projection()))
        self.assertFalse(out["pass"]); self.assertTrue(out["context_source_authorized"])
        self.assertFalse(out["registry_scope_authenticated"])

    def test_wrong_context_binding_rejected(self):
        reg=registry(); source=raw()
        def wrong(_):
            row=ctx_verify(source,phase_projection())({}); row["raw_source_sha256"]="0"*64; return row
        out=resolve(registry=reg,raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg),
            context_authority_receipt={"x":1},context_authority_verifier=wrong)
        self.assertFalse(out["pass"]); self.assertFalse(out["context_source_authorized"])

    def test_partial_context_reuses_existing_discriminator(self):
        reg=registry(); source=raw(include_phase=False)
        out=resolve(registry=reg,raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg),
            context_authority_receipt={"x":1},context_authority_verifier=ctx_verify(source,domain_projection()))
        self.assertFalse(out["pass"],out); self.assertEqual(out["next_observation_id"],"CHECK_PHASE")

    def test_terminally_equivalent_survivors_stop_without_identity(self):
        reg=registry(True); source=raw(include_phase=False)
        out=resolve(registry=reg,raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg),
            context_authority_receipt={"x":1},context_authority_verifier=ctx_verify(source,domain_projection()))
        self.assertTrue(out["pass"],out); self.assertFalse(out["concept_binding_proved"])
        self.assertTrue(out["does_not_require_global_word_sense_identity"])

    def test_projection_type_is_checked(self):
        reg=registry(); source=raw()
        out=resolve(registry=reg,raw_context_source=source,context_source_id="case.json",scope_id=SCOPE,
            registry_authority_receipt={"x":1},registry_authority_verifier=reg_verify(reg),
            context_authority_receipt={"x":1},context_authority_verifier=ctx_verify(source,phase_projection("BOOL")))
        self.assertFalse(out["pass"]); self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("ATTRIBUTE_PROJECTION_FIELD_TYPE_MISMATCH",out["reason"])

if __name__=="__main__": unittest.main(verbosity=2)
