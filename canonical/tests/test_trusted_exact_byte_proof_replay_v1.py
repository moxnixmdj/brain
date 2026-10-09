from copy import deepcopy

from canonical.runtime import trusted_exact_byte_proof_replay_v1 as replay


def _input():
    return {
        "contracts": [
            {
                "instruction_id": "length_constraints:nth_paragraph_first_word",
                "n": 1,
                "first_word": "Forbidden",
            },
            {
                "instruction_id": "keywords:forbidden_words",
                "forbidden_words": ["Forbidden"],
            },
        ]
    }


def _request(payload=None):
    payload = payload or _input()
    input_sha = replay._sha256(payload)
    return {
        "kernel_id": "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1",
        "kernel_path": replay.TRUSTED_KERNELS[
            "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1"
        ]["path"],
        "kernel_git_blob_sha": replay.TRUSTED_KERNELS[
            "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1"
        ]["git_blob_sha"],
        "input": payload,
        "input_sha256": input_sha,
        "expected_claim": {
            "kind": "BOUNDED_CONTRACT_SET_UNSAT",
            "input_sha256": input_sha,
            "kernel_schema": "PROJECT_BRAIN_LIVEBENCH_UNION25_SEMANTIC_UNSAT_KERNEL_V1",
            "conclusion": "UNSAT",
        },
    }


def test_exact_allowlisted_kernel_replays_and_proves_bound_claim():
    out = replay.replay(_request())
    assert out["pass"] is True, out
    assert out["independent_proof_replay_performed"] is True
    assert out["proof_verified"] is True
    assert out["verification_authority_mutated"] is False
    assert out["terminal_authority"] is False


def test_unknown_kernel_cannot_self_authorize():
    req = _request()
    req["kernel_id"] = "MY_MAGIC_THEOREM_PROVER"
    out = replay.replay(req)
    assert out["pass"] is False
    assert out["reason"] == "KERNEL_NOT_ALLOWLISTED"


def test_forged_kernel_sha_fails_closed():
    req = _request()
    req["kernel_git_blob_sha"] = "0" * 40
    out = replay.replay(req)
    assert out["pass"] is False
    assert out["reason"] == "KERNEL_SHA_MISMATCH"


def test_mutated_input_after_digest_fails_closed():
    req = _request()
    req["input"]["contracts"][0]["first_word"] = "Changed"
    out = replay.replay(req)
    assert out["pass"] is False
    assert out["reason"] == "INPUT_SHA256_MISMATCH"


def test_true_kernel_result_cannot_be_relabelled_as_different_theorem():
    req = _request()
    req["expected_claim"] = {
        "kind": "SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id": "scope://opus55/observable-trace",
        "conclusion": "UNSAT",
    }
    out = replay.replay(req)
    assert out["pass"] is False
    assert out["reason"] == "REPLAYED_CLAIM_MISMATCH"


def test_no_unsat_proof_remains_unknown():
    payload = {"contracts": [{"instruction_id": "keywords:forbidden_words", "forbidden_words": ["x"]}]}
    req = _request(payload)
    out = replay.replay(req)
    assert out["pass"] is False
    assert out["reason"] == "KERNEL_DID_NOT_PROVE_REQUESTABLE_CLAIM"
