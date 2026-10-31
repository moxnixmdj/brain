#!/usr/bin/env python3
"""Inspect final SWE composition declarations, without claiming workflow delivery.

Reuse the declarations-only boundary of software_hardcore_swe_supercomposer_v1:
producer availability and static preflight are not execution or acceptance of
an advertised multi-stage workflow. No capability authority is created here.
"""
from __future__ import annotations

import pathlib
from typing import Any

from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_HARDCORE_FINAL_SUPERCOMPOSER_V1"
CAPABILITY_ID = "software.hardcore.final.supercomposer.v1"
PROVIDES = ["software.hardcore.final.verified", "software.hardcore.final.synthesis.verified"]
REQUIRES: list[str] = [
    "software.hardcore.swe.composed.verified", "software.hardcore.swe.fullstack.verified",
    "software.architect.synthesize.cegis.verified", "software.patch.synthesize.cegis.proven",
    "software.synthesis.grid_program.exact",
]
REPO = pathlib.Path(__file__).resolve().parents[3]


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import (
        analyze_python_static_soundness, load_active_bound_registry,
    )

    repo = pathlib.Path(root).resolve()
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_hardcore_final_supercomposer.json")
    reg = load_active_bound_registry(repo)
    static_check = None
    if args.get("source_root"):
        source = (repo / str(args["source_root"])).resolve()
        if source != repo and repo not in source.parents:
            raise ValueError("PATH_OUTSIDE_REPOSITORY")
        if not source.exists():
            raise ValueError("SOURCE_ROOT_MISSING")
        static_check = analyze_python_static_soundness(repo, source)
    all_provides = {p for row in reg["capabilities"].values() for p in row.get("provides", [])}
    found = {required: required in all_provides for required in REQUIRES}
    producers = [
        "software.hardcore.swe.supercomposer.v1", "software.patch.synthesize.cegis.z3.v1",
        "software.synthesis.grid_induction.v1", "software.hardcore.kernel.orchestrate.v1",
    ]
    producer_found = {cid: cid in reg["capabilities"] for cid in producers}
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_hardcore_final_supercomposer_v1",
        "required_tokens": REQUIRES, "found": found, "producers": producer_found,
        "declarations_resolve": all(found.values()) and all(producer_found.values()),
        "workflow_executed": False, "verification_scope": "DECLARATIONS_ONLY",
        "status": "OPEN__DECLARATIONS_ONLY_NOT_SOFTWARE_DELIVERY",
        "pass": False, "verified": False, "static_soundness": static_check,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, artifact)
