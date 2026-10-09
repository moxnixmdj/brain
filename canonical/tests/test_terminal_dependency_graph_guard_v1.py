from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path

from canonical.runtime.executable_refinement_receipt_guard_v1 import (
    SCHEMA as REFINEMENT_RECEIPT_SCHEMA,
)
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
    cert = write(
        root,
        "canonical/governance/cert.json",
        json.dumps(
            {
                "subject_id": "route",
                "transition_refinement": {
                    "classes": [{"case_id": "PASS", "kind": "PASS"}]
                },
            }
        )
        + "\n",
    )
    return {
        "schema": SCHEMA,
        "date": "2026-10-09",
        "terminal_objective": "MISSION",
        "nodes": [
            {
                "id": "FRAMEWORK",
                "kind": "LEAF",
                "status": "UNRESOLVED",
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
                "note": "fixture route",
            },
        ],
        "terminal_closure": False,
        "terminal_credit_delta": 0,
    }


def make_receipt(root: Path, graph: dict, *, verified=True, subject="route") -> Path:
    proof = write(
        root,
        "canonical/verification/refinement-proof.json",
        json.dumps(
            {
                "pass": True,
                "subject_id": "route",
                "terminal_credit_delta": 0,
            }
        )
        + "\n",
    )
    route = graph["nodes"][1]
    cert_binding = route["refinement"]["certificate"]
    impl_binding = route["implementation"]
    return write(
        root,
        "canonical/verification/refinement.json",
        json.dumps(
            {
                "schema": REFINEMENT_RECEIPT_SCHEMA,
                "subject_id": subject,
                "refinement_verified": verified,
                "certificate_git_blob_sha": cert_binding["git_blob_sha"],
                "concrete_route_git_blob_sha": impl_binding["git_blob_sha"],
                "verification_method": "EXHAUSTIVE_FINITE_TRANSITION_CHECK",
                "verified_transition_case_ids": ["PASS"],
                "proof_artifact": {
                    "path": "canonical/verification/refinement-proof.json",
                    "git_blob_sha": blob(proof),
                },
                "verification_authority_mutated": False,
                "execution_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        )
        + "\n",
    )


def bind_receipt(graph: dict, receipt: Path) -> None:
    graph["nodes"][1]["refinement"]["verification_receipt"] = {
        "path": "canonical/verification/refinement.json",
        "git_blob_sha": blob(receipt),
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
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "route_REFINEMENT_RECEIPT_BINDING_INVALID"


def test_verified_receipt_must_be_semantically_verified(tmp_path):
    graph = base_graph(tmp_path)
    receipt = make_receipt(tmp_path, graph, verified=False)
    bind_receipt(graph, receipt)
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == (
        "REFINEMENT_RECEIPT_INVALID:RECEIPT_NOT_REFINEMENT_VERIFIED"
    )


def test_stale_refinement_receipt_fails_closed(tmp_path):
    graph = base_graph(tmp_path)
    receipt = make_receipt(tmp_path, graph)
    bind_receipt(graph, receipt)
    graph["nodes"][1]["refinement"]["verification_receipt"]["git_blob_sha"] = "0" * 40
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "route_REFINEMENT_RECEIPT_BLOB_DRIFT"


def test_verified_receipt_must_cover_full_declared_partition(tmp_path):
    graph = base_graph(tmp_path)
    receipt = make_receipt(tmp_path, graph)
    raw = json.loads(receipt.read_text(encoding="utf-8"))
    raw["verified_transition_case_ids"] = []
    receipt.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    bind_receipt(graph, receipt)
    route = graph["nodes"][1]
    route["lifecycle"] = "REFINEMENT_VERIFIED"
    route["refinement"]["status"] = "PROVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == (
        "REFINEMENT_RECEIPT_INVALID:RECEIPT_TRANSITION_COVERAGE_MISMATCH"
    )


def test_verified_live_requires_live_authority(tmp_path):
    graph = base_graph(tmp_path)
    receipt = make_receipt(tmp_path, graph)
    bind_receipt(graph, receipt)
    route = graph["nodes"][1]
    route["lifecycle"] = "VERIFIED_LIVE"
    route["creditable"] = True
    route["refinement"]["status"] = "PROVED"
    route["live_authority_status"] = "UNRESOLVED"
    out = validate_graph(graph, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "VERIFIED_LIVE_AUTHORITY_UNPROVED"


def test_verified_live_route_passes_only_with_proved_refinement_and_live_authority(
    tmp_path,
):
    graph = base_graph(tmp_path)
    receipt = make_receipt(tmp_path, graph)
    bind_receipt(graph, receipt)
    route = graph["nodes"][1]
    route["lifecycle"] = "VERIFIED_LIVE"
    route["creditable"] = True
    route["refinement"]["status"] = "PROVED"
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
