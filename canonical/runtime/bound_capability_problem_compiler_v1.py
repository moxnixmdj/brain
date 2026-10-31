"""Pure compiler from verified bound-capability instances to an explicit capability graph.

This is the shared planning/execution contract for the Universal Solver and Astra.
It reads the exact pinned BOUND_CAPABILITY_REGISTRY_V1 bytes, accepts only explicit
instances of VERIFIED_BOUND_CAPABILITY entries, renders the registry action template,
applies declared effect aliases, and emits a normal capability_planner problem.

It performs no dependency installation and no action. Astra may execute the emitted
graph; the universal solver may independently recompute and verify its execution
trace. Manual capability/action injection is intentionally outside this interface.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_PROBLEM_COMPILER_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class BoundProblemError(ValueError):
    pass


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load_registry() -> tuple[Mapping[str, Any], str]:
    # The checked-out Git commit already binds code and registry atomically.
    # Bind the compiled problem to those exact current registry bytes instead of
    # requiring a second manually-updated blob constant that goes stale.
    reg_path = ROOT / REGISTRY_PATH
    raw = reg_path.read_bytes()
    if not raw.lstrip().startswith(b"{"):
        snap = reg_path.with_name("BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
        if snap.is_file():
            raw = snap.read_bytes()
    actual = _git_blob(raw)
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema") not in (
        "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
        "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1",
    ):
        raise BoundProblemError("BOUND_REGISTRY_SCHEMA_INVALID")
    caps = dict(doc.get("capabilities") or {})
    snap = reg_path.with_name("BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
    if snap.is_file():
        sdoc = json.loads(snap.read_text(encoding="utf-8"))
        caps.update(sdoc.get("capabilities") or {})
    if not isinstance(caps, Mapping) or not caps:
        raise BoundProblemError("BOUND_REGISTRY_CAPABILITIES_INVALID")
    return caps, actual


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BoundProblemError(label + "_INVALID")
    return value.strip()


def _tokens(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BoundProblemError(label + "_INVALID")
    out = [_token(x, label) for x in value]
    if not allow_empty and not out:
        raise BoundProblemError(label + "_EMPTY")
    if len(out) != len(set(out)):
        raise BoundProblemError(label + "_DUPLICATE")
    return out


def _render(value: Any, inputs: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        return {k: _render(v, inputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, inputs) for v in value]
    if isinstance(value, str):
        if value.startswith("${input.") and value.endswith("}") and value.count("${") == 1:
            key = value[len("${input."):-1]
            if key not in inputs:
                raise BoundProblemError("BOUND_CAPABILITY_INPUT_MISSING:" + key)
            return deepcopy(inputs[key])
        out = value
        for key, val in inputs.items():
            out = out.replace("${input." + str(key) + "}", str(val))
        if "${input." in out:
            raise BoundProblemError("BOUND_CAPABILITY_INPUT_MISSING")
        return out
    return deepcopy(value)


def _aliases(raw: Any, declared: Sequence[str], label: str, *, allow_repeat_source: bool) -> list[tuple[str, str]]:
    if raw is None:
        pairs = []
    elif isinstance(raw, Mapping):
        pairs = list(raw.items())
    elif isinstance(raw, list):
        pairs = []
        for item in raw:
            if not isinstance(item, Mapping) or set(item) != {"effect", "as"}:
                raise BoundProblemError(label + "_ALIASES_INVALID")
            pairs.append((item["effect"], item["as"]))
    else:
        raise BoundProblemError(label + "_ALIASES_INVALID")

    allowed = {str(x) for x in declared}
    seen_src: set[str] = set()
    seen_dst: set[str] = set()
    out: list[tuple[str, str]] = []
    for src_raw, dst_raw in pairs:
        src = _token(src_raw, label + "_SOURCE")
        dst = _token(dst_raw, label + "_TARGET")
        if src not in allowed:
            raise BoundProblemError(label + "_SOURCE_UNKNOWN:" + src)
        if dst in seen_dst:
            raise BoundProblemError(label + "_TARGET_DUPLICATE:" + dst)
        if src in seen_src and not allow_repeat_source:
            raise BoundProblemError(label + "_SOURCE_DUPLICATE:" + src)
        seen_src.add(src)
        seen_dst.add(dst)
        out.append((src, dst))
    return out


def _apply_aliases(effects: Sequence[str], aliases: Sequence[tuple[str, str]]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    for src, dst in aliases:
        grouped.setdefault(src, []).append(dst)
    out: list[str] = []
    for effect in effects:
        targets = grouped.get(str(effect))
        out.extend(targets if targets else [str(effect)])
    return out


def _current_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return sys.platform


def compile_problem(spec: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(spec, Mapping):
            raise BoundProblemError("SPEC_NOT_OBJECT")
        allowed_keys = {
            "initial_facts",
            "target_effects",
            "capability_instances",
            "finish_summary",
            "max_expansions",
        }
        extra = sorted(set(spec) - allowed_keys)
        if extra:
            raise BoundProblemError("SPEC_FIELDS_UNSUPPORTED:" + ",".join(extra))

        initial = _tokens(spec.get("initial_facts", []), "INITIAL_FACTS")
        targets = _tokens(spec.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        raw_instances = spec.get("capability_instances")
        if not isinstance(raw_instances, list) or not raw_instances:
            raise BoundProblemError("CAPABILITY_INSTANCES_REQUIRED")

        registry, registry_blob = _load_registry()
        platform = _current_platform()
        caps: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        bindings: list[dict[str, Any]] = []

        for i, raw in enumerate(raw_instances):
            if not isinstance(raw, Mapping):
                raise BoundProblemError("CAPABILITY_INSTANCE_NOT_OBJECT:" + str(i))
            allowed_instance_keys = {
                "instance_id",
                "capability_id",
                "inputs",
                "requires_as",
                "provides_as",
            }
            extra_i = sorted(set(raw) - allowed_instance_keys)
            if extra_i:
                raise BoundProblemError("CAPABILITY_INSTANCE_FIELDS_UNSUPPORTED:" + ",".join(extra_i))

            instance_id = _token(raw.get("instance_id"), "INSTANCE_ID")
            capability_id = _token(raw.get("capability_id"), "CAPABILITY_ID")
            if instance_id in seen_ids:
                raise BoundProblemError("INSTANCE_ID_DUPLICATE:" + instance_id)
            seen_ids.add(instance_id)

            entry = registry.get(capability_id)
            if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
                raise BoundProblemError("SOURCE_CAPABILITY_NOT_VERIFIED:" + capability_id)
            if float(entry.get("incremental_spend_usd", 0)) != 0:
                raise BoundProblemError("SOURCE_CAPABILITY_NONZERO_INCREMENTAL_SPEND:" + capability_id)

            platforms = entry.get("platforms")
            if isinstance(platforms, list) and platforms and platform not in platforms:
                raise BoundProblemError("SOURCE_CAPABILITY_PLATFORM_UNSUPPORTED:" + capability_id)

            inputs = raw.get("inputs", {})
            if not isinstance(inputs, Mapping):
                raise BoundProblemError("INSTANCE_INPUTS_INVALID:" + instance_id)
            template = entry.get("action_template")
            if not isinstance(template, Mapping):
                raise BoundProblemError("SOURCE_ACTION_TEMPLATE_MISSING:" + capability_id)
            action = _render(template, inputs)

            req_decl = _tokens(entry.get("requires", []), capability_id + ".requires")
            pro_decl = _tokens(entry.get("provides", []), capability_id + ".provides", allow_empty=False)
            req_alias = _aliases(raw.get("requires_as"), req_decl, "REQUIRES_AS:" + instance_id, allow_repeat_source=True)
            pro_alias = _aliases(raw.get("provides_as"), pro_decl, "PROVIDES_AS:" + instance_id, allow_repeat_source=False)
            requires = _apply_aliases(req_decl, req_alias)
            provides = _apply_aliases(pro_decl, pro_alias)

            cap = {
                "id": instance_id,
                "source_capability_id": capability_id,
                "requires": requires,
                "provides": provides,
                "cost": float(entry.get("cost", 1)),
                "action": action,
                "result_fields": list(entry.get("result_fields") or []),
            }
            caps.append(cap)
            bindings.append({
                "instance_id": instance_id,
                "capability_id": capability_id,
                "requires": requires,
                "provides": provides,
            })

        finish = str(spec.get("finish_summary", "CAPABILITY_PLAN_COMPLETE")).strip()
        if not finish:
            raise BoundProblemError("FINISH_SUMMARY_REQUIRED")
        max_expansions = int(spec.get("max_expansions", 5000))
        if max_expansions < 1 or max_expansions > 1000000:
            raise BoundProblemError("MAX_EXPANSIONS_INVALID")

        problem = {
            "initial_facts": initial,
            "target_effects": targets,
            "capabilities": caps,
            "finish_summary": finish,
            "max_expansions": max_expansions,
        }
        canonical = json.dumps(problem, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return {
            "schema": SCHEMA,
            "status": "PASS__VERIFIED_BOUND_CAPABILITY_PROBLEM_COMPILED",
            "pass": True,
            "problem": problem,
            "problem_sha256": sha256(canonical).hexdigest(),
            "registry_path": REGISTRY_PATH,
            "registry_git_blob_sha": registry_blob,
            "instance_bindings": bindings,
            "manual_capability_action_injection_permitted": False,
            "execution_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "execution_authority": False,
            "terminal_authority": False,
        }
