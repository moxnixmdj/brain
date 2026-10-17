"""Binds already-existing provenance machinery to the standard adapter contract.

Nothing here is a new capability.  `source_candidate_provenance_verify` already
implements both operations needed by the Knowledge term:

    verify(candidate)                              -> BIBLIOGRAPHIC_PROVENANCE_VERIFIED
    materialize(candidate, bibliographic_verification) -> RETRIEVAL_PROVENANCE_VERIFIED

It simply exposes `verify`/`materialize` rather than `run(args, root)`, so the
registry could not bind to it, and `knowledge.status.assert` and
`knowledge.support.materialize` were left pointing at `runtime_native_action`,
a module that does not exist.

This module is the missing binding and nothing more: read args, delegate,
write the result.  All verification logic stays where it already lives.
"""
from __future__ import annotations

import json
import pathlib

import source_candidate_provenance_verify as PROV

SCHEMA = "PROJECT_BRAIN_KNOWLEDGE_STATUS_ADAPTER_V1"
MODEL_DEPENDENCY_COUNT = 0


def _safe(root: str, raw) -> pathlib.Path:
    p = pathlib.Path(str(raw))
    if not p.is_absolute():
        p = pathlib.Path(root) / p
    p = p.resolve()
    rootp = pathlib.Path(root).resolve()
    if p != rootp and rootp not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _read(root: str, raw) -> dict:
    return json.loads(_safe(root, raw).read_text(encoding="utf-8"))


def _write(root: str, raw, payload: dict) -> str:
    _safe(root, raw).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(raw)


def run_assert(args: dict, root: str) -> dict:
    """knowledge.status.assert -> verify a retrieval candidate's provenance."""
    args = dict(args or {})
    candidate = _read(root, args["candidate_path"])
    out = PROV.verify(candidate, int(args.get("timeout", 15)))
    out["model_dependency_count"] = MODEL_DEPENDENCY_COUNT
    out["incremental_spend_usd"] = 0
    if args.get("output_path"):
        _write(root, args["output_path"], out)
    return out


def run_materialize(args: dict, root: str) -> dict:
    """knowledge.support.materialize -> turn verified provenance into support."""
    args = dict(args or {})
    candidate = _read(root, args["candidate_path"])
    verification = _read(root, args["verification_path"])
    out = PROV.materialize(candidate, verification, int(args.get("timeout", 15)))
    out["model_dependency_count"] = MODEL_DEPENDENCY_COUNT
    out["incremental_spend_usd"] = 0
    if args.get("output_path"):
        _write(root, args["output_path"], out)
    return out
