#!/usr/bin/env python3
"""Formal local runner for the frozen goal-directed sufficiency gate.

This is a producer-run local adversarial experiment. It is not a frontier
benchmark score, GUI/DOM oracle, independent cloud attestation, carrier
qualification, own-weights demonstration, or §6 completion claim.

Run:

    python3 -m canonical.tools.goal_directed_sufficiency_gate_v1

The cases are synthetic adversaries shaped by OSWorld 2.0 failure phenomena
(hidden state, conflict disambiguation, dynamic updates, final-state
verification), not OSWorld tasks and not a substitute for them.
"""
from __future__ import annotations

import datetime
import json
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_directed_sufficiency_gate_v1 as gate  # noqa: E402

SCHEMA = "BRAIN_GOAL_DIRECTED_SUFFICIENCY_GATE_V1__RECEIPT"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PREREG_PATH = ROOT / "GOAL_DIRECTED_SUFFICIENCY_PREREG_20261124_V1.md"
VERIFIER_PATH = ROOT / "canonical" / "tools" / "goal_directed_sufficiency_independent_verifier_v1.py"
ATTESTATION_PATH = ROOT / "canonical" / "verification" / "GOAL_DIRECTED_SUFFICIENCY_LOCAL_RECHECK_20261124_V1.json"
RECEIPT_PATH = ROOT / "canonical" / "verification" / "GOAL_DIRECTED_SUFFICIENCY_GATE_20261124_V1.json"

P1 = ("q1", "authority", "which_source")
P2 = ("q2", "freshness", "which_version")
P3 = ("q3", "user", "clarification")
G1 = ("g1", "decision", "choose_source")
PROBES = [P1, P2, P3]
GOAL_PROBES = [G1]

SAFE_EVIDENCE = [
    {"facts": ["goal.purchase_order", "relation.checked"], "outcome": True, "version": 1},
    {"facts": ["goal.purchase_order"], "outcome": False, "version": 1},
    {"facts": ["goal.purchase_order", "relation.checked", "fresh.instance"], "outcome": True, "version": 1},
]
SAFE_STATES = [
    ["goal.purchase_order"],
    ["relation.checked"],
    ["goal.purchase_order", "relation.checked"],
    ["goal.purchase_order", "relation.checked", "fresh.instance"],
]
SAFE_GOAL_FACTS = ["goal.purchase_order", "relation.checked"]
PLAN = ["READ_GOAL", "ASK_NAMED_GAP", "VERIFY_FINAL_STATE", "SAVE_ABSTRACT_RULE"]
ABSTRACT_TRACE = [
    {"phase": "observe", "relation": "source_authority"},
    {"phase": "ask", "relation": "named_gap"},
    {"phase": "verify", "relation": "final_state"},
]
FRESH_INSTANCES = [
    {"instance_id": "fresh-a", "expected_plan": PLAN},
    {"instance_id": "fresh-b", "expected_plan": PLAN},
    {"instance_id": "fresh-c", "expected_plan": PLAN},
]

EXPECTED = {
    "A1_READ_ONLY": gate.READ_ONLY,
    "A2_CONFLICT_ASK": gate.ASK_SETTLED,
    "A3_SAVE_ABSTRACT": gate.SAVE_ADMITTED,
    "N1_CALLER_AUTHORITY": gate.DENY_AUTHORITY,
    "N2_RAW_RECORDING": gate.DENY_RAW,
    "N3_SAME_STATE_HIDDEN_PRECONDITION": gate.DENY_INSUFFICIENT,
    "N4_SEPARATION_IMPOSSIBLE": gate.DENY_INSUFFICIENT,
    "N5_DYNAMIC_STALE_UPDATE": gate.DENY_DYNAMIC,
    "N6_OUTSIDE_HYPOTHESIS_SPACE": gate.DENY_OUTSIDE,
    "N7_OPEN_HYPOTHESIS_SPACE": gate.DENY_OPEN,
    "N8_INSTRUMENT_BLIND": gate.DENY_BLIND,
    "N9_UNADMITTED_FRESH_INSTANCES": gate.DENY_ADMISSION,
}
ADMITTED_IDS = frozenset({"A1_READ_ONLY", "A2_CONFLICT_ASK", "A3_SAVE_ABSTRACT"})


def _key(probe: Sequence[str]) -> str:
    return "|".join(str(x) for x in probe)


