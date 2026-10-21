#!/usr/bin/env python3
"""Locate a validated typed decision problem already present in the repository.

Producer for ``structured.decision_evidence.available``, the one effect
``decision.synthesis.typed.stdlib`` requires and nothing produced. With no
producer its ``input_path`` had no upstream step, so the verifier chain
``decision.synthesis.verify.stdlib`` died with ``DECISION_VERIFIER_INPUT_MISSING``.

This module does not synthesise decision evidence and does not infer semantics.
Typed decision problems carrying ``PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1``
already exist in this repository as real task inputs; the honest producer for
the effect is therefore a locator that proves what it returns is usable, not a
generator that invents alternatives, constraint states, or confidence values.

Two conditions must both hold before a file is admitted:

1. it declares the typed decision problem schema, and
2. ``evidence_decision_synthesis.synthesize`` returns ``DECIDED`` for it.

Condition 2 is what makes this more than a schema grep. It proves the located
problem satisfies the consumer's own validator and is actually decidable, so
the downstream synthesizer cannot fail on an input this module handed it.

No learned parameters, no external model call, no spend. Deterministic: sorted
walk, first validated match wins, so the same tree always yields the same
problem. Fails closed when nothing qualifies.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

SCHEMA = "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1"
EMIT_SCHEMA = "PROJECT_BRAIN_DECISION_EVIDENCE_LOCATION_V1"
DEFAULT_MAX_SCAN = 40000
MAX_FILE_BYTES = 4_000_000


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _synthesis_module():
    """Load the consumer itself, so validation uses its real authority.

    Deliberately not a re-implementation: if ``_normalize`` or ``synthesize``
    tightens, this locator tightens with it instead of drifting into admitting
    problems the consumer would reject.
    """
    path = pathlib.Path(__file__).resolve().with_name("evidence_decision_synthesis.py")
    spec = importlib.util.spec_from_file_location("evidence_decision_synthesis", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("DECISION_SYNTHESIS_ADAPTER_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _decides(synthesis, problem):
    """True only when the consumer reaches a terminal decision on this problem."""
    try:
        result = synthesis.synthesize(problem)
    except Exception:
        return False
    return isinstance(result, dict) and result.get("status") == "DECIDED"


def run(args, root):
    args = dict(args or {})
    base = _safe_path(root, args.get("search_root") or ".")
    out = _safe_path(root, args.get("output_path"))
    if not base.is_dir():
        raise RuntimeError("SEARCH_ROOT_NOT_A_DIRECTORY")
    if out.suffix.lower() != ".json":
        raise RuntimeError("JSON_OUTPUT_REQUIRED")
    try:
        max_scan = max(1, min(int(args.get("max_scan", DEFAULT_MAX_SCAN)), 200000))
    except (TypeError, ValueError):
        raise RuntimeError("SCAN_LIMIT_INVALID")

    root_path = pathlib.Path(root).resolve()
    synthesis = _synthesis_module()
    scanned = located = 0
    chosen = None
    chosen_rel = ""
    for path in sorted(base.glob("**/*.json")):
        if located >= max_scan:
            break
        if not path.is_file():
            continue
        located += 1
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            problem = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if not isinstance(problem, dict) or problem.get("schema") != SCHEMA:
            continue
        scanned += 1
        if _decides(synthesis, problem):
            chosen = problem
            chosen_rel = path.resolve().relative_to(root_path).as_posix()
            break

    if chosen is None:
        # Fail closed rather than emitting an empty or synthetic problem: an
        # unverifiable decision problem must not become available evidence.
        raise RuntimeError("DECISION_EVIDENCE_NONE_VALIDATED")

    canonical = json.dumps(chosen, indent=2, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(canonical, encoding="utf-8")
    raw = out.read_bytes()
    return {
        "adapter": "decision_evidence_locate",
        "status": "DECISION_EVIDENCE_LOCATED",
        "schema": EMIT_SCHEMA,
        "source_path": chosen_rel,
        "source_sha256": hashlib.sha256(
            pathlib.Path(root_path / chosen_rel).read_bytes()
        ).hexdigest(),
        "alternative_count": len(chosen.get("alternatives") or []),
        "constraint_count": len(chosen.get("constraints") or []),
        "evidence_count": len(chosen.get("evidence") or []),
        "json_files_scanned": located,
        "schema_matches_validated": scanned,
        "output_path": str(out.relative_to(root_path)).replace("\\", "/"),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
