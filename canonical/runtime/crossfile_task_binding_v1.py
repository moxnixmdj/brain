"""Lossless, request-local connection to the existing cross-file workflow.

Only an explicit staged-report request is supported. This neither registers a
capability nor turns arbitrary prose into executable edit instructions.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
from canonical.runtime.swe_task_artifacts_v1 import confined_path, fresh_output

CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
_PREFIX = re.compile(r"^\s*(?:write|create)\s+(?:a\s+)?cross[- ]file\s+repair\s+report\b", re.I)
_GRAMMAR = re.compile(
    r"\s*(?:write|create)\s+(?:a\s+)?cross[- ]file\s+repair\s+report\s+to\s+"
    r"(?P<output>[A-Za-z0-9_./-]+\.json)\s+for\s+(?:the\s+)?source\s+root\s+"
    r"(?P<source>[A-Za-z0-9_./-]+)\s+using\s+(?:the\s+)?(?P<kind>issue|task)\s+(?:path|file)\s+"
    r"(?P<input>[A-Za-z0-9_./-]+\.json)\.?\s*", re.I)
STAGE_ARTIFACTS = frozenset({".orchestrate_plan.json", ".orchestrate_stage.diff", ".orchestrate_testselect.json"})


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def is_request(goal):
    return bool(_PREFIX.match(str(goal)))


def parse_goal(goal):
    match = _GRAMMAR.fullmatch(goal)
    if match is None:
        raise ValueError("CROSSFILE_REQUEST_HAS_UNBOUND_PROSE_OR_PATHS")
    return {"source_root": match["source"], "output_path": match["output"],
            match["kind"].lower() + "_path": match["input"]}


def content_manifest(manifest):
    files = [r for r in manifest["files"] if r["path"] not in STAGE_ARTIFACTS]
    return {"files": files, "tree_sha256": digest({"files": files})}


def bind_context(goal, context, root):
    """Reuse the real compiler and binder; copy only this request's template."""
    wanted = parse_goal(goal)
    registry, admissible, compiled = context
    if (compiled.get("selected_capability") != CAPABILITY_ID
            or compiled.get("capability_dag") or compiled.get("controller_actions") is not None):
        raise ValueError("CROSSFILE_REQUEST_NOT_DECISIVELY_SELECTED")
    entry = deepcopy(admissible[CAPABILITY_ID])
    mode = "issue_path" if "issue_path" in wanted else "task_path"
    for key in ("action_template", "declared_action_template"):
        if key in entry:
            entry[key]["args"][mode] = "${input." + mode + "}"
    inputs = front.bind_all_inputs(goal, entry, root)
    if inputs != wanted:
        raise ValueError("CROSSFILE_PATH_ROLES_NOT_EXACTLY_BOUND")
    source = confined_path(root, inputs["source_root"])
    if not source.is_dir():
        raise ValueError("CROSSFILE_SOURCE_NOT_DIRECTORY")
    output = fresh_output(root, inputs["output_path"], "unused.json")
    if source == output or source in output.parents:
        raise ValueError("CROSSFILE_OUTPUT_OVERLAPS_SOURCE")
    path = confined_path(root, inputs[mode])
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("CROSSFILE_INPUT_NOT_OBJECT")
    if mode == "issue_path":
        if (not isinstance(payload.get("issue_id"), str) or not payload["issue_id"].strip()
                or not isinstance(payload.get("title"), str) or not payload["title"].strip()
                or not isinstance(payload.get("body", ""), str)
                or set(payload) - {"issue_id", "title", "body"}):
            raise ValueError("CROSSFILE_ISSUE_SCHEMA_UNSUPPORTED")
    else:
        if set(payload) - {"issue_id", "edits"}:
            # Prose belongs in issue mode, where it is parsed/refused rather
            # than silently treated as metadata beside authoritative edit ops.
            raise ValueError("CROSSFILE_TASK_HAS_UNBOUND_METADATA")
        from canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 import _task
        _task(payload, source)
    manifest = tree_manifest(source)
    if manifest["pass"] is not True:
        raise ValueError("CROSSFILE_SOURCE_MANIFEST_INVALID")
    spec = {"goal_sha256": hashlib.sha256(goal.encode()).hexdigest(),
            "source_root": inputs["source_root"], "output_path": inputs["output_path"],
            "input_key": mode, "input_path": inputs[mode],
            "input_sha256": hashlib.sha256(raw).hexdigest(),
            "source_tree_sha256": manifest["tree_sha256"]}
    for key in ("action_template", "declared_action_template"):
        if key in entry:
            entry[key]["args"]["request_binding"] = deepcopy(spec)
            entry[key]["args"]["request_binding_sha256"] = digest(spec)
    updated = dict(admissible)
    updated[CAPABILITY_ID] = entry
    plan = dict(compiled)
    plan["inputs"] = inputs
    plan["crossfile_task_binding"] = spec
    return registry, updated, plan


def validate_binding(args, root, manifest=None):
    """The source/input must still be the preflight versions, not replacements."""
    spec = args.get("request_binding")
    if not isinstance(spec, dict) or digest(spec) != args.get("request_binding_sha256"):
        raise ValueError("CROSSFILE_REQUEST_BINDING_INVALID")
    mode = spec.get("input_key")
    if (mode not in ("issue_path", "task_path")
            or args.get(mode) != spec.get("input_path")
            or args.get("source_root") != spec.get("source_root")
            or args.get("output_path") != spec.get("output_path")
            or args.get("task_path" if mode == "issue_path" else "issue_path")):
        raise ValueError("CROSSFILE_REQUEST_BINDING_SUBSTITUTED")
    source = confined_path(root, spec["source_root"])
    manifest = tree_manifest(source) if manifest is None else manifest
    path = confined_path(root, spec["input_path"])
    if (manifest["pass"] is not True or manifest["tree_sha256"] != spec["source_tree_sha256"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != spec["input_sha256"]):
        raise ValueError("CROSSFILE_REQUEST_PREIMAGE_CHANGED")
    return spec


def goal_matches_args(goal, args):
    wanted = parse_goal(goal)
    spec = args.get("request_binding") or {}
    return (all(args.get(k) == v for k, v in wanted.items())
            and spec.get("goal_sha256") == hashlib.sha256(goal.encode()).hexdigest())
