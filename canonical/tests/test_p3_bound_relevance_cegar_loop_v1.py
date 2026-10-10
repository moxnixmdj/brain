from unittest.mock import patch

from canonical.runtime.p3_bound_relevance_cegar_loop_v1 import evaluate


def base_payload():
    return {
        "context_id":"ctx",
        "v3_input":{"task":{"claims":[]}},
        "cegar_problem":{"formal_source_constraints":[]},
        "truth_payloads_by_discriminator_id":{},
        "truth_payloads_by_predicate_id":{},
        "source_positive_selection_contracts":{},
        "max_refinement_steps":3,
    }


def common(policy="p"):
    return {
        "pass":True,
        "status":"COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
        "common_policy_certified":True,
        "selected_policy_id":policy,
    }


def selected(did="d", atom="source-condition-sha256:a"):
    return {
        "pass":False,
        "status":"UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED",
        "common_policy_certified":False,
        "selected_discriminator":{
            "discriminator_id":did,
            "formula":{"op":"ATOM","id":atom},
            "cost_units":1.0,
            "branches":[],
        },
    }


def realized(policy="p"):
    return {
        "pass":True,
        "status":"PASS__P3_SOURCE_POSITIVE_SELECTION_CELL",
        "selected_policy_id":policy,
        "selected_claim_ids":["A"],
        "rendered_text":"A",
        "render_trace":[],
    }


def truth(atom="source-condition-sha256:a", value="TRUE"):
    return {
        "pass":True,
        "status":"PASS__SELECTED_SEMANTIC_PREDICATE_PROVED_"+value,
        "predicate_id":atom,
        "requested_predicate_id":"alias",
        "predicate_truth":value,
        "truthful_precommitment_observation":True,
    }


def test_common_policy_realizes_without_truth_query():
    p=base_payload()
    p["source_positive_selection_contracts"]={"p":{"selected_policy_id":"p"}}
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=common()), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_selection",return_value=realized()
    ), patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth") as t:
        out=evaluate(p)
    assert out["pass"] is True,out
    assert out["selected_policy_id"]=="p"
    assert out["refinement_steps"]==0
    t.assert_not_called()


def test_true_selected_atom_refines_then_realizes():
    atom="source-condition-sha256:a"
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    p["source_positive_selection_contracts"]={"p":{"selected_policy_id":"p"}}
    seen=[]
    def cegar(problem):
        seen.append(problem)
        return selected(atom=atom) if len(seen)==1 else common()
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",side_effect=cegar), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=truth(atom,"TRUE")
    ), patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_selection",return_value=realized()):
        out=evaluate(p)
    assert out["pass"] is True,out
    assert seen[1]["formal_source_constraints"]==[{"op":"ATOM","id":atom}]
    assert out["refinement_steps"]==1


def test_false_selected_atom_refines_with_not_then_realizes():
    atom="source-condition-sha256:a"
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    p["source_positive_selection_contracts"]={"p":{"selected_policy_id":"p"}}
    seen=[]
    def cegar(problem):
        seen.append(problem)
        return selected(atom=atom) if len(seen)==1 else common()
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",side_effect=cegar), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=truth(atom,"FALSE")
    ), patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_selection",return_value=realized()):
        out=evaluate(p)
    assert out["pass"] is True,out
    assert seen[1]["formal_source_constraints"]==[{"op":"NOT","arg":{"op":"ATOM","id":atom}}]


def test_negated_selected_formula_still_binds_underlying_atom_identity():
    atom="source-condition-sha256:a"
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    s=selected(atom=atom)
    s["selected_discriminator"]["formula"]={"op":"NOT","arg":{"op":"ATOM","id":atom}}
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=s), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=truth(atom,"TRUE")
    ):
        out=evaluate(p)
    assert out["pass"] is False
    assert out["status"]=="OPEN__REFINEMENT_STEP_BOUND_EXHAUSTED" or out["reason"]=="CEGAR_REFINEMENT_NO_PROGRESS_REPEAT_OBSERVATION"


def test_truth_identity_mismatch_fails_closed():
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=selected(atom="source-condition-sha256:a")), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=truth("source-condition-sha256:b","TRUE")
    ):
        out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="SELECTED_DISCRIMINATOR_TRUTH_IDENTITY_MISMATCH"


def test_caller_alias_cannot_authorize_mismatched_truth():
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    tr=truth("source-condition-sha256:b","TRUE")
    tr["requested_predicate_id"]="source-condition-sha256:a"
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=selected(atom="source-condition-sha256:a")), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=tr
    ):
        out=evaluate(p)
    assert out["reason"]=="SELECTED_DISCRIMINATOR_TRUTH_IDENTITY_MISMATCH"


def test_unknown_truth_localizes_proof_coverage():
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    unknown={
        "pass":False,"status":"UNKNOWN__SELECTED_PREDICATE_NOT_PROVED",
        "predicate_truth":"UNKNOWN","truthful_precommitment_observation":False,
    }
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=selected()), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=unknown
    ):
        out=evaluate(p)
    assert out["status"]=="OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"


