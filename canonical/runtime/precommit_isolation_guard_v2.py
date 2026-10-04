"""Generic fail-closed precommit-isolation guard.

This guard checks mechanical antecedents shared by benchmark-specific
isolation proofs.  Passing it does NOT prove benchmark comparability and does
not authorize fresh reality.  Each benchmark still needs an independently
verified thin adapter for population/scorer/effort/tools/environment/comparator.
"""
from __future__ import annotations
import hashlib
from typing import Mapping, Any

SCHEMA = "PROJECT_BRAIN_PRECOMMIT_ISOLATION_GUARD_V2"
REQUIRED_COMPONENTS = ("candidate","harness","scorer","environment","policy")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise ValueError("BUNDLE_NOT_MAPPING")
    hashes = bundle.get("committed_hashes")
    executed = bundle.get("executed_hashes")
    if not isinstance(hashes, Mapping) or not isinstance(executed, Mapping):
        raise ValueError("HASH_MAP_MISSING")

    failures: list[str] = []
    for k in REQUIRED_COMPONENTS:
        c = hashes.get(k)
        e = executed.get(k)
        if not isinstance(c, str) or len(c) != 64:
            failures.append(f"INVALID_COMMITTED_HASH:{k}")
        if not isinstance(e, str) or len(e) != 64:
            failures.append(f"INVALID_EXECUTED_HASH:{k}")
        if isinstance(c, str) and isinstance(e, str) and c != e:
            failures.append(f"HASH_MISMATCH:{k}")

    booleans = {
        "commit_precedes_case_exposure": bundle.get("commit_precedes_case_exposure"),
        "independent_executor_controls_reveal": bundle.get("independent_executor_controls_reveal"),
        "no_evaluation_feedback_channel_to_candidate": bundle.get("no_evaluation_feedback_channel_to_candidate"),
        "outputs_bound_to_precommitment": bundle.get("outputs_bound_to_precommitment"),
    }
    for k, v in booleans.items():
        if v is not True:
            failures.append(f"ANTECEDENT_NOT_PROVED:{k}")

    adapter = bundle.get("benchmark_adapter")
    adapter_ok = isinstance(adapter, Mapping) and all(
        adapter.get(k) is True
        for k in ("population","scorer","effort","tools","environment","comparator")
    )
    if not adapter_ok:
        failures.append("BENCHMARK_ADAPTER_INCOMPLETE")

    mechanical_pass = not failures
    return {
        "schema": SCHEMA,
        "mechanical_antecedents_pass": mechanical_pass,
        "failures": failures,
        "generic_isolation_antecedents_satisfied": mechanical_pass,
        "benchmark_specific_comparability_proved": adapter_ok,
        "fresh_reality_authorized": False,
        "acceptance_credit_authorized": False,
        "execution_authority": False,
        "promotion_authority": False,
        "note": "A pass is only an input to a separately independently verified benchmark-specific activation.",
    }
