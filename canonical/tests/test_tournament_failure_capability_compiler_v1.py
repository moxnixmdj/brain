import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime.tournament_failure_capability_compiler_v1 import (
    evaluate_cell,
    evaluate_manifest,
)


def _blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _world_digest(cell):
    material = [
        {"id": w["id"], "adequate_actions": sorted(set(w["adequate_actions"]))}
        for w in sorted(cell["worlds"], key=lambda w: w["id"])
    ]
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _install_receipts(root: Path, cell, *, minimum_policy_count: int, minimum_bits: int):
    digest = _world_digest(cell)
    proof = root / "proof.json"
    proof_doc = {
        "cell_id": cell["id"],
        "world_set_sha256": digest,
        "conclusion": "success",
        "separator_necessary": True,
        "minimum_policy_count": minimum_policy_count,
        "minimum_persistent_bits": minimum_bits,
    }
    proof.write_text(json.dumps(proof_doc, sort_keys=True) + "\n", encoding="utf-8")
    proof_binding = {"path": "proof.json", "git_blob_sha": _blob_sha(proof)}
    verifier = root / "verify.json"
    verifier_doc = {
        "cell_id": cell["id"],
        "world_set_sha256": digest,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": proof_binding,
    }
    verifier.write_text(json.dumps(verifier_doc, sort_keys=True) + "\n", encoding="utf-8")
    cell["persistent_separator"]["necessity_proof"] = proof_binding
    cell["persistent_separator"]["independent_verifier_receipt"] = {
        "path": "verify.json",
        "git_blob_sha": _blob_sha(verifier),
    }
    return proof


def test_common_policy_needs_zero_persistent_bits():
    out = evaluate_cell({
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a", "b"]},
            {"id": "w2", "adequate_actions": ["b", "c"]},
        ],
    })
    assert out["pass"] is True
    assert out["classification"] == "COMMON_POLICY"
    assert out["common_adequate_actions"] == ["b"]
    assert out["minimum_persistent_bits"] == 0


def test_tournament_failure_without_discriminator_fails_closed():
    out = evaluate_cell({
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["b"]},
        ],
    })
    assert out["pass"] is False
    assert out["classification"] == "TOURNAMENT_FAILURE_UNRESOLVED"
    assert out["minimum_policy_count"] == 2
    assert out["minimum_persistent_bits"] == 1
    assert out["conflicting_world_pairs"] == [["w1", "w2"]]


def test_precommitment_jit_discriminator_closes_failure():
    out = evaluate_cell({
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["b"]},
        ],
        "jit_discriminator": {
            "available_before_commitment": True,
            "world_to_value": {"w1": "left", "w2": "right"},
        },
    })
    assert out["pass"] is True
    assert out["classification"] == "JIT_DISCRIMINATOR"
    assert out["minimum_persistent_bits"] == 1


def test_discriminator_bucket_must_have_common_adequate_action():
    out = evaluate_cell({
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["b"]},
        ],
        "jit_discriminator": {
            "available_before_commitment": True,
            "world_to_value": {"w1": "same", "w2": "same"},
        },
    })
    assert out["pass"] is False
    assert out["classification"] == "TOURNAMENT_FAILURE_UNRESOLVED"


def test_persistent_separator_requires_exact_repository_bytes():
    base = {
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["b"]},
        ],
        "persistent_separator": {
            "bits": 1,
            "world_to_symbol": {"w1": "0", "w2": "1"},
            "necessity_proof": {"path": "missing-proof.json", "git_blob_sha": "a" * 40},
            "independent_verifier_receipt": {"path": "missing-verifier.json", "git_blob_sha": "b" * 40},
        },
    }
    with TemporaryDirectory() as td:
        root = Path(td)
        out = evaluate_cell(base, repo_root=root)
        assert out["pass"] is False

        proof = root / "proof.json"
        verifier = root / "verify.json"
        proof.write_text("{}\n", encoding="utf-8")
        verifier.write_text("{}\n", encoding="utf-8")
        base["persistent_separator"]["necessity_proof"] = {"path": "proof.json", "git_blob_sha": _blob_sha(proof)}
        base["persistent_separator"]["independent_verifier_receipt"] = {"path": "verify.json", "git_blob_sha": _blob_sha(verifier)}
        out = evaluate_cell(base, repo_root=root)
        assert out["pass"] is False

        proof = _install_receipts(root, base, minimum_policy_count=2, minimum_bits=1)
        out = evaluate_cell(base, repo_root=root)
        assert out["pass"] is True
        assert out["classification"] == "PERSISTENT_SEPARATOR_CANDIDATE"
        assert out["exact_repository_bytes_verified"] is True
        assert out["independent_semantic_verification_bound"] is True

        proof.write_text('{"mutated":true}\n', encoding="utf-8")
        out = evaluate_cell(base, repo_root=root)
        assert out["pass"] is False


def test_separator_symbol_alphabet_must_fit_declared_bits():
    cell = {
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["a"]},
            {"id": "w3", "adequate_actions": ["b"]},
            {"id": "w4", "adequate_actions": ["b"]},
        ],
        "persistent_separator": {
            "bits": 1,
            "world_to_symbol": {"w1": "s1", "w2": "s2", "w3": "s3", "w4": "s4"},
        },
    }
    with TemporaryDirectory() as td:
        root = Path(td)
        _install_receipts(root, cell, minimum_policy_count=2, minimum_bits=1)
        out = evaluate_cell(cell, repo_root=root)
        assert out["pass"] is False
        assert out["minimum_persistent_bits"] == 1


def test_invalid_world_container_fails_closed():
    out = evaluate_cell({"id": "c", "worlds": {"w1": {"adequate_actions": ["a"]}}})
    assert out["pass"] is False
    assert out["classification"] == "INVALID_CELL"
    assert out["reason"] == "WORLDS_INVALID"

def test_manifest_never_grants_terminal_credit():
    out = evaluate_manifest({
        "cells": [{
            "id": "c",
            "worlds": [
                {"id": "w1", "adequate_actions": ["a"]},
                {"id": "w2", "adequate_actions": ["a"]},
            ],
        }]
    })
    assert out["pass"] is True
    assert out["terminal_credit"] is False