def two_regimes() -> list[dict[str, Any]]:
    return [
        {"regime_id": "latest_email_authoritative", "outcomes": {
            _key(P1): "latest_email", _key(P2): "v2", _key(P3): "latest_email",
            _key(G1): "latest_email"}},
        {"regime_id": "original_table_authoritative", "outcomes": {
            _key(P1): "original_table", _key(P2): "v1", _key(P3): "original_table",
            _key(G1): "original_table"}},
    ]


def blind_regimes() -> list[dict[str, Any]]:
    same = {
        _key(P1): "same", _key(P2): "same", _key(P3): "same", _key(G1): "same",
    }
    return [
        {"regime_id": "regime_a", "outcomes": dict(same)},
        {"regime_id": "regime_b", "outcomes": dict(same)},
    ]


def open_regimes(count: int = 25) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(count):
        label = f"regime_{i:02d}"
        rows.append({"regime_id": label, "outcomes": {
            _key(P1): label, _key(P2): label, _key(P3): label, _key(G1): label}})
    return rows


def _complex_base(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "instruction": "Reconcile the purchase-order workflow from the authoritative source.",
        "observation": {"elements": []},
        "goal_facts": list(SAFE_GOAL_FACTS),
        "scan_facts": list(SAFE_GOAL_FACTS),
        "evidence": [dict(r) for r in SAFE_EVIDENCE],
        "candidate_states": [list(r) for r in SAFE_STATES],
        "current_version": 1,
        "regime_rows": [],
        "probes": [list(p) for p in PROBES],
        "goal_probes": [list(p) for p in GOAL_PROBES],
        "oracle_name": "none",
        "candidate_store_payload": None,
        "plan_sketch": list(PLAN),
        "experience_trace": [dict(r) for r in ABSTRACT_TRACE],
        "fresh_instances": [dict(r) for r in FRESH_INSTANCES],
        "artifact_span": ["multi_item_state", "final_state"],
        "goal_family": "conflict_disambiguation",
        "env_kind": "stateful_workflow",
    }