def test_unknown_truth_preserves_single_actionable_information_request():
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":{"x":1}}
    request={
        "request_kind":"ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
        "minimum_observation_count":1,
        "independent_verification_required":True,
    }
    template={
        "schema":"PROJECT_BRAIN_SEMANTIC_TRUTH_MATERIALIZATION_TEMPLATE_V1",
        "truth_kind":"REGCAP_LOSS_CUSHION_GROUNDING",
        "claim_kind":"RELATIVE_RIVAL_SELECTION",
        "target_concept_id":"REGCAP::CCOB",
        "provider_semantic_truth_authority":False,
    }
    unknown={
        "pass":False,
        "status":"UNKNOWN__SELECTED_PREDICATE_NOT_PROVED",
        "predicate_truth":"UNKNOWN",
        "truthful_precommitment_observation":False,
        "next_information_request":request,
        "next_required_edge":"REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
        "checker_materialization_template":template,
    }
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=selected()), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=unknown
    ):
        out=evaluate(p)
    assert out["status"]=="OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"
    assert out["next_information_request"]==request
    assert out["next_required_edge"]=="REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION"
    assert out["checker_materialization_template"]==template
    assert "next_information_request" not in out.get("detail",{})
    assert "checker_materialization_template" not in out.get("detail",{})


def test_conflicting_actionable_truth_requests_remain_candidates():
    p=base_payload()
    p["truth_payloads_by_discriminator_id"]={"d":[{"x":1},{"x":2}]}
    requests=[
        {"request_kind":"A","minimum_observation_count":1},
        {"request_kind":"B","minimum_observation_count":1},
    ]
    returned=iter([
        {
            "pass":False,"status":"UNKNOWN__A","predicate_truth":"UNKNOWN",
            "truthful_precommitment_observation":False,
            "next_information_request":requests[0],
            "next_required_edge":"EDGE_A",
        },
        {
            "pass":False,"status":"UNKNOWN__B","predicate_truth":"UNKNOWN",
            "truthful_precommitment_observation":False,
            "next_information_request":requests[1],
            "next_required_edge":"EDGE_B",
        },
    ])
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=selected()), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",
        side_effect=lambda payload: next(returned),
    ):
        out=evaluate(p)
    assert out["status"]=="OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"
    assert out["next_information_request_candidates"]==requests
    assert out["next_required_edge"]=="DISAMBIGUATE_SELECTED_PREDICATE_INFORMATION_REQUEST"
    assert "next_information_request" not in out


def test_composite_selected_formula_is_proved_from_authoritative_atoms_with_short_circuit():
    a="source-condition-sha256:a"
    b="source-condition-sha256:b"
    p=base_payload()
    p["truth_payloads_by_predicate_id"]={a:{"a":1},b:{"b":1}}
    p["source_positive_selection_contracts"]={"p":{"selected_policy_id":"p"}}
    s=selected(atom=a)
    s["selected_discriminator"]["formula"]={
        "op":"OR",
        "args":[{"op":"ATOM","id":a},{"op":"ATOM","id":b}],
    }
    seen=[]
    def cegar(problem):
        seen.append(problem)
        return s if len(seen)==1 else common()
    def truth_eval(payload):
        if "a" in payload:
            return truth(a,"TRUE")
        raise AssertionError("OR short circuit should not request b after a is true")
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",side_effect=cegar), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",side_effect=truth_eval
    ), patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_selection",return_value=realized()):
        out=evaluate(p)
    assert out["pass"] is True,out
    assert seen[1]["formal_source_constraints"]==[{"op":"ATOM","id":a}]


def test_composite_formula_missing_atom_payload_localizes_exact_atom():
    a="source-condition-sha256:a"
    b="source-condition-sha256:b"
    p=base_payload()
    p["truth_payloads_by_predicate_id"]={a:{"a":1}}
    s=selected(atom=a)
    s["selected_discriminator"]["formula"]={
        "op":"AND",
        "args":[{"op":"ATOM","id":a},{"op":"ATOM","id":b}],
    }
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=s), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_truth",return_value=truth(a,"TRUE")
    ):
        out=evaluate(p)
    assert out["status"]=="OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED"
    assert out["detail"]["predicate_id"]==b


def test_policy_coverage_hole_is_not_misclassified_as_relevance():
    p=base_payload()
    hole={"pass":False,"status":"FAIL_CLOSED","reason":"AUTHENTICATED_POLICY_COVER_INCOMPLETE"}
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=hole):
        out=evaluate(p)
    assert out["status"]=="OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED"


def test_common_policy_without_exact_selection_binding_stays_open():
    p=base_payload()
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=common()):
        out=evaluate(p)
    assert out["status"]=="OPEN__COMMON_POLICY_SELECTION_BINDING_REQUIRED"


def test_no_terminal_authority_on_success():
    p=base_payload()
    p["source_positive_selection_contracts"]={"p":{"selected_policy_id":"p"}}
    with patch("canonical.runtime.p3_bound_relevance_cegar_loop_v1.solve_cegar",return_value=common()), patch(
        "canonical.runtime.p3_bound_relevance_cegar_loop_v1.evaluate_selection",return_value=realized()
    ):
        out=evaluate(p)
    assert out["pass"] is True
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
