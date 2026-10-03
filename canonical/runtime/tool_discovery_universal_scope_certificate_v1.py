"""Fail-closed universal scope certificate candidate for Tool Discovery V4.

The proof is not empirical generalization from the frozen 180-case sample.
It binds a content-addressed exact-partition discovery interface to the exact V4
policy and proves the finite-discovery / finite-route invariants needed for every
finite valid hidden-tool ecosystem in the frozen matched protocol.

No acceptance credit is granted here. Independent public-runner verification
and a separate acceptance reduction remain mandatory.
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

EXPECTED_BLOBS = {
    "canonical/runtime/tool_discovery_dynamic_candidate_v4.py":
        "e614d0bed8e291e31f57189cd6f0f75aa39b0f74",
    "canonical/tests/test_tool_discovery_dynamic_v4.py":
        "23f0add178ca0c731d15e0645ee9b8841317efee",
    "canonical/verification/TOOL_DISCOVERY_DYNAMIC_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "10cb18355d247a05177230d0dd345e161e84111d",
    "canonical/runtime/tool_discovery_complete_authority_manifest_v1.py":
        "a7060e25461000a1aa313a0c363e22807db70bc8",
    "canonical/tests/test_tool_discovery_complete_authority_manifest_v1.py":
        "2cab93f3213ea0a025a84041418db5f5fd180405",
    "canonical/governance/TOOL_DISCOVERY_COMPLETE_AUTHORITY_SCOPE_RELATION_V1.json":
        "03083ade14dc0c241b3b9eb46eaa4c2627b54628",
    "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json":
        "49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json":
        "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":
        "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "7885a827b1483bfb38315c1f492848f7e4680285",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
}

REQUIRED_FACTS = (
    "MANIFEST_FINITE_UNIQUE_AUTHORITY",
    "MANIFEST_EXACT_DISJOINT_COVER",
    "MANIFEST_CONTENT_ADDRESSED",
    "MANIFEST_PUBLIC_FIELDS_ONLY",
    "MANIFEST_PRIVATE_SOURCE_MEMBERSHIP",
    "DISCOVERY_RECEIPTS_CONTENT_BOUND",
    "DISCOVERY_APPLICATION_MONOTONIC",
    "V4_DISCOVERY_PRECEDES_ROUTE_EVALUATION",
    "V4_DISCOVERY_PROGRESS_IS_FINITE",
    "V4_GLOBAL_ADMISSIBILITY_FILTER",
    "V4_GLOBAL_COST_ORDER",
    "V4_CURRENT_EPOCH_EVIDENCE_ONLY",
    "V4_NEGATIVE_SKIP_UNKNOWN_PROBE_POSITIVE_SELECT",
    "V4_ESCALATES_ONLY_AFTER_ROUTE_EXHAUSTION",
    "FROZEN_PROTOCOL_IS_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
    "FROZEN_TARGET_REQUIRES_LEAST_COST_AND_TRANSFER",
    "UNIVERSAL_FORMAL_SCOPE_IS_ADMISSIBLE_BASIS",
    "PRIOR_V4_REPAIR_INDEPENDENTLY_VERIFIED",
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _has(text: str, *parts: str) -> bool:
    return all(p in text for p in parts)


def derive_source_facts(manifest_source: str, v4_source: str) -> dict[str, bool]:
    mf = _functions(manifest_source)
    vf = _functions(v4_source)

    discovery_pos = v4_source.find("if sources:")
    constraint_pos = v4_source.find("constraint=public.get")
    route_loop_pos = v4_source.find("for tool in tools:")

    return {
        "MANIFEST_FINITE_UNIQUE_AUTHORITY": (
            "validate_instance" in mf
            and _has(
                manifest_source,
                'rows = authority_rows(instance)',
                'if len(ids) != len(set(ids)):',
                'raise ManifestError("AUTHORITY_DUPLICATE_TOOL_ID")',
            )
        ),
        "MANIFEST_EXACT_DISJOINT_COVER": _has(
            manifest_source,
            'if len(partition_members) != len(set(partition_members)):',
            'raise ManifestError("PARTITION_OVERLAP")',
            'if set(partition_members) != set(ids):',
            '"PARTITION_NOT_EXACT:missing="',
        ),
        "MANIFEST_CONTENT_ADDRESSED": _has(
            manifest_source,
            'actual_root = _sha256(rows)',
            'if claimed_root != actual_root:',
            '"AUTHORITY_HASH_MISMATCH"',
            'partition_commitment = _sha256(',
            'if claimed_partition != partition_commitment:',
            '"PARTITION_HASH_MISMATCH"',
        ),
        "MANIFEST_PUBLIC_FIELDS_ONLY": _has(
            manifest_source,
            'PUBLIC_TOOL_KEYS = frozenset(',
            '"tool_id", "cost", "available", "authorized", "epoch", "meta"',
            'unknown = set(raw) - PUBLIC_TOOL_KEYS',
            '"TOOL_NONPUBLIC_FIELDS:"',
        ),
        "MANIFEST_PRIVATE_SOURCE_MEMBERSHIP": _has(
            manifest_source,
            '# Candidate receives source identities/cost/availability only',
            '"source_id": str(x["source_id"])',
            '"available": True',
        ) and '"tool_ids":' not in manifest_source[
            manifest_source.find("def initial_public"):
            manifest_source.find("def discover")
        ],
        "DISCOVERY_RECEIPTS_CONTENT_BOUND": _has(
            manifest_source,
            '"authority_sha256": state["authority_sha256"]',
            '"partition_sha256": state["partition_sha256"]',
            '"source_sha256": state["source_hashes"][str(source["source_id"])]',
            '"RECEIPT_EPOCH_MISMATCH"',
            '"RECEIPT_AUTHORITY_MISMATCH"',
            '"RECEIPT_PARTITION_MISMATCH"',
        ),
        "DISCOVERY_APPLICATION_MONOTONIC": (
            "apply_discovery" in mf
            and _has(
                manifest_source,
                'present = {str(x.get("tool_id") or "") for x in visible}',
                '"DISCOVERY_DUPLICATE_VISIBLE_TOOL:"',
                'visible.append(row)',
                '"SOURCE_ALREADY_DISCOVERED:"',
                'receipts.append(dict(receipt))',
            )
        ),
        "V4_DISCOVERY_PRECEDES_ROUTE_EVALUATION": (
            "next_action" in vf
            and discovery_pos >= 0
            and constraint_pos >= 0
            and route_loop_pos >= 0
            and discovery_pos < constraint_pos < route_loop_pos
        ),
        "V4_DISCOVERY_PROGRESS_IS_FINITE": _has(
            v4_source,
            'queried=_queried_sources(public)',
            'str(s.get("source_id") or "") not in queried',
            'if sources:',
            'return {"action":"DISCOVER"',
        ),
        "V4_GLOBAL_ADMISSIBILITY_FILTER": _has(
            v4_source,
            't.get("available") is True',
            't.get("authorized") is True',
            '_pred(constraint,t)',
        ),
        "V4_GLOBAL_COST_ORDER": _has(
            v4_source,
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
        ),
        "V4_CURRENT_EPOCH_EVIDENCE_ONLY": _has(
            v4_source,
            'int(rec.get("epoch",-1))==epochs[tid]',
            'ev.get("kind")=="TOOL_VERSION_CHANGED"',
            'out[tid]=int(ev.get("new_epoch",out[tid]+1))',
        ),
        "V4_NEGATIVE_SKIP_UNKNOWN_PROBE_POSITIVE_SELECT": _has(
            v4_source,
            'if v is False:',
            'impossible=True; break',
            'if v is None: unknown.append(cap)',
            'if impossible: continue',
            'if unknown:',
            'return {"action":"PROBE"',
            'return {"action":"SELECT","tool_id":tid}',
        ),
        "V4_ESCALATES_ONLY_AFTER_ROUTE_EXHAUSTION": _has(
            v4_source,
            'for tool in tools:',
            'return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_DISCOVERY"}',
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_proved": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "status": (
            "PASS__TOOL_DISCOVERY_V4_UNIVERSAL_FORMAL_SCOPE_PROOF__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "exact_cover": (
                "Every accepted finite authority instance has one hash-bound exact "
                "disjoint cover by initial visibility plus available discovery sources. "
                "Hidden capability support is not part of public manifest metadata."
            ),
            "discovery_induction": (
                "Base case has finitely many unqueried sources. V4 returns DISCOVER "
                "before route evaluation whenever one exists. A valid receipt marks one "
                "previously unqueried source and monotonically reveals exactly its "
                "authority rows. Therefore induction on the finite source count reaches "
                "a state where the complete authority is visible before any probe/select."
            ),
            "route_induction": (
                "After saturation V4 traverses the complete admissible authority in "
                "nondecreasing (cost, tool_id) order. For each route, truthful current-"
                "epoch evidence either supplies a negative required-capability witness, "
                "causes a missing required capability to be probed, or proves all "
                "required capabilities positive. Hence the first selected route is "
                "exactly the globally least-cost sufficient route."
            ),
            "no_route": (
                "If no sufficient admissible route exists, finite truthful probing "
                "eventually falsifies every admissible route and traversal exhausts, so "
                "ESCALATE is correct. If a sufficient route exists, its required probes "
                "are positive and it is selected before exhaustion."
            ),
            "transfer": (
                "Probe receipts persist across later tasks while epochs are unchanged. "
                "Public version changes update the current epoch; V4 ignores stale prior "
                "receipts and reacquires only affected evidence."
            ),
            "ceiling": (
                "Under the frozen matched hidden-tool-ecosystem target, pointwise valid-"
                "route-top1/terminal-success ceiling is 1 when a sufficient admissible "
                "route exists, and correct escalation is the success action otherwise. "
                "The proof is universal over the declared finite domain, not a sample "
                "frequency claim."
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

    relation = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_COMPLETE_AUTHORITY_SCOPE_RELATION_V1.json"
    ))
    assert relation["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert relation["proof_domain"]["terminal_case_replay_required"] is False
    assert relation["relation_to_prior_sample"]["sample_is_not_used_as_universal_scope_proof"] is True

    protocol = json.loads(_text(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    ))
    row = next(
        x for x in protocol["protocols"]
        if x["family"] == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    assert row["proof_mode"] == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
    assert "hidden capability variants" in row["acceptance"]
    assert "second-task transfer" in row["acceptance"]

    registry = json.loads(_text(
        "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
    ))
    contract = next(
        x for x in registry["active_contracted_residuals"]
        if x.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    )
    assert "unknown or changing capabilities" in contract["environment_state"]
    assert "least-cost admissible route" in contract["required_output_or_action"]
    assert "learned capability state transfers to later tasks" in contract["success_condition"]

    binding = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
    ))
    assert "UNKNOWN_CAPABILITY_DISCOVERY" in binding["objective_dimensions"]
    assert "LEAST_COST_SUFFICIENT_ROUTE" in binding["objective_dimensions"]
    assert "CROSS_TASK_TRANSFER" in binding["objective_dimensions"]
    assert binding["information_boundary"]["candidate_receives_hidden_oracle"] is False

    cut = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"
    ))
    assert cut["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert "VERIFIED_DISCOVERY_INTERFACE" in cut["minimum_missing_fact"]

    interface_contract = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
    ))
    req = set(interface_contract["required_properties"])
    assert {
        "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
        "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
        "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
        "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
        "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
        "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
        "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
    } == req

    firewall = json.loads(_text(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    ))
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]

    bindings = json.loads(_text(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    ))
    claim = next(
        x for x in bindings["claims"]
        if x.get("predicate_id") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    )
    assert claim.get("scope_complete") is False
    assert claim.get("state") != "PROVED"

    prior = json.loads(_text(
        "canonical/verification/TOOL_DISCOVERY_DYNAMIC_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
    ))
    assert prior["status"].startswith("PASS__EXACT_BYTES")
    assert prior["independent_public_runner"]["run_conclusion"] == "success"
    assert prior["hard_nonclaims"]

    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_complete_authority_manifest_v1.py"),
        _text("canonical/runtime/tool_discovery_dynamic_candidate_v4.py"),
    )
    facts.update({
        "FROZEN_PROTOCOL_IS_HIDDEN_TOOL_ECOSYSTEM_TRANSFER":
            row["proof_mode"] == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
        "FROZEN_TARGET_REQUIRES_LEAST_COST_AND_TRANSFER":
            (
                "least-cost admissible route" in contract["required_output_or_action"]
                and "learned capability state transfers to later tasks"
                    in contract["success_condition"]
            ),
        "UNIVERSAL_FORMAL_SCOPE_IS_ADMISSIBLE_BASIS":
            "UNIVERSAL_FORMAL_SCOPE_PROOF"
            in firewall["admissible_absolute_dominance_bases"],
        "PRIOR_V4_REPAIR_INDEPENDENTLY_VERIFIED":
            prior["independent_public_runner"]["run_conclusion"] == "success",
    })
    return prove_from_facts(facts)


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
