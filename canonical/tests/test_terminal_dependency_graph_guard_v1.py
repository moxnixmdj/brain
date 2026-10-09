from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path

from canonical.runtime.terminal_dependency_graph_guard_v1 import (
    SCHEMA,
    validate_graph,
)


def blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def base_graph(root: Path) -> dict:
    impl = write(root, "canonical/runtime/route.py", "def run(x):\n    return x\n")
    cert = write(root, "canonical/governance/cert.json", '{"schema":"CERT"}\n')
    return {
        "schema": SCHEMA,
        "date": "2026-10-09",
        "terminal_objective": "MISSION",
        "nodes": [
            {
                "id": "FRAMEWORK",
                "kind": "LEAF",
                "status": "UNRESOLVED",
                "attack_families": ["COMPOSITION_MISMATCH"],
                "note": "fixture",
            },
            {
                "id": "route",
                "kind": "ROUTE",
                "lifecycle": "IMPLEMENTED",
                "creditable": False,
                "terminal_authority": False,
                "implementation": {
                    "path": "canonical/runtime/route.py",
                    "git_blob_sha": blob(impl),
                },
                "refinement": {
                    "status": "UNRESOLVED",
                    "certificate": {
                        "path": "canonical/governance/cert.json",
                        "git_blob_sha": blob(cert),
                    },
                    "verification_receipt": None,
                },
                "live_authority_status": "UNRESOLVED",
                "attack_families": ["IMPLEMENTATION_REFINEMENT_MISMATCH"],
                "note": "fixture route",
            },
        ],
        "terminal_closure": False,
        "terminal_credit_delta": 0,
    }


def test_unknown_leaf_status_fails_closed(tmp_path):
    graph = base_graph(tmp_path)
    graph["nodes"][0]["status"] = "PROBABLY_FINE"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "LEAF_STATUS_INVALID"


def test_noncreditable_implemented_route_is_allowed_but_unresolved(tmp_path):
    graph = base_graph(tmp_path)
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["route_states"]["route"] == "IMPLEMENTED"
    assert "route::EXECUTABLE_REFINEMENT" in out["unresolved"]
    assert out["graph_completeness_proved"] is False
    assert out["terminal_credit_delta"] == 0


def test_creditable_route_cannot_stop_at_implemented(tmp_path):
    graph = base_graph(tmp_path)
    graph["nodes"][1]["creditable"] = True
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "CREDITABLE_ROUTE_REFINEMENT_REQUIRED"


def test_refinement_verified_requires_verified_receipt(tmp_path):
    graph = base_graph(tmp_path)
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    route["refinement"]["verification_receipt"] = None
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "route_REFINEMENT_RECEIPT_BINDING_INVALID"


def test_verified_receipt_must_say_refinement_verified_true(tmp_path):
    graph = base_graph(tmp_path)
    receipt = write(
        tmp_path,
        "canonical/verification/refinement.json",
        json.dumps({"subject_id": "route", "refinement_verified": False}) + "\n",
    )
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    route["refinement"]["verification_receipt"] = {
        "path": "canonical/verification/refinement.json",
        "git_blob_sha": blob(receipt),
    }
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "REFINEMENT_RECEIPT_NOT_VERIFIED"


def test_stale_refinement_receipt_fails_closed(tmp_path):
    graph = base_graph(tmp_path)
    receipt = write(
        tmp_path,
        "canonical/verification/refinement.json",
        json.dumps({"subject_id": "route", "refinement_verified": True}) + "\n",
    )
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    route["refinement"]["verification_receipt"] = {
        "path": "canonical/verification/refinement.json",
        "git_blob_sha": "0" * 40,
    }
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "route_REFINEMENT_RECEIPT_BLOB_DRIFT"


def test_verified_live_requires_live_authority(tmp_path):
    graph = base_graph(tmp_path)
    receipt = write(
        tmp_path,
        "canonical/verification/refinement.json",
        json.dumps({"subject_id": "route", "refinement_verified": True}) + "\n",
    )
    route = graph["nodes"][1]
    route["lifecycle"] = "VERIFIED_LIVE"
    route["creditable"] = True
    route["refinement"]["status"] = "PROVED"
    route["refinement"]["verification_receipt"] = {
        "path": "canonical/verification/refinement.json",
        "git_blob_sha": blob(receipt),
    }
    route["live_authority_status"] = "UNRESOLVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "VERIFIED_LIVE_AUTHORITY_UNPROVED"


def test_verified_live_route_passes_only_with_proved_refinement_and_live_authority(tmp_path):
    graph = base_graph(tmp_path)
    receipt = write(
        tmp_path,
        "canonical/verification/refinement.json",
        json.dumps({"subject_id": "route", "refinement_verified": True}) + "\n",
    )
    route = graph["nodes"][1]
    route["lifecycle"] = "VERIFIED_LIVE"
    route["creditable"] = True
    route["refinement"]["status"] = "PROVED"
    route["refinement"]["verification_receipt"] = {
        "path": "canonical/verification/refinement.json",
        "git_blob_sha": blob(receipt),
    }
    route["live_authority_status"] = "PROVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["route_states"]["route"] == "VERIFIED_LIVE"
    assert out["terminal_authority"] is False


def test_terminal_closure_cannot_hide_unresolved_leaves(tmp_path):
    graph = base_graph(tmp_path)
    graph["terminal_closure"] = True
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "TERMINAL_CLOSURE_WITH_UNRESOLVED_LEAVES"


def test_empty_attack_family_set_is_explicitly_unresolved(tmp_path):
    graph = base_graph(tmp_path)
    graph["nodes"][0]["status"] = "PROVED"
    graph["nodes"][0]["attack_families"] = []
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert "FRAMEWORK::ATTACK_APPLICABILITY" in out["unresolved"]


def test_terminal_closure_rejects_unknown_attack_applicability(tmp_path):
    graph = base_graph(tmp_path)
    graph["nodes"][0]["status"] = "PROVED"
    graph["nodes"][0]["attack_families"] = []
    graph["nodes"][1]["refinement"]["status"] = "PROVED"
    graph["nodes"][1]["live_authority_status"] = "PROVED"
    graph["nodes"][1]["attack_families"] = ["VERSION_DRIFT"]
    graph["terminal_closure"] = True
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "TERMINAL_CLOSURE_WITH_UNRESOLVED_LEAVES"
    assert "FRAMEWORK::ATTACK_APPLICABILITY" in out["unresolved"]
