from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime import observable_policy_cover_executor_v1 as cover_executor
from canonical.runtime import reached_escape_policy_cover_authority_bridge_v1 as bridge
from canonical.runtime import reached_escape_state_kernel_v1 as kernel


def _blob(raw: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob " + str(len(raw)).encode() + b"\0" + raw)
    return h.hexdigest()


def _receipt(**extra):
    return {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        **extra,
    }


def policy(pid, worlds, cost=1):
    return {
        "policy_id": pid,
        "adequate_world_ids": list(worlds),
        "cost_units": cost,
        "adequacy_receipt": _receipt(
            policy_id=pid,
            policy_adequate_on_every_listed_world=True,
            policy_safe_on_every_listed_world=True,
            hard_constraint_scope_complete=True,
            brain_owned=True,
            deployed_exact=True,
            resource_bound_proved=True,
        ),
    }


def discriminator(did, outcomes, cost=1):
    return {
        "discriminator_id": did,
        "outcomes": dict(outcomes),
        "cost_units": cost,
        "truth_safety_receipt": _receipt(
            discriminator_id=did,
            outcome_map_complete=True,
            truth_preserving=True,
            safe_on_entire_state=True,
            resource_bound_proved=True,
        ),
    }


def problem(*, policies, discriminators=()):
    return {
        "state_id": "S",
        "worlds": [{"world_id": "r1"}, {"world_id": "r2"}],
        "world_set_completeness_receipt": _receipt(
            policy_relevant_world_set_complete=True,
            state_id="S",
        ),
        "policies": list(policies),
        "discriminators": list(discriminators),
    }


def state_from_problem(p):
    return {
        "schema": kernel.STATE_SCHEMA,
        "state_id": p["state_id"],
        "regions": [{"region_id": row["world_id"]} for row in p["worlds"]],
        "policies": [
            {
                "policy_id": row["policy_id"],
                "adequate_region_ids": list(row["adequate_world_ids"]),
                # Deliberately untrusted caller flags. Bridge/V2 must not rely on them.
                "authenticated": True,
                "safe": True,
            }
            for row in p["policies"]
        ],
        "discriminators": [
            {
                "discriminator_id": row["discriminator_id"],
                "outcomes": dict(row["outcomes"]),
                "authenticated": True,
                "safe": True,
                "truthful": True,
                "complete": True,
            }
            for row in p.get("discriminators", [])
        ],
    }


def _write_json(root: Path, rel: str, doc: dict) -> tuple[str, str]:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return rel, _blob(raw)


def bound_cover(root: Path, p: dict):
    problem_sha = cover_executor._digest(p)
    receipt = {
        "schema": cover_executor.COVER_BINDING_SCHEMA,
        "state_id": p["state_id"],
        "problem_sha256": problem_sha,
        "cover_inputs_authenticated": True,
        "policy_relevant_world_set_completeness_authenticated": True,
        "all_policy_adequacy_receipts_authenticated": True,
        "all_discriminator_truth_safety_receipts_authenticated": True,
        "brain_owned_and_resource_bounds_authenticated": True,
    }
    rpath, rsha = _write_json(
        root,
        "canonical/governance/test_policy_cover_binding.json",
        receipt,
    )
    verification = {
        "schema": cover_executor.COVER_BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rsha,
        "state_id": p["state_id"],
        "problem_sha256": problem_sha,
        "pass": True,
        "independent_verified": True,
        "input_authentication_verified": True,
        "policy_adequacy_authentication_verified": True,
        "discriminator_semantics_authentication_verified": True,
        "independent_verifier_id": "TEST_POLICY_COVER_INDEPENDENT_VERIFIER",
    }
    vpath, vsha = _write_json(
        root,
        "canonical/verification/test_policy_cover_binding_verify.json",
        verification,
    )
    return {
        "receipt": {"path": rpath, "git_blob_sha": rsha},
        "verification": {"path": vpath, "git_blob_sha": vsha},
    }


def test_positive_authenticated_split_cover_enters_v2():
    p = problem(
        policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
        discriminators=[discriminator("d", {"r1": "A", "r2": "B"})],
    )
    with TemporaryDirectory() as td:
        root = Path(td)
        binding = bound_cover(root, p)
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": binding,
            },
            repo_root=root,
        )
    assert out["pass"] is True, out
    assert out["policy_cover_authority_bound"] is True
    assert out["truth_authority_bound"] is True
    assert out["resource_admissibility_proved"] is True
    assert out["bounded_reached_state_totality_proved"] is True
    assert out["kernel_result"]["status"] == "STRICT_PROGRESS_WITH_DISCRIMINATOR"
    assert out["global_escape_progress_totality_proved"] is False
    assert out["terminal_authority"] is False


