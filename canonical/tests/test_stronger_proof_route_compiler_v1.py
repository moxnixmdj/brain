from canonical.runtime.stronger_proof_route_compiler_v1 import compile_routes, SCHEMA

SHA = "a" * 40

def receipt():
    return {"path": "canonical/verification/x.json", "git_blob_sha": SHA}

def route(kind, **kw):
    out = {
        "route_id": kind.lower(),
        "kind": kind,
        "verified": True,
        "independent": True,
        "receipt": receipt(),
        "scope_relation": "EXACT",
        "semantic_entailment_verified": True,
        "metric_entailment_verified": True,
    }
    out.update(kw)
    return out

def doc(routes):
    return {"schema": SCHEMA, "targets": [{"predicate_id": "P", "routes": routes}]}

def test_exact_existing_wins():
    v = compile_routes(doc([
        route("FORMAL_DOMINANCE_OR_EQUIVALENCE"),
        route("EXACT_EXISTING_CONTENT_ADDRESSED_RECEIPT"),
    ]))
    assert v["selected"]["P"]["kind"] == "EXACT_EXISTING_CONTENT_ADDRESSED_RECEIPT"

def test_scope_must_be_exact_or_superset():
    v = compile_routes(doc([route("VERIFIED_SCOPE_COMPLETE_SUPERSET", scope_relation="UNKNOWN")]))
    assert not v["selected"]

def test_owner_result_is_input_not_replacement():
    v = compile_routes(doc([route("OWNER_RESULT")]))
    assert not v["selected"]
    assert v["open_targets"][0]["rejected_routes"][0]["reason"] == "EVIDENCE_INPUT_NOT_REPLACEMENT_PROOF"

def test_custom_benchmark_requires_saturation():
    v = compile_routes(doc([route("NEW_CUSTOM_BENCHMARK")]))
    assert not v["selected"]
    v2 = compile_routes(doc([route("NEW_CUSTOM_BENCHMARK", external_dominance_saturated=True)]))
    assert v2["selected"]["P"]["kind"] == "NEW_CUSTOM_BENCHMARK"

def test_bad_receipt_is_rejected():
    r = route("OBJECTIVE_CEILING_OR_FLOOR")
    r["receipt"] = {"path": "x", "git_blob_sha": "bad"}
    v = compile_routes(doc([r]))
    assert not v["selected"]
