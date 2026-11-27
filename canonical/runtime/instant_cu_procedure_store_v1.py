"""External, inspectable, editable, deletable instant Computer-Use Procedure Store.

Zero external model calls. Zero memorized-fact weights (`parameters_stored: 0`).
Every learned procedure lives as plain, human-readable JSON on disk, abstracted
over typed environment holes (`__WORKSPACE__`, `__REPO_DIR__`, `__TARGET_BRANCH__`,
`__OUTPUT_PATH__`, `__PATTERN__`, `__DB_PATH__`, etc.) so concrete paths, branch
names, or secrets from one environment can NEVER leak into an unseen environment.

Admission, recall, deletion, and single-counterexample precondition narrowing
mirror `instant_condition_store_v1.py` and `instant_swe_skill_store_v1.py`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_INSTANT_CU_PROCEDURE_STORE_V1"
AUTHORITY = "NONE"

STATUS_PROVISIONAL = "PROVISIONAL__ADMITTED_FROM_VERIFIED_RUN"
STATUS_NARROWED = "NARROWED__COUNTEREXAMPLE_REFINED"
STATUS_QUARANTINED = "QUARANTINED__NO_OBSERVABLE_SEPARATION"

DEFAULT_STORE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "state"
    / "INSTANT_CU_PROCEDURE_STORE_V1.json"
)

ALLOWED_HOLES = frozenset({
    "__WORKSPACE__",
    "__REPO_DIR__",
    "__TARGET_BRANCH__",
    "__OUTPUT_PATH__",
    "__INPUT_PATH__",
    "__INPUT_DIR__",
    "__OUTPUT_DIR__",
    "__ARCHIVE_PATH__",
    "__PATTERN__",
    "__QUERY__",
    "__ARG_1__",
    "__ARG_2__",
    "__DB_PATH__",
    "__WAL_PATH__",
    "__LOGS_DIR__",
    "__SORT_KEY__",
    "__KEY_PATH__",
    "__CERT_PATH__",
    "__TEST_TARGET__",
})


def new_store() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "external_model_dependency": False,
        "parameters_stored": 0,
        "procedures": {},
    }


def load_store(path: str | pathlib.Path = DEFAULT_STORE_PATH) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        return new_store()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError(f"UNEXPECTED_PROCEDURE_STORE_SCHEMA: {data.get('schema')!r}")
    data.setdefault("procedures", {})
    return data


def save_store(store: Mapping[str, Any], path: str | pathlib.Path = DEFAULT_STORE_PATH) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def delete_procedure(store: dict[str, Any], procedure_id: str) -> bool:
    procs = store.get("procedures")
    if isinstance(procs, dict) and procedure_id in procs:
        del procs[procedure_id]
        return True
    return False


def _abstract_value(val: Any, concrete_to_hole: Mapping[str, str]) -> Any:
    if isinstance(val, str):
        out = val
        for concrete, hole in sorted(concrete_to_hole.items(), key=lambda kv: -len(kv[0])):
            if concrete and concrete in out:
                out = out.replace(concrete, hole)
        return out
    if isinstance(val, list):
        return [_abstract_value(v, concrete_to_hole) for v in val]
    if isinstance(val, dict):
        return {k: _abstract_value(v, concrete_to_hole) for k, v in val.items()}
    return val


def _instantiate_value(val: Any, hole_to_concrete: Mapping[str, str]) -> Any:
    if isinstance(val, str):
        out = val
        for hole, concrete in hole_to_concrete.items():
            if hole in out:
                out = out.replace(hole, str(concrete))
        return out
    if isinstance(val, list):
        return [_instantiate_value(v, hole_to_concrete) for v in val]
    if isinstance(val, dict):
        return {k: _instantiate_value(v, hole_to_concrete) for k, v in val.items()}
    return val


def _contains_unabstracted_path(val: Any) -> bool:
    """Reject admission if an absolute temporary/workspace path leaked into a procedure."""
    if isinstance(val, str):
        return val.startswith("/tmp/") or val.startswith("/home/") or val.startswith("/var/")
    if isinstance(val, list):
        return any(_contains_unabstracted_path(v) for v in val)
    if isinstance(val, dict):
        return any(_contains_unabstracted_path(v) for v in val.values())
    return False


def _extract_used_holes(val: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(val, str):
        for h in ALLOWED_HOLES:
            if h in val:
                found.add(h)
    elif isinstance(val, list):
        for v in val:
            found.update(_extract_used_holes(v))
    elif isinstance(val, dict):
        for v in val.values():
            found.update(_extract_used_holes(v))
    return found


def induce_procedure_from_verified_run(
    store: dict[str, Any],
    *,
    domain: str,
    goal_kind: str,
    concrete_steps: Sequence[Mapping[str, Any]],
    hole_bindings: Mapping[str, str],
    env_observables: Sequence[str],
    frame_invariants: Sequence[str],
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Compile ONE verified computer-use run into a hole-abstracted external procedure.

    Refuses admission if any environment-specific absolute path leaks through or
    round-trip instantiation fails to reconstruct `concrete_steps`.
    """
    if not concrete_steps:
        return None
    valid_bindings = {
        h: str(v) for h, v in hole_bindings.items() if h in ALLOWED_HOLES and str(v)
    }
    concrete_to_hole = {v: h for h, v in valid_bindings.items()}
    abstract_steps = [_abstract_value(dict(st), concrete_to_hole) for st in concrete_steps]

    # Admission gate 1: no leaked host-specific paths
    if _contains_unabstracted_path(abstract_steps):
        return None

    # Admission gate 2: exact round-trip reconstruction
    reconstructed = [_instantiate_value(st, valid_bindings) for st in abstract_steps]
    if reconstructed != [dict(st) for st in concrete_steps]:
        return None

    used_holes = sorted(_extract_used_holes(abstract_steps))
    obs_sorted = sorted(set(str(o) for o in env_observables))
    inv_sorted = sorted(set(str(i) for i in frame_invariants))

    sig = json.dumps(
        {"domain": domain, "goal_kind": goal_kind, "steps": abstract_steps},
        sort_keys=True,
    )
    pid = "proc_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]

    procs = store.setdefault("procedures", {})
    existing = procs.get(pid)
    if existing is not None:
        existing["support_count"] = int(existing.get("support_count", 1)) + 1
        # Intersect support observables across positive runs
        prev_obs = set(existing.get("support_env_observables") or ())
        existing["support_env_observables"] = sorted(prev_obs & set(obs_sorted)) if prev_obs else obs_sorted
        if provenance:
            provs = list(existing.get("provenance_examples") or [])
            provs.append(dict(provenance))
            existing["provenance_examples"] = provs[-10:]
        return existing

    # Promote core domain observables into initial required preconditions; keep full set for narrowing
    core_required = [o for o in obs_sorted if o.startswith("has_") or o.startswith("domain:")]
    record = {
        "procedure_id": pid,
        "status": STATUS_PROVISIONAL,
        "domain": domain,
        "goal_kind": goal_kind,
        "required_holes": used_holes,
        "required_env_observables": sorted(core_required),
        "support_env_observables": obs_sorted,
        "frame_invariants": inv_sorted,
        "steps": abstract_steps,
        "support_count": 1,
        "refutations": [],
        "provenance_examples": [dict(provenance)] if provenance else [],
        "external_model_dependency": False,
        "parameters_stored": 0,
    }
    procs[pid] = record
    return record


