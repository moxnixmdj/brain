from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
from pathlib import Path

from canonical.runtime.terminal_dependency_falsifier_v1 import (
    FAMILIES,
    falsify_graph,
)
from canonical.runtime.terminal_dependency_graph_guard_v1 import SCHEMA


def blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def graph(root: Path) -> dict:
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
                "attack_families": [
                    "COMPOSITION_MISMATCH",
                    "IMPLEMENTATION_REFINEMENT_MISMATCH",
                ],
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
                "attack_families": [
                    "VERSION_DRIFT",
                    "IMPLEMENTATION_REFINEMENT_MISMATCH",
                ],
                "note": "fixture route",
            },
        ],
        "terminal_closure": False,
        "terminal_credit_delta": 0,
    }


def test_unbound_verified_live_refinement_mismatch_becomes_obligation(tmp_path):
    raw = graph(tmp_path)
    raw["nodes"][1]["lifecycle"] = "VERIFIED_LIVE"
    raw["nodes"][1]["creditable"] = True
    out = falsify_graph(raw, repo_root=tmp_path, validate_structure=False)
    matches = [
        row for row in out["obligations"]
        if row["node_id"] == "route"
        and row["family"] == "IMPLEMENTATION_REFINEMENT_MISMATCH"
    ]
    assert matches
    assert matches[0]["status"] == "OPEN_COUNTEREXAMPLE_OBLIGATION"
    assert out["terminal_closure_proved"] is False


def test_irrelevant_statistical_family_is_not_invented(tmp_path):
    raw = graph(tmp_path)
    out = falsify_graph(raw, repo_root=tmp_path)
    route_families = {
        row["family"] for row in out["obligations"] if row["node_id"] == "route"
    }
    assert "ADAPTIVE_SELECTION" not in route_families
    assert "PROXY_MEASUREMENT" not in route_families


def test_unknown_applicability_is_explicit_not_pass(tmp_path):
    raw = graph(tmp_path)
    raw["nodes"][0]["attack_families"] = []
    out = falsify_graph(raw, repo_root=tmp_path)
    row = next(x for x in out["obligations"] if x["node_id"] == "FRAMEWORK")
    assert row["family"] == "UNDECLARED_APPLICABILITY"
    assert row["status"] == "APPLICABILITY_UNRESOLVED"
    assert out["terminal_closure_proved"] is False


def test_unsupported_family_fails_closed(tmp_path):
    raw = graph(tmp_path)
    raw["nodes"][0]["attack_families"] = ["MAGIC"]
    out = falsify_graph(raw, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ATTACK_FAMILY_UNSUPPORTED"


def test_falsifier_never_claims_open_world_closure(tmp_path):
    raw = graph(tmp_path)
    for node in raw["nodes"]:
        if node["kind"] == "LEAF":
            node["status"] = "PROVED"
        else:
            node["lifecycle"] = "REFINEMENT_VERIFIED"
            node["refinement"]["status"] = "PROVED"
            node["live_authority_status"] = "PROVED"
    out = falsify_graph(raw, repo_root=tmp_path, validate_structure=False)
    assert out["pass"] is True
    assert out["terminal_closure_proved"] is False
    assert out["generator_coverage_proved"] is False
    assert out["terminal_credit_delta"] == 0


def test_family_registry_is_exact_and_nonempty():
    assert "IMPLEMENTATION_REFINEMENT_MISMATCH" in FAMILIES
    assert "NEGATION" in FAMILIES
    assert "CAUSAL_CONFOUNDING" in FAMILIES
