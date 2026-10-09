from __future__ import annotations

from pathlib import Path

from canonical.runtime.executable_refinement_verifier_v1 import git_blob_sha
from canonical.runtime.terminal_dependency_graph_guard_v1 import SCHEMA, verify_graph

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "canonical/governance/ROUTER_DEPLOYMENT_CANARY_EXECUTABLE_REFINEMENT_20261009_V1.json"
ROUTE = ROOT / "canonical/runtime/router_deployment_canary_v1.py"


def graph():
    return {
        "schema": SCHEMA,
        "date": "2026-10-09",
        "terminal_objective": "TEST",
        "claims_complete": False,
        "leaves": [
            {
                "id": "canary-implementation",
                "status": "PROVED",
                "binding": {
                    "path": str(ROUTE.relative_to(ROOT)),
                    "git_blob_sha": git_blob_sha(ROUTE),
                },
            },
            {
                "id": "canary-refinement",
                "status": "UNRESOLVED",
                "binding": {
                    "path": str(CERT.relative_to(ROOT)),
                    "git_blob_sha": git_blob_sha(CERT),
                },
            },
        ],
        "routes": [
            {
                "id": "router-deployment-canary",
                "lifecycle": "IMPLEMENTED",
                "creditable": False,
                "terminal_load_bearing": False,
                "dependency_leaf_ids": ["canary-implementation", "canary-refinement"],
                "executable_refinement_leaf_id": "canary-refinement",
                "deployment_identity_leaf_id": None,
            }
        ],
        "terminal_credit_delta": 0,
    }


def test_unknown_leaf_status_rejected():
    raw = graph()
    raw["leaves"][0]["status"] = "MAGIC"
    out = verify_graph(raw, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "LEAF_STATUS_INVALID"


def test_verified_live_without_refinement_dependency_rejected():
    raw = graph()
    raw["routes"][0]["lifecycle"] = "VERIFIED_LIVE"
    raw["routes"][0]["creditable"] = True
    raw["routes"][0]["executable_refinement_leaf_id"] = None
    out = verify_graph(raw, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "REFINEMENT_DEPENDENCY_REQUIRED"


def test_structural_canary_certificate_cannot_be_promoted_to_refinement_verified():
    raw = graph()
    raw["routes"][0]["lifecycle"] = "REFINEMENT_VERIFIED"
    raw["leaves"][1]["status"] = "PROVED"
    out = verify_graph(raw, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "REFINEMENT_CERTIFICATE_NOT_MECHANICALLY_VERIFIED"


def test_stale_refinement_binding_rejected():
    raw = graph()
    raw["leaves"][1]["binding"]["git_blob_sha"] = "0" * 40
    out = verify_graph(raw, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "LEAF_BLOB_DRIFT"


def test_implemented_without_refinement_remains_valid_non_live_state():
    out = verify_graph(graph(), repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["claims_complete"] is False
    assert out["terminal_credit_delta"] == 0


def test_graph_cannot_self_claim_completeness():
    raw = graph()
    raw["claims_complete"] = True
    out = verify_graph(raw, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "GRAPH_MUST_NOT_SELF_CLAIM_COMPLETENESS"
