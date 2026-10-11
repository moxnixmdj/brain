from hashlib import sha1
import json

from canonical.runtime.terminal_closure_reducer import evaluate_manifest


def _git_blob_sha(path):
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _base_manifest(universal_cover_proof=None):
    families = [{"id": f"F{i}", "closure_state": "OPEN"} for i in range(19)]
    predicates = {
        "exact_target_family_count_19": True,
        "every_required_behavior_contracted": True,
        "every_required_behavior_has_admissible_proof": True,
        "donor_dependent_required_behaviors_zero": True,
        "unexplained_required_behaviors_zero": True,
        "unresolved_verifier_mutations_zero": True,
        "unresolved_composition_failures_zero": True,
        "contaminated_evidence_used_for_promotion_zero": True,
        "resource_or_authority_violations_zero": True,
        "all_frozen_opus_acceptance_predicates_pass": False,
        "final_donor_deletion_cleanroom_pass": True,
        "proof_bundle_frozen": True,
    }
    counters = {
        "uncontracted_required_behaviors": 0,
        "unproved_required_behaviors": 0,
        "donor_dependent_required_behaviors": 0,
        "unresolved_verifier_mutations": 0,
        "unresolved_composition_failures": 0,
        "contaminated_promotion_evidence": 0,
        "resource_or_authority_violations": 0,
    }
    out = {
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": families,
        "counters": counters,
        "terminal_predicates": predicates,
    }
    if universal_cover_proof is not None:
        out["universal_cover_proof"] = universal_cover_proof
    return out

def _bind_current_donor_authority(tmp_path,manifest):
    reducer=tmp_path/"canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py"
    reducer.parent.mkdir(parents=True,exist_ok=True)
    reducer.write_text("# hardened synthetic reducer\n",encoding="utf-8")
    receipt_path=tmp_path/"global-ownership.json"
    receipt={
        "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__SYNTHETIC",
        "brain_reducer_blob_sha":_git_blob_sha(reducer),
        "result":{"terminal_predicates":{
            "final_donor_deletion_cleanroom_pass":True,
            "donor_deletion_protocol_v2_bound":True,
            "runtime_cognition_model_independent":True,
            "zero_external_model_runtime_cognition_dependencies":True,
            "copied_or_rehosted_teacher_absent":True,
            "runtime_dependency_inventory_complete":True,
        }},
    }
    receipt_path.write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
    manifest["global_ownership_postconditions"]={
        "status":"INDEPENDENT_PASS",
        "evidence":"global-ownership.json",
        "evidence_blob_sha":_git_blob_sha(receipt_path),
    }
    return manifest


def _write_valid_bound_proof(tmp_path):
    proof_path = tmp_path / "proof.json"
    proof = {
        "proof_kind": "SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id": "scope://opus55/observable-trace",
        "conclusion": "success",
        "observable_trace_scope_complete": True,
        "all_useful_target_behaviors_in_scope": True,
        "every_admission_sound": True,
        "residual_complement_unsat": True,
        "selected_cover_complete": True,
        "u_empty": True,
        "abc_closed": True,
        "all_credited_routes_brain_owned": True,
        "donor_independence_closed": True,
        "clean_room_replay_pass": True,
    }
    proof_path.write_text(json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8")
    proof_binding = {"path": "proof.json", "git_blob_sha": _git_blob_sha(proof_path)}

    verifier_path = tmp_path / "verifier.json"
    verifier = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": proof_binding,
    }
    verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
    verifier_binding = {
        "path": "verifier.json",
        "git_blob_sha": _git_blob_sha(verifier_path),
    }
    return {
        "proof_kind": proof["proof_kind"],
        "scope_id": proof["scope_id"],
        "conclusion": "success",
        "proof_artifact": proof_binding,
        "verifier_receipt_artifact": verifier_binding,
    }


def test_universal_route_requires_explicit_proof():
    out = evaluate_manifest({})
    assert out["achieved"] is False


def test_fake_hex_bindings_cannot_self_certify():
    declaration = {
        "proof_kind": "SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id": "scope://opus55/observable-trace",
        "conclusion": "success",
        "independent_verified": True,
        "exact_byte_bound": True,
        "observable_trace_scope_complete": True,
        "all_useful_target_behaviors_in_scope": True,
        "every_admission_sound": True,
        "residual_complement_unsat": True,
        "selected_cover_complete": True,
        "u_empty": True,
        "abc_closed": True,
        "all_credited_routes_brain_owned": True,
        "donor_independence_closed": True,
        "clean_room_replay_pass": True,
        "proof_artifact": {
            "path": "p",
            "git_blob_sha": "a" * 40,
        },
        "verifier_receipt_artifact": {
            "path": "v",
            "git_blob_sha": "b" * 40,
        },
    }
    out = evaluate_manifest(_base_manifest(declaration))
    assert out["achieved"] is False
    assert any(
        failure.startswith("UNIVERSAL_PROOF_ARTIFACT_UNBOUND:")
        for failure in out["universal_cover_route"]["failed_predicates"]
    )


def test_universal_scope_cover_route_requires_real_bound_bytes(tmp_path):
    declaration = _write_valid_bound_proof(tmp_path)
    manifest=_bind_current_donor_authority(tmp_path,_base_manifest(declaration))
    out = evaluate_manifest(manifest, repo_root=tmp_path)
    assert out["achieved"] is True
    assert out["proof_route"] == "UNIVERSAL_SCOPE_COMPLETE_COVER"


def test_universal_cover_cannot_bypass_missing_current_donor_authority(tmp_path):
    declaration=_write_valid_bound_proof(tmp_path)
    out=evaluate_manifest(_base_manifest(declaration),repo_root=tmp_path)
    assert out["achieved"] is False
    assert any(x.startswith("DONOR_AUTHORITY:") for x in out["failed_predicates"])


def test_proof_byte_drift_fails_closed(tmp_path):
    declaration = _write_valid_bound_proof(tmp_path)
    (tmp_path / "proof.json").write_text("{}\n", encoding="utf-8")
    out = evaluate_manifest(_base_manifest(declaration), repo_root=tmp_path)
    assert out["achieved"] is False
    assert "UNIVERSAL_PROOF_ARTIFACT_UNBOUND:GIT_BLOB_SHA_MISMATCH" in (
        out["universal_cover_route"]["failed_predicates"]
    )


def test_verifier_must_bind_exact_proof_artifact(tmp_path):
    declaration = _write_valid_bound_proof(tmp_path)
    verifier_path = tmp_path / "verifier.json"
    verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
    verifier["proof_artifact"] = {
        "path": "other.json",
        "git_blob_sha": "c" * 40,
    }
    verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
    declaration["verifier_receipt_artifact"]["git_blob_sha"] = _git_blob_sha(verifier_path)

    out = evaluate_manifest(_base_manifest(declaration), repo_root=tmp_path)
    assert out["achieved"] is False
    assert "UNIVERSAL_VERIFIER_PROOF_BINDING_MISMATCH" in (
        out["universal_cover_route"]["failed_predicates"]
    )
