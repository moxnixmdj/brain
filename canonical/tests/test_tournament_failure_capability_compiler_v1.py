from canonical.runtime.tournament_failure_capability_compiler_v1 import (
    evaluate_cell,
    evaluate_manifest,
)


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


def test_persistent_separator_requires_content_addressed_receipts():
    base = {
        "id": "c",
        "worlds": [
            {"id": "w1", "adequate_actions": ["a"]},
            {"id": "w2", "adequate_actions": ["b"]},
        ],
        "persistent_separator": {
            "bits": 1,
            "world_to_symbol": {"w1": "0", "w2": "1"},
        },
    }
    out = evaluate_cell(base)
    assert out["pass"] is False

    base["persistent_separator"]["necessity_proof"] = {
        "path": "proof.json",
        "git_blob_sha": "a" * 40,
    }
    base["persistent_separator"]["independent_verifier_receipt"] = {
        "path": "verify.json",
        "git_blob_sha": "b" * 40,
    }
    out = evaluate_cell(base)
    assert out["pass"] is True
    assert out["classification"] == "PERSISTENT_SEPARATOR_CANDIDATE"
    assert out["requires_exact_byte_verification_before_credit"] is True


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