def _question_base(case_id: str, oracle_name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    case = _complex_base(case_id)
    case.update({
        "goal_facts": list(SAFE_GOAL_FACTS) + ["authority.source"],
        "scan_facts": list(SAFE_GOAL_FACTS),
        "regime_rows": [dict(r) for r in rows],
        "oracle_name": oracle_name,
    })
    return case


def frozen_cases() -> list[dict[str, Any]]:
    """The exact case bundle frozen by the preregistration."""
    read_only = _complex_base("A1_READ_ONLY")
    read_only.update({
        "instruction": 'Click the "Save" button.',
        "observation": {"elements": [{"index": 0, "tag": "button", "text": "Save",
                                      "label": "Save", "value": "Save"}]},
        "goal_facts": ["button.save"],
        "scan_facts": ["button.save"],
        "evidence": [{"facts": ["button.save"], "outcome": True, "version": 1}],
        "candidate_states": [["button.save"]],
    })

    ask = _question_base("A2_CONFLICT_ASK", "latest_email", two_regimes())
    save = _complex_base("A3_SAVE_ABSTRACT")

    caller = _complex_base("N1_CALLER_AUTHORITY")
    caller["force_learn"] = True

    raw = _complex_base("N2_RAW_RECORDING")
    raw["candidate_store_payload"] = {
        "path": "/tmp/purchase_order.xlsx",
        "argv": ["click", "save"],
        "content": "exact bytes from the experience",
        "reward": 1,
    }

    hidden = _question_base("N3_SAME_STATE_HIDDEN_PRECONDITION", "none", [])
    hidden.update({
        "evidence": [
            {"facts": ["goal.expense", "source.email"], "outcome": True, "version": 1},
            {"facts": ["goal.expense", "source.email"], "outcome": False, "version": 1},
        ],
        "goal_facts": ["goal.expense", "authority.latest_email"],
        "scan_facts": ["goal.expense", "source.email"],
        "candidate_states": [["goal.expense", "source.email"]],
    })

    separation = _complex_base("N4_SEPARATION_IMPOSSIBLE")
    separation.update({
        "evidence": [
            {"facts": ["shared.fact"], "outcome": True, "version": 1},
            {"facts": ["shared.fact", "decoy.b"], "outcome": False, "version": 1},
            {"facts": ["shared.fact", "decoy.c"], "outcome": True, "version": 1},
        ],
        "goal_facts": ["shared.fact"],
        "scan_facts": ["shared.fact"],
        "candidate_states": [["shared.fact"], ["shared.fact", "decoy.b"],
                             ["shared.fact", "decoy.c"]],
    })

    dynamic = _complex_base("N5_DYNAMIC_STALE_UPDATE")
    dynamic.update({
        "current_version": 2,
        "goal_facts": list(SAFE_GOAL_FACTS) + ["dynamic.fresh_update"],
        "scan_facts": list(SAFE_GOAL_FACTS),
    })

    outside = _question_base("N6_OUTSIDE_HYPOTHESIS_SPACE", "outside_space", two_regimes())
    open_space = _question_base("N7_OPEN_HYPOTHESIS_SPACE", "open", open_regimes())
    blind = _question_base("N8_INSTRUMENT_BLIND", "blind", blind_regimes())

    unadmitted = _complex_base("N9_UNADMITTED_FRESH_INSTANCES")
    unadmitted["fresh_instances"] = [
        {"instance_id": "fresh-a", "expected_plan": ["WRONG_PLAN"]},
        {"instance_id": "fresh-b", "expected_plan": ["WRONG_PLAN"]},
    ]

    return [
        read_only, ask, save, caller, raw, hidden, separation, dynamic,
        outside, open_space, blind, unadmitted,
    ]


def oracle_for(name: str) -> Callable[[tuple[str, ...]], str] | None:
    if name == "none":
        return None
    if name == "outside_space":
        return lambda _probe: "OUTSIDE_SPACE"
    if name == "open":
        return lambda _probe: "UNKNOWN"
    if name == "blind":
        return lambda _probe: "same"
    if name == "latest_email":
        table = {_key(P1): "latest_email", _key(P2): "v2",
                 _key(P3): "latest_email", _key(G1): "latest_email"}
        return lambda probe: table.get(_key(probe), "UNKNOWN")
    raise ValueError(f"unknown frozen oracle {name!r}")


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_ref() -> str:
    return secrets.token_hex(8)


def _truth() -> dict[str, Any]:
    return {
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "written_to_weights": False,
        "own_weights": False,
        "carrier_qualified": False,
        "execution_authorized": False,
        "patch_published": False,
        "independent_attestation": False,
        "independent_cloud_verifier": False,
        "gui_dom_oracle": False,
        "hardest_open_nov_2026_score": "NO_SCORE",
        "acceptance_credit_delta": 0,
        "section_6": "NOT_DONE",
        "truth_achieved": False,
        "completion_claim": False,
    }


def evaluate(
    *,
    store_path: str | Path = gate.STORE_PATH,
    write_store: bool = False,
    prereg_path: str | Path = PREREG_PATH,
    verifier_path: str | Path = VERIFIER_PATH,
    receipt_path: str | Path | None = None,
    attestation_path: str | Path = ATTESTATION_PATH,
) -> dict[str, Any]:
    """Run all frozen cases, store one admitted rule, and optionally recheck."""
    case_bundle = frozen_cases()
    decisions: list[dict[str, Any]] = []
    for case in case_bundle:
        decision = gate.assess(case, oracle=oracle_for(str(case.get("oracle_name") or "none")),
                               store_path=store_path, write_store=False)
        decisions.append(decision)
    matched = sum(1 for row in decisions if row.get("decision") == EXPECTED.get(row.get("case_id")))
    if matched != len(EXPECTED):
        bad = [{"case_id": r.get("case_id"), "decision": r.get("decision"),
                "expected": EXPECTED.get(r.get("case_id"))} for r in decisions
               if r.get("decision") != EXPECTED.get(r.get("case_id"))]
        raise RuntimeError(f"frozen expected-decision mismatch: {bad}")

    save_case = next(case for case in case_bundle if case["case_id"] == "A3_SAVE_ABSTRACT")
    store_action = gate.assess(save_case, oracle=None, store_path=store_path,
                               write_store=write_store)
    if store_action.get("decision") != gate.SAVE_ADMITTED:
        raise RuntimeError(f"store action did not admit: {store_action.get('decision')}")

    editability: dict[str, Any]
    store_path_obj = Path(store_path)
    if write_store and store_path_obj.is_file():
        before = gate.store_status(store_path_obj)
        original = store_path_obj.read_bytes()
        store_path_obj.unlink()
        missing = gate.store_status(store_path_obj)
        store_path_obj.write_bytes(original)
        after = gate.store_status(store_path_obj)
        editability = {
            "before": before,
            "missing": missing,
            "after": after,
            "removal_refused": missing.get("status") == "STORE_MISSING__REFUSE",
            "restore_verified": after.get("status") == "PASS__STORE_VERIFIED",
            "restart_digest_matches": before.get("digest") == after.get("digest"),
        }
    else:
        editability = {
            "status": "NOT_RUN__NO_STORE_WRITTEN",
            "removal_refused": False,
            "restore_verified": False,
            "restart_digest_matches": False,
        }

    forbidden_store_fields = gate.forbidden_fields(store_action.get("rule") or {})
    negative_refusals = sum(1 for row in decisions
                            if row.get("case_id") not in ADMITTED_IDS
                            and str(row.get("decision") or "").startswith("REFUSED"))
    question_probes = sum(int(row.get("probes_executed") or 0) for row in decisions)
    store_write_count = 1 if store_action.get("store_write") else 0
    counts = {
        "case_count": len(case_bundle),
        "admitted_arms": len(ADMITTED_IDS),
        "negative_arms": len(case_bundle) - len(ADMITTED_IDS),
        "expected_decision_matches": matched,
        "negative_refusals": negative_refusals,
        "question_probes": question_probes,
        "store_write_count": store_write_count,
        "forbidden_store_fields": forbidden_store_fields,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "verifier_processes": 1 if receipt_path is not None else 0,
    }
    refs = {
        "producer_run_ref": _run_ref(),
        "decision_run_ref": _run_ref(),
        "store_run_ref": _run_ref(),
        "restart_run_ref": _run_ref(),
    }
    refs["run_refs_distinct"] = len(set(refs.values())) == len(refs)
    payload = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prereg_sha256": _sha256_file(Path(prereg_path)),
        "verifier_script_sha256": _sha256_file(Path(verifier_path)),
        "case_bundle": case_bundle,
        "decisions": decisions,
        "store_action": {
            "decision": store_action.get("decision"),
            "reason": store_action.get("reason"),
            "store_write": store_action.get("store_write"),
            "store": store_action.get("store"),
            "rule": store_action.get("rule"),
        },
        "store_editability": editability,
        "counts": counts,
        "run_refs": refs,
        "truth": _truth(),
        "physical_cost_blockers_logged_once": [
            "Docker/Podman/Harbor unavailable",
            "Python 3.12 unavailable",
            "disposable independent VM unavailable",
            "OSWorld 2.1 assets unavailable",
            "GPU/torch/open-weight training substrate unavailable",
            "paid multi-run benchmark infrastructure not attempted",
        ],
        "external_sources_build_time_only": True,
        "frontier_score_claim": False,
    }
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "receipt_sha256": gate.digest(payload),
        "canonical_payload": payload,
        "independent_attestation": False,
    }

    if receipt_path is not None:
        out = Path(receipt_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        attestation = Path(attestation_path)
        attestation.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-I", str(Path(verifier_path)),
               "--receipt", str(out), "--prereg", str(Path(prereg_path)),
               "--store", str(store_path_obj), "--out", str(attestation)]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                              check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"separate local recheck failed: {proc.stdout}\n{proc.stderr}")
        recheck = json.loads(attestation.read_text(encoding="utf-8"))
        if recheck.get("status") != "LOCAL_DIFFERENT_CODE_RECHECK_PASS__NOT_INDEPENDENT_ATTESTATION":
            raise RuntimeError(f"separate local recheck refused: {recheck}")
        before_digest = (editability.get("before") or {}).get("digest")
        if (recheck.get("store_digest") != before_digest
                or recheck.get("recomputed_receipt_sha256") != receipt.get("receipt_sha256")):
            raise RuntimeError("separate local recheck digest did not match the producer")
        receipt["separate_local_recheck"] = recheck
        receipt["verifier_run_refs"] = [recheck.get("run_ref")]
        # receipt_sha256 covers canonical_payload, which is deliberately unchanged
        # after the separate recheck; the attestation is outside that hash.
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    receipt = evaluate(receipt_path=RECEIPT_PATH, attestation_path=ATTESTATION_PATH,
                       write_store=True)
    payload = receipt["canonical_payload"]
    print("GOAL_DIRECTED_GATE_PASS__PROGRESS_ONLY")
    print(json.dumps({
        "cases": payload["counts"]["case_count"],
        "expected_decision_matches": payload["counts"]["expected_decision_matches"],
        "negative_refusals": payload["counts"]["negative_refusals"],
        "question_probes": payload["counts"]["question_probes"],
        "store_write_count": payload["counts"]["store_write_count"],
        "separate_local_recheck": (receipt.get("separate_local_recheck") or {}).get("status"),
        "section_6": payload["truth"]["section_6"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
