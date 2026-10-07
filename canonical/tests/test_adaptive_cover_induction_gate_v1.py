import hashlib
import json
from pathlib import Path

from canonical.runtime.adaptive_cover_induction_gate_v1 import (
    RECEIPT_SCHEMA,
    _state_contract,
    _top_contract,
    _sha256,
    evaluate,
)


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _write_receipt(
    root: Path,
    name: str,
    *,
    state_id: str,
    role: str,
    subject_sha256: str,
    **claims,
):
    path = root / name
    doc = {
        "schema": RECEIPT_SCHEMA,
        "state_id": state_id,
        "receipt_role": role,
        "subject_sha256": subject_sha256,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        **claims,
    }
    path.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": name, "git_blob_sha": _git_blob_sha(path)}


def _bind_receipts(p, root: Path):
    top = p["top_initialization"]
    top["receipt"] = _write_receipt(
        root,
        "top.json",
        state_id="__SCOPE__",
        role="TOP_INITIALIZATION",
        subject_sha256=_sha256(_top_contract(p["initial_state_id"], top)),
        alpha_total_on_scope=True,
        true_context_preserved_in_gamma_top=True,
    )
    for row in p["states"]:
        sid = row["state_id"]
        subject = _sha256(_state_contract(row))
        if row["terminal"]:
            row["terminal_adequacy_receipt"] = _write_receipt(
                root,
                f"{sid}-adequacy.json",
                state_id=sid,
                role="TERMINAL_ADEQUACY",
                subject_sha256=subject,
                policy_adequate_on_entire_concretization=True,
            )
            row["terminal_safety_receipt"] = _write_receipt(
                root,
                f"{sid}-safety.json",
                state_id=sid,
                role="TERMINAL_SAFETY",
                subject_sha256=subject,
                policy_safe_on_entire_concretization=True,
            )
        else:
            row["refinement_soundness_receipt"] = _write_receipt(
                root,
                f"{sid}-soundness.json",
                state_id=sid,
                role="REFINEMENT_SOUNDNESS",
                subject_sha256=subject,
                true_context_preserved_in_every_actual_successor=True,
            )
            row["refinement_safety_receipt"] = _write_receipt(
                root,
                f"{sid}-safety.json",
                state_id=sid,
                role="REFINEMENT_SAFETY",
                subject_sha256=subject,
                refinement_safe_on_entire_concretization=True,
            )
            row["outcome_completeness_receipt"] = _write_receipt(
                root,
                f"{sid}-outcomes.json",
                state_id=sid,
                role="OUTCOME_COMPLETENESS",
                subject_sha256=subject,
                outcome_model_complete=True,
            )
    return p


def base(root: Path):
    p = {
        "initial_state_id": "TOP",
        "top_initialization": {
            "alpha_total_on_scope": True,
            "true_context_preserved_in_gamma_top": True,
        },
        "states": [
            {
                "state_id": "TOP",
                "terminal": False,
                "refinement_policy_id": "q0",
                "outcomes": [
                    {
                        "outcome_id": "a",
                        "successor_state_id": "T0",
                        "cost_units": 2,
                    },
                    {
                        "outcome_id": "b",
                        "successor_state_id": "M",
                        "cost_units": 1,
                    },
                ],
            },
            {
                "state_id": "M",
                "terminal": False,
                "refinement_policy_id": "q1",
                "outcomes": [
                    {
                        "outcome_id": "done",
                        "successor_state_id": "T1",
                        "cost_units": 3,
                    }
                ],
            },
            {
                "state_id": "T0",
                "terminal": True,
                "terminal_policy_id": "p0",
                "terminal_cost_units": 5,
            },
            {
                "state_id": "T1",
                "terminal": True,
                "terminal_policy_id": "p1",
                "terminal_cost_units": 4,
            },
        ],
    }
    return _bind_receipts(p, root)


def test_mechanizes_rank_budget_and_cover(tmp_path):
    o = evaluate(base(tmp_path), repo_root=tmp_path)
    assert o["pass"]
    assert o["derived_rank"] == {"M": 1, "T0": 0, "T1": 0, "TOP": 2}
    assert o["initial_worst_case_resource_bound_units"] == 8.0
    assert o["receipt_binding"] == (
        "EXACT_REPOSITORY_GIT_BLOB_PLUS_EXACT_STATE_CONTRACT_SHA256"
    )
    assert not o["u_empty_authorized"]


def test_counterfeit_sha_shaped_receipt_fails(tmp_path):
    p = base(tmp_path)
    p["states"][2]["terminal_adequacy_receipt"] = {
        "path": "does-not-exist.json",
        "git_blob_sha": "a" * 40,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "policy_adequate_on_entire_concretization": True,
    }
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "TERMINAL_ADEQUACY_UNPROVED"


def test_byte_drift_fails(tmp_path):
    p = base(tmp_path)
    receipt = p["states"][2]["terminal_adequacy_receipt"]
    (tmp_path / receipt["path"]).write_text("{}\n", encoding="utf-8")
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "TERMINAL_ADEQUACY_UNPROVED"


def test_state_contract_drift_fails(tmp_path):
    p = base(tmp_path)
    p["states"][0]["outcomes"][0]["cost_units"] = 99
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "REFINEMENT_SOUNDNESS_UNPROVED"


def test_receipt_substitution_between_states_fails(tmp_path):
    p = base(tmp_path)
    p["states"][3]["terminal_adequacy_receipt"] = p["states"][2][
        "terminal_adequacy_receipt"
    ]
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "TERMINAL_ADEQUACY_UNPROVED"


def test_cycle_fails(tmp_path):
    p = base(tmp_path)
    p["states"][1]["outcomes"][0]["successor_state_id"] = "TOP"
    _bind_receipts(p, tmp_path)
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "WELL_FOUNDED_RANK_IMPOSSIBLE_CYCLE"


def test_outcome_completeness_is_load_bearing(tmp_path):
    p = base(tmp_path)
    path = tmp_path / p["states"][0]["outcome_completeness_receipt"]["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["outcome_model_complete"] = False
    path.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
    p["states"][0]["outcome_completeness_receipt"]["git_blob_sha"] = _git_blob_sha(path)
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "OUTCOME_COMPLETENESS_UNPROVED"


def test_terminal_safety_is_load_bearing(tmp_path):
    p = base(tmp_path)
    path = tmp_path / p["states"][2]["terminal_safety_receipt"]["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["policy_safe_on_entire_concretization"] = False
    path.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
    p["states"][2]["terminal_safety_receipt"]["git_blob_sha"] = _git_blob_sha(path)
    o = evaluate(p, repo_root=tmp_path)
    assert not o["pass"]
    assert o["reason"] == "TERMINAL_SAFETY_UNPROVED"
