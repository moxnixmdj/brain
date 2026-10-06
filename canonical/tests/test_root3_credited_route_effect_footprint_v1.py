from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.root3_credited_route_effect_footprint_v1 import (
    EffectFootprintError,
    MANIFEST_SCHEMA,
    RECEIPT_SCHEMA,
    compile_footprint,
    git_blob_sha,
    sha256_json,
)


def _write(root: Path, rel: str, data: bytes) -> dict[str, str]:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": rel, "git_blob_sha": git_blob_sha(data)}


def _json_write(root: Path, rel: str, value: dict) -> dict[str, str]:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return _write(root, rel, data)


def _route(
    root: Path,
    *,
    route_id: str,
    route_rel: str,
    route_bytes: bytes,
    ontology: list[dict[str, str]],
    effects: list[str],
    scope_complete: bool = True,
):
    route_binding = _write(root, route_rel, route_bytes)
    route_bindings = [route_binding]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "route_id": route_id,
        "route_binding_sha256": sha256_json(route_bindings),
        "effect_ontology_binding_sha256": sha256_json(ontology),
        "scope_complete": scope_complete,
        "conservative": True,
        "fail_closed_outside_footprint": True,
        "independent_or_objective": True,
        "predicate_ids": ["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"],
        "material_effect_ids": effects,
    }
    receipt_binding = _json_write(
        root,
        f"receipts/{route_id}.json",
        receipt,
    )
    return {
        "route_id": route_id,
        "route_bindings": route_bindings,
        "reachability_receipt": receipt_binding,
    }


def _manifest(root: Path):
    ontology = [
        _write(root, "ontology/material.py", b"MATERIAL\n"),
        _write(root, "ontology/process.py", b"PROCESS\n"),
    ]
    routes = [
        _route(
            root,
            route_id="route.alpha",
            route_rel="routes/a.py",
            route_bytes=b"A\n",
            ontology=ontology,
            effects=["file.open_write", "network.connect"],
        ),
        _route(
            root,
            route_id="route.beta",
            route_rel="routes/b.py",
            route_bytes=b"B\n",
            ontology=ontology,
            effects=["network.connect", "process.READ_ONLY_DECLARED_QUERY"],
        ),
    ]
    return {
        "schema": MANIFEST_SCHEMA,
        "effect_ontology_bindings": ontology,
        "credited_routes": routes,
    }


def test_compiler_unions_overlapping_route_footprints(tmp_path: Path):
    manifest = _manifest(tmp_path)
    out = compile_footprint(manifest, repo_root=tmp_path)
    assert out["status"] == "PASS__CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILED"
    assert out["credited_route_count"] == 2
    assert out["material_effect_count"] == 3
    assert out["material_effect_ids"] == [
        "file.open_write",
        "network.connect",
        "process.READ_ONLY_DECLARED_QUERY",
    ]
    assert out["terminal_credit_delta"] == 0


def test_route_byte_drift_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    (tmp_path / "routes/a.py").write_bytes(b"DRIFT\n")
    with pytest.raises(EffectFootprintError, match="ROUTE_BINDING_BLOB_DRIFT"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_receipt_byte_drift_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    p = tmp_path / manifest["credited_routes"][0]["reachability_receipt"]["path"]
    p.write_text(p.read_text() + " ", encoding="utf-8")
    with pytest.raises(EffectFootprintError, match="REACHABILITY_RECEIPT_BLOB_DRIFT"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_incomplete_receipt_fails_closed(tmp_path: Path):
    ontology = [_write(tmp_path, "ontology/material.py", b"MATERIAL\n")]
    route = _route(
        tmp_path,
        route_id="route.bad",
        route_rel="routes/bad.py",
        route_bytes=b"BAD\n",
        ontology=ontology,
        effects=[],
        scope_complete=False,
    )
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "effect_ontology_bindings": ontology,
        "credited_routes": [route],
    }
    with pytest.raises(EffectFootprintError, match="SCOPE_COMPLETE_NOT_TRUE"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_receipt_route_binding_mismatch_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    p = tmp_path / manifest["credited_routes"][0]["reachability_receipt"]["path"]
    receipt = json.loads(p.read_text())
    receipt["route_binding_sha256"] = "0" * 64
    new_binding = _json_write(
        tmp_path,
        manifest["credited_routes"][0]["reachability_receipt"]["path"],
        receipt,
    )
    manifest["credited_routes"][0]["reachability_receipt"] = new_binding
    with pytest.raises(EffectFootprintError, match="RECEIPT_ROUTE_BINDING_MISMATCH"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_duplicate_route_id_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    manifest["credited_routes"][1]["route_id"] = manifest["credited_routes"][0]["route_id"]
    with pytest.raises(EffectFootprintError, match="DUPLICATE_ROUTE_ID"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_missing_predicate_scope_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    route = manifest["credited_routes"][0]
    p = tmp_path / route["reachability_receipt"]["path"]
    receipt = json.loads(p.read_text())
    receipt["predicate_ids"] = []
    route["reachability_receipt"] = _json_write(
        tmp_path,
        route["reachability_receipt"]["path"],
        receipt,
    )
    with pytest.raises(EffectFootprintError, match="PREDICATE_SCOPE_INCOMPLETE"):
        compile_footprint(manifest, repo_root=tmp_path)


def test_zero_effect_pure_route_is_allowed_with_complete_receipt(tmp_path: Path):
    ontology = [_write(tmp_path, "ontology/material.py", b"MATERIAL\n")]
    route = _route(
        tmp_path,
        route_id="route.pure",
        route_rel="routes/pure.py",
        route_bytes=b"PURE\n",
        ontology=ontology,
        effects=[],
    )
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "effect_ontology_bindings": ontology,
        "credited_routes": [route],
    }
    out = compile_footprint(manifest, repo_root=tmp_path)
    assert out["material_effect_ids"] == []
    assert out["material_effect_count"] == 0