def test_positive_authenticated_common_policy_enters_v2_terminal_cell():
    p = problem(policies=[policy("p_all", ("r1", "r2"), cost=3)])
    with TemporaryDirectory() as td:
        root = Path(td)
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": bound_cover(root, p),
            },
            repo_root=root,
        )
    assert out["pass"] is True, out
    assert out["kernel_result"]["status"] == "TERMINALIZE_WITH_COMMON_POLICY"
    assert out["policy_cover_totality"]["policy_safety_coverage_proved"] is True
    assert out["policy_cover_minimum_worst_case_resource_bound_units"] == 3.0


def test_missing_binding_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    out = bridge.construct(
        {"state": state_from_problem(p), "policy_cover_problem": p}
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REACHED_ESCAPE_POLICY_COVER_AUTHORITY"
    assert "POLICY_COVER_BINDING_REQUIRED" in out["reason"]


def test_state_problem_projection_mismatch_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    s = state_from_problem(p)
    s["policies"][0]["adequate_region_ids"] = ["r1"]
    with TemporaryDirectory() as td:
        root = Path(td)
        out = bridge.construct(
            {
                "state": s,
                "policy_cover_problem": p,
                "cover_binding": bound_cover(root, p),
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "STATE_POLICY_COVER_PROJECTION_MISMATCH" in out["reason"]


def test_adequate_but_unsafe_policy_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    p["policies"][0]["adequacy_receipt"]["policy_safe_on_every_listed_world"] = False
    with TemporaryDirectory() as td:
        root = Path(td)
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": bound_cover(root, p),
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "POLICY_AUTHORITY_PREMISE_UNPROVED" in out["reason"]


def test_incomplete_hard_constraint_scope_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    p["policies"][0]["adequacy_receipt"]["hard_constraint_scope_complete"] = False
    with TemporaryDirectory() as td:
        root = Path(td)
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": bound_cover(root, p),
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "POLICY_AUTHORITY_PREMISE_UNPROVED" in out["reason"]


def test_nonfinite_resource_cost_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"), cost=float("inf"))])
    out = bridge.construct(
        {
            "state": state_from_problem(p),
            "policy_cover_problem": p,
            "cover_binding": {},
        }
    )
    assert out["pass"] is False
    assert "POLICY_COST" in out["reason"]


def test_cover_binding_blob_drift_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    with TemporaryDirectory() as td:
        root = Path(td)
        binding = bound_cover(root, p)
        binding["receipt"]["git_blob_sha"] = "0" * 40
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": binding,
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "POLICY_COVER_BINDING_NOT_AUTHENTICATED" in out["reason"]


def test_verification_subject_mismatch_fails_closed():
    p = problem(policies=[policy("p_all", ("r1", "r2"))])
    with TemporaryDirectory() as td:
        root = Path(td)
        binding = bound_cover(root, p)
        vpath = root / binding["verification"]["path"]
        doc = json.loads(vpath.read_text())
        doc["subject_git_blob_sha"] = "1" * 40
        _, new_sha = _write_json(root, binding["verification"]["path"], doc)
        binding["verification"]["git_blob_sha"] = new_sha
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": binding,
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "POLICY_COVER_BINDING_NOT_AUTHENTICATED" in out["reason"]


def test_unresolved_cover_is_not_promoted_to_repair_or_totality():
    p = problem(
        policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
        discriminators=[],
    )
    with TemporaryDirectory() as td:
        root = Path(td)
        out = bridge.construct(
            {
                "state": state_from_problem(p),
                "policy_cover_problem": p,
                "cover_binding": bound_cover(root, p),
            },
            repo_root=root,
        )
    assert out["pass"] is False
    assert "POLICY_COVER_TOTALITY_NOT_PROVED" in out["reason"]
    assert out["global_escape_progress_totality_proved"] is False
    assert out["terminal_credit_delta"] == 0