def recall_procedures(
    store: Mapping[str, Any],
    *,
    domain: str,
    goal_kind: str,
    env_observables: Sequence[str],
    hole_bindings: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Recall and instantiate matching non-quarantined procedures for an unseen environment."""
    obs_set = set(str(o) for o in env_observables)
    procs = store.get("procedures") or {}
    matches: list[dict[str, Any]] = []

    for pid, proc in sorted(
        procs.items(),
        key=lambda kv: (-int(kv[1].get("support_count", 1)), kv[0]),
    ):
        if proc.get("status") == STATUS_QUARANTINED:
            continue
        if proc.get("domain") != domain or proc.get("goal_kind") != goal_kind:
            continue
        req_obs = set(proc.get("required_env_observables") or ())
        if not req_obs.issubset(obs_set):
            continue
        req_holes = proc.get("required_holes") or []
        if any(h not in hole_bindings or not str(hole_bindings[h]) for h in req_holes):
            continue
        inst_steps = [_instantiate_value(st, hole_bindings) for st in proc.get("steps") or ()]
        matches.append({
            "procedure_id": pid,
            "status": proc.get("status"),
            "support_count": int(proc.get("support_count", 1)),
            "steps": inst_steps,
            "frame_invariants": list(proc.get("frame_invariants") or ()),
        })
    return matches


def refute_procedure(
    store: dict[str, Any],
    procedure_id: str,
    *,
    counterexample_observables: Sequence[str],
    reason: str = "POSTCONDITION_FAILED",
) -> dict[str, Any]:
    """Narrow a procedure's required observables from ONE counterexample, or quarantine fail-closed."""
    procs = store.get("procedures") or {}
    proc = procs.get(procedure_id)
    if proc is None:
        return {"procedure_id": procedure_id, "status": "NOT_FOUND"}

    ce_set = set(str(o) for o in counterexample_observables)
    sup_set = set(proc.get("support_env_observables") or ())
    req_set = set(proc.get("required_env_observables") or ())

    separators = sorted((sup_set - ce_set) - req_set)
    ref_entry = {
        "reason": reason,
        "counterexample_observables": sorted(ce_set),
    }

    if separators:
        added = separators[0]
        req_set.add(added)
        proc["required_env_observables"] = sorted(req_set)
        proc["status"] = STATUS_NARROWED
        ref_entry["resolution"] = f"ADDED_OBSERVABLE:{added}"
        proc.setdefault("refutations", []).append(ref_entry)
        return {
            "procedure_id": procedure_id,
            "status": "NARROWED",
            "added_observable": added,
        }

    proc["status"] = STATUS_QUARANTINED
    ref_entry["resolution"] = "QUARANTINED_NO_SEPARATING_OBSERVABLE"
    proc.setdefault("refutations", []).append(ref_entry)
    return {"procedure_id": procedure_id, "status": "QUARANTINED"}
