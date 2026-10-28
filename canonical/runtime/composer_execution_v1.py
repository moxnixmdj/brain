# PROJECT_BRAIN
"""One executor for every composer adapter: a composition is verified when its
producers RAN on the caller's inputs and each one verified -- never because
the producers' names appear in the registry.

Measured before this (2026-10-28, direct calls with no task, no source, no
patch, no tests): sixteen ``*_supercomposer``/``*_composer``/``*_fusion``
adapters and three gate-list adapters returned ``verified: True`` after
checking that capability ids and ``provides`` tokens existed in
``BOUND_CAPABILITY_REGISTRY_V1.json``.  Nothing executed.  The front door's
``expect`` for each of them is ``output_verified == true``, so a sentence that
reached one was credited for work that was never done.

Rules enforced here, all fail-closed:

* every producer must be a registered capability with an importable adapter;
* every ``${input.X}`` the producer's own action template declares must be
  bound from the composer's inputs, except ``output_path`` which the composer
  assigns per step under its own artifact directory -- an unbound input is a
  refusal naming the producer and the key, not a default;
* the producer runs through the same ``fn(args, root)`` contract the front
  door uses, its registry ``expect`` is checked, and a result carrying
  ``verified: False`` fails the step;
* a composer reached again while it is still running is a cycle, refused;
* ``verified`` is the conjunction over a non-empty step ledger.

Nothing here knows what any producer does.  It only insists that it did it.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import traceback
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COMPOSER_EXECUTION_V1"
REGISTRY_REL = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
_INPUT_RE = re.compile(r"^\$\{input\.([A-Za-z0-9_]+)\}$")
_ACTIVE: list[str] = []


class ComposerRefusal(RuntimeError):
    pass


def _safe_output(root: pathlib.Path, raw: str | None, default: str) -> pathlib.Path:
    p = (root / str(raw or default)).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _registry(repo: pathlib.Path) -> dict[str, Any]:
    candidates = [repo / REGISTRY_REL, pathlib.Path(__file__).resolve().parents[2] / REGISTRY_REL]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")).get("capabilities") or {}
    raise ComposerRefusal("REGISTRY_UNAVAILABLE")


def _load_adapter(repo: pathlib.Path, entry: Mapping[str, Any]):
    module_name = str(entry.get("adapter_module") or "")
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    declared = str(source.get("adapter_path") or "")
    brain = pathlib.Path(__file__).resolve().parents[2]
    bases = [repo, brain]
    for base in bases:
        path = (base / declared).resolve() if declared else \
            (base / "canonical" / "runtime" / "bound_capabilities" / (module_name + ".py")).resolve()
        if base in path.parents and path.is_file() and path.suffix == ".py":
            break
    else:
        raise ComposerRefusal("PRODUCER_ADAPTER_MISSING:" + (declared or module_name))
    name = "project_brain_composer_step_" + module_name
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ComposerRefusal("PRODUCER_ADAPTER_LOAD_FAILED:" + module_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _expectation_holds(expect: Any, result: Mapping[str, Any]) -> tuple[bool, str]:
    if expect is None:
        return True, ""
    if not isinstance(expect, Mapping):
        return False, "ACTION_EXPECTATION_INVALID"
    field = str(expect.get("field") or "").strip()
    value = result.get(field)
    typ = expect.get("type", "field_nonempty")
    if typ == "field_nonempty":
        ok = value not in (None, "", [], {})
    elif typ == "field_contains":
        ok = str(expect.get("value", "")) in str(value or "")
    elif typ == "field_equals":
        ok = value == expect.get("value")
    else:
        return False, "ACTION_EXPECTATION_TYPE_UNKNOWN:" + str(typ)
    return ok, "" if ok else "ACTION_EXPECTATION_FAILED:" + field + ":OBSERVED=" + repr(value)[:200]


def _bind(producer: str, template: Mapping[str, Any], inputs: Mapping[str, Any],
          step_output_rel: str) -> tuple[dict[str, Any], list[str]]:
    bound: dict[str, Any] = {}
    unbound: list[str] = []
    for key, value in (template or {}).items():
        if key == "capability_id":
            continue
        m = _INPUT_RE.match(value) if isinstance(value, str) else None
        if m is None:
            bound[key] = json.loads(json.dumps(value))
            continue
        name = m.group(1)
        if name == "output_path":
            bound[key] = step_output_rel
        elif name in inputs and inputs[name] is not None:
            bound[key] = inputs[name]
        else:
            unbound.append(name)
    return bound, unbound


def declared_inputs(repo: pathlib.Path, producers: list[str]) -> list[str]:
    """Union of the ``${input.*}`` names the producers declare, minus output_path."""
    reg = _registry(repo)
    names: set[str] = set()
    for pid in producers:
        entry = reg.get(pid) or {}
        for value in ((entry.get("action_template") or {}).get("args") or {}).values():
            m = _INPUT_RE.match(value) if isinstance(value, str) else None
            if m and m.group(1) != "output_path":
                names.add(m.group(1))
    return sorted(names)


def compose(*, capability_id: str, schema: str, adapter: str, producers: list[str],
            requires: list[str], args: Mapping[str, Any], root: str | pathlib.Path,
            default_output: str, description: str = "") -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    args = dict(args or {})
    output = _safe_output(repo, args.get("output_path"), default_output)
    step_dir = output.with_name(output.stem + ".steps")
    step_dir.mkdir(parents=True, exist_ok=True)
    inputs = {k: v for k, v in args.items() if k not in ("output_path", "capability_id")}

    steps: list[dict[str, Any]] = []
    reason = ""
    if capability_id in _ACTIVE:
        reason = "COMPOSER_CYCLE:" + capability_id
    elif not producers:
        reason = "COMPOSER_HAS_NO_PRODUCERS"
    else:
        _ACTIVE.append(capability_id)
        try:
            reg = _registry(repo)
            for pid in producers:
                safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in pid)
                step_out = step_dir / (safe + ".json")
                step_rel = step_out.relative_to(repo).as_posix()
                row: dict[str, Any] = {"producer": pid, "verified": False, "status": "",
                                       "output_path": step_rel}
                entry = reg.get(pid)
                if not isinstance(entry, Mapping):
                    row["status"] = "PRODUCER_NOT_REGISTERED"
                    steps.append(row)
                    break
                template = (entry.get("action_template") or {})
                bound, unbound = _bind(pid, template.get("args") or {}, inputs, step_rel)
                row["bound_inputs"] = sorted(bound)
                if unbound:
                    row["status"] = "COMPOSER_INPUT_UNBOUND:" + ",".join(sorted(unbound))
                    steps.append(row)
                    break
                try:
                    module = _load_adapter(repo, entry)
                    fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
                    if not callable(fn):
                        raise ComposerRefusal("PRODUCER_ENTRYPOINT_MISSING")
                    result = fn(bound, repo)
                except ComposerRefusal as exc:
                    row["status"] = str(exc)
                    steps.append(row)
                    break
                except BaseException as exc:  # noqa: BLE001 - a raising producer is a failed step
                    row["status"] = "PRODUCER_RAISED:" + type(exc).__name__ + ":" + str(exc)[:300]
                    row["traceback_tail"] = traceback.format_exc()[-600:]
                    steps.append(row)
                    break
                if not isinstance(result, Mapping):
                    row["status"] = "PRODUCER_RESULT_INVALID"
                    steps.append(row)
                    break
                ok, why = _expectation_holds(template.get("expect"), result)
                if not ok:
                    row["status"] = why
                elif result.get("verified") is False:
                    row["status"] = "PRODUCER_NOT_VERIFIED:" + str(result.get("reason") or result.get("status") or "")[:200]
                else:
                    row["status"] = "VERIFIED"
                    row["verified"] = True
                row["result_output_sha256"] = result.get("output_sha256")
                row["result_summary"] = {k: result[k] for k in ("status", "gate", "verified", "complete")
                                         if k in result and isinstance(result[k], (str, bool, int, float))}
                steps.append(row)
                if not row["verified"]:
                    break
        finally:
            _ACTIVE.remove(capability_id)
        if steps and not steps[-1]["verified"]:
            reason = steps[-1]["status"]
        elif len(steps) != len(producers):
            reason = "COMPOSER_INCOMPLETE"

    verified = bool(steps) and len(steps) == len(producers) and all(s["verified"] for s in steps)
    artifact = {
        "schema": schema,
        "executor_schema": SCHEMA,
        "capability_id": capability_id,
        "description": description,
        "required_tokens": list(requires),
        "producers": list(producers),
        "inputs_bound": sorted(inputs),
        "steps": steps,
        "steps_run": len(steps),
        "verified": verified,
        "reason": reason,
        "verification_basis": "EVERY_PRODUCER_EXECUTED_ON_THESE_INPUTS_AND_VERIFIED"
        if verified else "NOT_VERIFIED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": adapter,
        "capability_id": capability_id,
        "output_path": output.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "verified": verified,
        "steps_run": len(steps),
        "producers": list(producers),
        "reason": reason,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
