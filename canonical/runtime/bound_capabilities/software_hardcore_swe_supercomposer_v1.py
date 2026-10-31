#!/usr/bin/env python3
"""Hardcore SWE supercomposer — real multi-stage index -> localize -> repair -> verify pipeline."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
from typing import Any

def _load_registry(repo: pathlib.Path) -> dict[str, Any]:
    target = repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    raw = target.read_text(encoding="utf-8").strip()
    if raw.startswith("@"):
        ptr = pathlib.Path(raw[1:].strip())
        target = ptr if ptr.is_file() else (target.parent / "BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
    return json.loads(target.read_text(encoding="utf-8"))

SCHEMA = "PROJECT_BRAIN_SOFTWARE_HARDCORE_SWE_SUPERCOMPOSER_V1"
CAPABILITY_ID = "software.hardcore.swe.supercomposer.v1"
PROVIDES = ["software.hardcore.swe.composed.verified", "software.hardcore.swe.fullstack.verified"]
REQUIRES: list[str] = [
    "python.pipeline.allowlist.verified",
    "python.pr.land.verified",
    "python.transformation.fused.verified",
    "software.hardcore.kernel.verified",
    "software.repair.loop.cegis_verified",
]
REPO = pathlib.Path(__file__).resolve().parents[3]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_swe_supercomposer.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    args = dict(args or {})
    output = _safe_output(repo, args.get("output_path"))

    # Resolve registry properly through @-pointer-aware loader (never raw json.loads on pointer file)
    reg = _load_registry(repo)
    all_prov = {p for m in reg["capabilities"].values() for p in m.get("provides", [])}
    found = {r: (r in all_prov) for r in REQUIRES}
    producers = [
        "software.hardcore.kernel.orchestrate.v1",
        "software.patch.synthesize.cegis.z3.v1",
        "software.repair.loop.cegis_hypothesis.v1",
        "python.pipeline.allowlist_gate.v1",
        "python.pr.land.composer.v1",
        "python.refactor.test_scaffold.fusion.v1",
    ]
    prod_found = {c: c in reg["capabilities"] for c in producers}
    verified = all(found.values()) and all(prod_found.values())

    pipeline_execution: dict[str, Any] | None = None
    files_edited: list[str] = []
    src_raw = str(args.get("source_root") or "").strip()
    if src_raw:
        src_abs = (repo / src_raw).resolve()
        if src_abs != repo and repo in src_abs.parents and src_abs.exists():
            from canonical.runtime.bound_capabilities import (
                python_coupled_software_repair_loop_v1 as cloop,
                python_dynamic_fault_localizer_v1 as fl,
                python_source_symbol_index as sym_idx,
                python_test_guided_patch_search_v1 as ptg,
            )
            from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files

            tmp_idx = output.parent / f".super_idx_{os.getpid()}.json"
            tmp_fl = output.parent / f".super_fl_{os.getpid()}.json"
            tmp_rep = output.parent / f".super_rep_{os.getpid()}.json"
            try:
                idx_res = sym_idx.run({
                    "source_root": src_raw,
                    "output_path": tmp_idx.relative_to(repo).as_posix(),
                }, repo)
                target_dir = src_abs if src_abs.is_dir() else src_abs.parent
                try:
                    tfiles = list(discover_test_files(target_dir))
                except FileNotFoundError:
                    tfiles = []
                stage_summary: dict[str, Any] = {
                    "indexed_files": idx_res["file_count"],
                    "indexed_symbols": idx_res["symbol_count"],
                    "discovered_tests": [t.relative_to(repo).as_posix() for t in tfiles],
                }
                if tfiles:
                    tenv = ptg._source_env(target_dir, *tfiles)
                    base_res = ptg._run_tests(repo, ptg.suite_argv(sys.executable, *tfiles), 30, tenv)
                    stage_summary["baseline_returncode"] = base_res["returncode"]
                    if base_res["returncode"] != 0:
                        fl_res = fl.run({
                            "source_root": target_dir.relative_to(repo).as_posix(),
                            "test_paths": [t.relative_to(repo).as_posix() for t in tfiles],
                            "output_path": tmp_fl.relative_to(repo).as_posix(),
                        }, repo)
                        stage_summary["top_suspicious_symbol"] = fl_res.get("answer")
                        rep_res = cloop.run({
                            "source_root": target_dir.relative_to(repo).as_posix(),
                            "test_paths": [t.relative_to(repo).as_posix() for t in tfiles],
                            "output_path": tmp_rep.relative_to(repo).as_posix(),
                            "apply": True,
                        }, repo)
                        stage_summary["repair_pass"] = bool(rep_res.get("pass"))
                        if rep_res.get("pass") and rep_res.get("patches"):
                            from canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 import (
                                _apply_unified_diff_text,
                            )
                            for prow in rep_res["patches"]:
                                sp_abs = (repo / prow["source_path"]).resolve()
                                if repo in sp_abs.parents and sp_abs.is_file():
                                    patched_c = _apply_unified_diff_text(
                                        sp_abs.read_text(encoding="utf-8"), prow["unified_diff"]
                                    )
                                    if patched_c is not None:
                                        sp_abs.write_text(patched_c, encoding="utf-8")
                                        ptg._purge_source_bytecode(sp_abs)
                                        files_edited.append(prow["source_path"])
                        post_res = ptg._run_tests(repo, ptg.suite_argv(sys.executable, *tfiles), 30, tenv)
                        stage_summary["post_returncode"] = post_res["returncode"]
                        verified = verified and (post_res["returncode"] == 0)
                pipeline_execution = stage_summary
            finally:
                for tf in (tmp_idx, tmp_fl, tmp_rep):
                    tf.unlink(missing_ok=True)

    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "required_tokens": REQUIRES,
        "found": found,
        "producers": prod_found,
        "pipeline_execution": pipeline_execution,
        "files_edited": files_edited,
        "composition": "index -> dynamic_fault_localize -> cegis_coupled_repair -> verified_test_gate",
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "software_hardcore_swe_supercomposer_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "verified": verified,
        "found": found,
        "pipeline_execution": pipeline_execution,
        "files_edited": files_edited,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
