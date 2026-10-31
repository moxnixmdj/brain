#!/usr/bin/env python3
"""Task-bound compatibility adapter for bounded repair and candidate checking.

Reuse the existing provenance-guided repair -> isolated realization -> measured
acceptance controller, with concrete and Hypothesis checks of the SAME candidate.
No demo sources, registry-only proofs, or unchanged retries. ``budget`` bounds
controller dispatches; one bounded dispatch is sufficient because the controller
already searches candidates. Its own candidate limits still apply.

The legacy capability/effect identifiers are retained for compatibility; they
are not a claim of Z3-based patch synthesis, universal repair, or independent
semantic verification. Explicit source_root, task_text and contract_checks are
required. The old budget-only registry template now fails closed rather than
manufacturing success; this change does not claim natural-language reachability.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_LOOP_CEGIS_HYPOTHESIS_V1"
CAPABILITY_ID = "software.repair.loop.cegis_hypothesis.v1"
PROVIDES = ["software.repair.loop.cegis_verified", "software.repair.synthesis.triad_proven"]
REQUIRES = ["python.fault.localization.symbol_ranked"]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_repair_loop_cegis.json")).resolve()
    if p == root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    if p.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    return p


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    budget = args.get("budget", 3)
    if type(budget) is not int or not 1 <= budget <= 100:
        raise ValueError("BUDGET_MUST_BE_POSITIVE_BOUNDED_INTEGER")
    if not isinstance(args.get("source_root"), str) or not args["source_root"].strip():
        raise ValueError("SOURCE_ROOT_REQUIRED")
    if not isinstance(args.get("task_text"), str) or not args["task_text"].strip():
        raise ValueError("TASK_TEXT_REQUIRED")
    checks = args.get("contract_checks")
    if not isinstance(checks, list) or not checks or len(checks) > 16:
        raise ValueError("CONTRACT_CHECKS_REQUIRED")
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as controller

    # Unique scratch prevents collisions between concurrent calls and leaves no
    # stale intermediate report to be mistaken for evidence from this attempt.
    import tempfile
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".repair-check-", dir=output.parent) as td:
        forwarded = dict(args)
        forwarded.pop("budget", None)
        forwarded["output_path"] = str((pathlib.Path(td) / "measured.json").relative_to(repo))
        measured = controller.run(forwarded, repo)
    accepted = (
        measured.get("pass") is True
        and measured.get("acceptance_stop_authorized") is True
        and measured.get("source_restored") is True
        and measured.get("contract_checks_pass") is True
        and bool(measured.get("contract_checks"))
        and bool(measured.get("patches"))
    )
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "status": "PASS__TASK_BOUND_REPAIR_CHECKED" if accepted else "OPEN__TASK_BOUND_REPAIR_NOT_ACCEPTED",
        "pass": accepted, "verified": accepted, "iterations": 1, "budget": budget,
        "verification_mode": "REALIZED_PATCH_MEASURED_TESTS_AND_FINITE_CONTRACT_SAMPLES",
        "measurement": {k: v for k, v in measured.items()
                        if k not in {"output_path", "output_sha256", "output_verified"}},
        "source_restored": measured.get("source_restored") is True,
        "patches": measured.get("patches", []) if accepted else [],
        "independent_semantic_oracle_credit": False,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    with output.open("xb") as stream:
        stream.write(raw)
    return {**artifact, "adapter": "software_repair_loop_cegis_hypothesis_v1",
            "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "output_verified": accepted}
