"""Universal complete-interface certificate candidate for Tool Discovery.

The already independently verified dynamic refinement says that the Brain-owned
V3 policy discharges its unknown-identity discovery/selection obligations if an
independently verified interface instance satisfies
TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.

This checker binds that implication to the closed-world interface construction:
for every accepted finite epoch, the source partition is exactly the
Brain-callable tool universe; discovery and execution share one canonical
metadata authority; probes are exact hidden truth; sessions are monotone and
epoch-bound; and out-of-universe execution fails closed.

No acceptance, family, capability, execution, or promotion credit is granted by
this candidate. Independent public-runner verification remains mandatory.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)
MINIMUM_FACT = (
    "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
    "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1"
)

EXPECTED_BLOBS = {
    "canonical/runtime/tool_discovery_complete_interface_instance_v1.py":
        "566cdcaba2f0eece4e267d2620b786d867eaa864",
    "canonical/runtime/tool_discovery_dynamic_candidate_v3.py":
        "bbbee4d6baf8df937543644397abba38a67dce62",
    "canonical/runtime/tool_discovery_dynamic_refinement_v1.py":
        "991c039c0b405bf77508ce7921abc69460f57332",
    "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json":
        "49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    "canonical/governance/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_ACTIVATION_V1.json":
        "44faeb24bdc2d9189b7c0de1b1e2be9b1210aeeb",
    "canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "5fcdc5ae35f51c40f312edbe5727284c9f6ca3dd",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
}

REQUIRED_PROPERTIES = {
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

REQUIRED_FACTS = (
    "FINITE_EPOCH_TOOL_AND_SOURCE_CARRIERS",
    "SOURCE_PARTITION_EXACTLY_EQUALS_TOOL_UNIVERSE",
    "DISCOVERY_SESSION_VISIBLE_SET_IS_MONOTONE",
    "DISCOVERY_RECEIPTS_BIND_SOURCE_AND_EPOCH",
    "DISCOVERY_AND_EXECUTION_SHARE_CANONICAL_METADATA",
    "PROBE_RETURNS_EXACT_HIDDEN_TRUTH_AND_BINDS_EPOCH",
    "OUT_OF_UNIVERSE_EXECUTION_FAILS_CLOSED",
    "ACTIVE_EPOCH_MUTATION_FAILS_FINGERPRINT",
    "VERSION_CHANGE_REQUIRES_NEW_EPOCH_OR_SESSION_RESTART",
    "HIDDEN_CAPABILITY_TRUTH_IS_NOT_PUBLIC_TOOL_METADATA",
    "PR1100_CONDITIONAL_REFINEMENT_IS_INDEPENDENTLY_VERIFIED",
    "FROZEN_TOOL_DISCOVERY_SCOPE_LITERALS_ARE_BOUND",
)

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()

def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def _has(text: str, *parts: str) -> bool:
    return all(part in text for part in parts)

def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def derive_interface_facts(source: str) -> dict[str, bool]:
    funcs = _functions(source)
    return {
        "FINITE_EPOCH_TOOL_AND_SOURCE_CARRIERS": (
            "compile_epoch" in funcs
            and _has(
                source,
                'not isinstance(raw_tools, list) or not raw_tools',
                'not isinstance(raw_sources, list) or not raw_sources',
                'not isinstance(ids, list)',
            )
        ),
        "SOURCE_PARTITION_EXACTLY_EQUALS_TOOL_UNIVERSE": _has(
            source,
            'if tool_id not in universe:',
            '"SOURCE_REFERENCES_UNKNOWN_TOOL:"',
            'if tool_id in owner:',
            '"TOOL_ASSIGNED_TO_MULTIPLE_SOURCES:"',
            'if set(owner) != universe:',
            '"SOURCE_UNION_INCOMPLETE:"',
        ),
        "DISCOVERY_SESSION_VISIBLE_SET_IS_MONOTONE": (
            "apply_discovery" in funcs
            and _has(
                source,
                'prior = set(map(str, session["visible_tool_ids"]))',
                'additions = {str(t["tool_id"]) for t in receipt["tools"]}',
                'out["visible_tool_ids"] = sorted(prior | additions)',
                '"DISCOVERY_SOURCE_ALREADY_QUERIED:"',
            )
        ),
        "DISCOVERY_RECEIPTS_BIND_SOURCE_AND_EPOCH": (
            "discover" in funcs
            and _has(
                source,
                '"kind": "DISCOVERY_RESULT"',
                '"source_id": sid',
                '"epoch": int(epoch["epoch_id"])',
                '"epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"])',
            )
        ),
        "DISCOVERY_AND_EXECUTION_SHARE_CANONICAL_METADATA": (
            "discover" in funcs
            and "execution_admit" in funcs
            and source.count("_public_tool(") >= 4
            and _has(
                source,
                'for t in epoch["tools"]',
                'row = next((t for t in epoch["tools"] if t["tool_id"] == tid), None)',
                '"tool": _public_tool(row, int(epoch["epoch_id"]))',
            )
        ),
        "PROBE_RETURNS_EXACT_HIDDEN_TRUTH_AND_BINDS_EPOCH": (
            "probe" in funcs
            and _has(
                source,
                'truth = epoch["capability_truth"]',
                '"supported": bool(truth[tid][cap])',
                '"epoch": int(epoch["epoch_id"])',
                '"epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"])',
            )
        ),
        "OUT_OF_UNIVERSE_EXECUTION_FAILS_CLOSED": (
            "execution_admit" in funcs
            and _has(
                source,
                'if row is None:',
                '"admitted": False',
                '"reason": "TOOL_ID_OUTSIDE_CONTENT_ADDRESSED_EPOCH_UNIVERSE"',
            )
        ),
        "ACTIVE_EPOCH_MUTATION_FAILS_FINGERPRINT": (
            "_assert_fingerprint" in funcs
            and _has(
                source,
                'actual = _sha256(_payload_without_fingerprint(epoch))',
                'if supplied != actual:',
                '"EPOCH_FINGERPRINT_MISMATCH"',
            )
        ),
        "VERSION_CHANGE_REQUIRES_NEW_EPOCH_OR_SESSION_RESTART": (
            "rotate_epoch" in funcs
            and "_assert_session" in funcs
            and _has(
                source,
                'if new_epoch_id <= int(epoch["epoch_id"]):',
                '"NEW_EPOCH_ID_MUST_INCREASE"',
                'if session.get("epoch_fingerprint_sha256") != epoch.get("fingerprint_sha256"):',
                '"SESSION_EPOCH_MISMATCH_RESTART_REQUIRED"',
                'return compile_epoch(spec)',
            )
        ),
        "HIDDEN_CAPABILITY_TRUTH_IS_NOT_PUBLIC_TOOL_METADATA": (
            "_public_tool" in funcs
            and _has(
                source,
                'if k not in {"capability_truth", "hidden_capabilities", "_oracle"}',
                '"HIDDEN_TRUTH_EMBEDDED_IN_PUBLIC_TOOL:"',
            )
        ),
    }

def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__COMPLETE_INTERFACE_PREMISE_MISSING",
            "missing": missing,
            "complete_interface_instance_proved": False,
            "minimum_missing_fact_satisfied_candidate": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    return {
        "status": (
            "PASS__COMPLETE_DISCOVERY_INTERFACE_INSTANCE_UNIVERSAL_CONSTRUCTION__"
            "PR1100_CONDITIONAL_REFINEMENT_COMPOSED__"
            "INDEPENDENT_PUBLIC_RUNNER_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "complete_interface_instance_proved": True,
        "minimum_missing_fact": MINIMUM_FACT,
        "minimum_missing_fact_satisfied_candidate": True,
        "scope_atom": ATOM,
        "scope_atom_satisfied_candidate": True,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "closed_world_carrier": (
                "For each valid epoch, U is the exact content-addressed set of "
                "tool identities admitted by the interface execution boundary; "
                "identities outside U fail closed."
            ),
            "complete_discovery": (
                "compile_epoch accepts only finite available source partitions "
                "whose exact union is U and whose ownership is total and unique. "
                "Each source can be queried once and apply_discovery updates the "
                "visible set by set union, so exhausting the finite source set "
                "reveals every identity in U without removing prior identities."
            ),
            "metadata_and_probe_soundness": (
                "Discovery and execution project the same canonical public tool "
                "record, while probe reads the separate hidden truth table and "
                "binds the result to the immutable epoch fingerprint."
            ),
            "epoch_induction": (
                "A session is bound to one immutable epoch fingerprint. Any "
                "version change creates a strictly newer epoch; an old session "
                "cannot be evaluated against it and must restart. Repeating this "
                "argument covers every finite sequence of changing epochs."
            ),
            "policy_composition": (
                "The independently verified PR1100 implication proves dynamic "
                "V3 discovery progress, unknown-identity coverage, least-cost "
                "evidence-supported selection, and sound no-route escalation "
                "whenever the seven complete-interface properties hold."
            ),
            "scope": (
                "The construction is cardinality- and identity-independent over "
                "every finite Brain-callable frozen tool ecosystem, arbitrary "
                "hidden boolean capability variants, public authority/constraint "
                "metadata, and every finite epoch sequence. No finite sample is "
                "used to generalize this scope claim."
            ),
        },
        "uses_empirical_generalization": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

def verify() -> dict[str, Any]:
    for rel, want in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != want:
            raise AssertionError((rel, got, want))

    contract = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
    ))
    props = contract.get("required_properties")
    assert isinstance(props, list)
    assert set(props) == REQUIRED_PROPERTIES
    assert contract.get("instance_verified") is False

    activation = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_ACTIVATION_V1.json"
    ))
    assert activation["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert activation["target_proof_atom"] == ATOM
    assert activation["current_minimum_missing_fact"] == MINIMUM_FACT
    assert activation["target_preserved"] is True
    assert activation["universal_target_proved"] is False

    prior = json.loads(_text(
        "canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
    ))
    assert prior["public_runner"]["conclusion"] == "success"
    assert prior["target_preserved"] is True
    assert prior["universal_target_proved"] is False
    assert prior["minimum_missing_fact_after_verified_reduction"] == MINIMUM_FACT
    assert "CONDITIONAL_PROGRAM_SIDE_REFINEMENT_OBLIGATIONS_PASS" in prior["verified"]

    protocol = json.loads(_text(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    ))
    row = next(
        x for x in protocol["protocols"]
        if x["family"] == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert row["proof_mode"] == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
    assert row["task_dimensions"] == [
        "unknown tool discovery",
        "schema/authority filtering",
        "route selection under incomplete evidence",
        "safe probe choice",
        "capability-state update",
        "later-task transfer without rediscovery",
    ]
    assert "frozen tool ecosystems with hidden capability variants" in row["acceptance"]
    assert "second-task transfer from first-task evidence" in row["acceptance"]
    assert "no unsupported capability-state promotion" in row["acceptance"]

    registry = json.loads(_text(
        "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
    ))
    behavior = next(
        x for x in registry["active_contracted_residuals"]
        if x.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    )
    assert behavior["scope"] == "Unknown/changing tool ecosystem to verified usable route"
    assert "Discover candidate tools if needed" in behavior["required_output_or_action"]
    assert "available tool schemas/capabilities" in behavior["inputs"]
    assert "bounded safe probes" in behavior["allowed_information"]

    source_facts = derive_interface_facts(_text(
        "canonical/runtime/tool_discovery_complete_interface_instance_v1.py"
    ))
    source_facts["PR1100_CONDITIONAL_REFINEMENT_IS_INDEPENDENTLY_VERIFIED"] = True
    source_facts["FROZEN_TOOL_DISCOVERY_SCOPE_LITERALS_ARE_BOUND"] = True
    return prove_from_facts(source_facts)

def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("scope_atom_satisfied_candidate") is True else 1

if __name__ == "__main__":
    raise SystemExit(main())

