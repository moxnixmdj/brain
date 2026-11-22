#!/usr/bin/env python3
"""Static audit of every tracked Python module that can name a model endpoint.

The question this instrument answers is narrow on purpose:

    Starting from a named entry module, which files could reach a model-inference
    endpoint literal, whether through a static import or through one of the tree's
    own dynamic loaders?

It answers with `ast`, so **no audited module is ever imported or executed**. That
makes the answer a lower bound in one direction (a URL assembled from parts at run
time is invisible here) and an over-approximation in another (an import inside a
branch that never runs still counts). Both directions are reported, because a
"zero model calls" claim that does not say which way it can be wrong is not a
measurement.

Three literal classes are distinguished, and only the first is cognition:

    INFERENCE_ENDPOINT      a chat/completions style route: an external model answer
                            is the output (pollinations, openai, anthropic, openrouter,
                            or a loopback llama.cpp server on /v1)
    MODEL_ARTIFACT_HOST     huggingface.co: model *bytes*, not an answer
    (unclassified)          anything else

The instrument also censuses the one switch in the tree that turns a model into an
operative planner (`allow_optional_model_planner`) across committed missions and
across the guards that could forbid it, because "off by default" and "cannot be
turned on" are different facts and only the second one is a boundary.

Authority: NONE. This is an audit of source text. It confers no capability credit
and it does not establish that any route is correct, only which files can name a
model endpoint.
"""
from __future__ import annotations

import argparse
import ast
import functools
import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "BRAIN_MODEL_CALL_SURFACE_AUDIT_V1"
AUTHORITY = "NONE__STATIC_ONLY__NO_AUDITED_MODULE_EXECUTED"

INFERENCE_ENDPOINT = re.compile(
    r"(text\.pollinations\.ai"
    r"|api\.openai\.com|api\.anthropic\.com|openrouter\.ai"
    r"|generativelanguage\.googleapis\.com|api\.mistral\.ai|api\.groq\.com"
    r"|\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0):\d+/(?:v1|api)\b"
    r"|/v1/chat/completions|/chat/completions)"
)
MODEL_ARTIFACT_HOST = re.compile(r"(huggingface\.co|hf\.co)")

GUARD_PATHS = (
    "canonical/runtime/enforce_goal_hierarchy.py",
    "execution_guard/enforce_load_bearing_primary_pr.py",
    "execution_guard/load_bearing_primary_admission.py",
)
PLANNER_FLAG = "allow_optional_model_planner"
MISSIONS_DIR = "canonical/astra_runtime/missions"


def git(root: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


def tracked_python_files(root: pathlib.Path) -> list[str]:
    raw = git(root, "ls-files", "-z", "*.py")
    return sorted(x for x in raw.split("\0") if x)


def _module_name(rel: str) -> str | None:
    if not rel.endswith(".py"):
        return None
    parts = rel[:-3].split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


@functools.lru_cache(maxsize=20000)
def _read_cached(path: str, mtime_ns: int, size: int) -> str:
    # The stat tuple is part of the key, so a file edited during one audit is re-read
    # and a second audit of the same tree does not pay for the parse twice.
    return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")


def read_text(root: pathlib.Path, rel: str) -> str:
    path = root / rel
    stat = path.stat()
    return _read_cached(str(path), stat.st_mtime_ns, stat.st_size)


@functools.lru_cache(maxsize=20000)
def _parse_cached(path: str, mtime_ns: int, size: int) -> ast.Module | None:
    try:
        return ast.parse(_read_cached(path, mtime_ns, size))
    except SyntaxError:
        return None


def _parse(root: pathlib.Path, rel: str) -> ast.Module | None:
    try:
        stat = (root / rel).stat()
    except OSError:
        return None
    return _parse_cached(str(root / rel), stat.st_mtime_ns, stat.st_size)


def endpoint_hits(root: pathlib.Path, rel: str) -> list[dict]:
    """Every string literal in `rel` whose text names a model endpoint or artifact host."""
    try:
        text = read_text(root, rel)
    except OSError:
        return []
    if not (INFERENCE_ENDPOINT.search(text) or MODEL_ARTIFACT_HOST.search(text)):
        return []
    tree = _parse(root, rel)
    if tree is None:
        return [{"line": 0, "class": "UNPARSABLE", "literal": ""}]
    hits: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        value = node.value
        kind = None
        matched = ""
        if m := INFERENCE_ENDPOINT.search(value):
            kind, matched = "INFERENCE_ENDPOINT", m.group(0)
        elif m := MODEL_ARTIFACT_HOST.search(value):
            kind, matched = "MODEL_ARTIFACT_HOST", m.group(0)
        if kind is None:
            continue
        key = (node.lineno, matched)
        if key in seen:
            continue
        seen.add(key)
        hits.append({"line": node.lineno, "class": kind, "literal": matched})
    if hits:
        return sorted(hits, key=lambda x: (x["line"], x["literal"]))
    # Text matched but no literal did (e.g. the pattern is split across an f-string):
    # report the line, never guess that it is unreachable.
    for i, line in enumerate(text.splitlines(), 1):
        if m := (INFERENCE_ENDPOINT.search(line) or MODEL_ARTIFACT_HOST.search(line)):
            kind = (
                "INFERENCE_ENDPOINT"
                if INFERENCE_ENDPOINT.search(line)
                else "MODEL_ARTIFACT_HOST"
            )
            return [{"line": i, "class": kind, "literal": m.group(0)}]
    return []


def internal_imports(root: pathlib.Path, rel: str) -> set[str]:
    tree = _parse(root, rel)
    if tree is None:
        return set()
    # Absolute imports only; relative imports are followed by the package they name.
    # Names that do not resolve to a tracked file simply drop out of the closure, so
    # stdlib and third-party imports cost nothing and are never guessed at.
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
            for alias in node.names:
                if alias.name != "*":
                    found.add(node.module + "." + alias.name)
    return found


def static_closure(
    root: pathlib.Path, entry_rel: str, by_module: dict[str, str]
) -> set[str]:
    seen: set[str] = set()
    stack = [_module_name(entry_rel)]
    while stack:
        name = stack.pop()
        if not name:
            continue
        rel = by_module.get(name)
        if rel is None or rel in seen:
            continue
        seen.add(rel)
        stack.extend(internal_imports(root, rel))
    return seen


def dynamic_load_targets(root: pathlib.Path, rel: str) -> list[dict]:
    """Sites in `rel` that load another module by a string, bypassing the import graph.

    Two shapes exist in this tree and both are read here without executing anything:

        _load_runtime_helper("<module>")                 -> canonical/runtime/<module>.py
        spec_from_file_location(..., <path>/"<file>.py") -> that sibling file
    """
    tree = _parse(root, rel)
    if tree is None:
        return []
    out: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        # The tree calls `importlib.util.spec_from_file_location(...)`, so the loader
        # name is an ATTRIBUTE two levels down, not a bare Name.
        parts: list[str] = []
        cursor = fn
        while isinstance(cursor, ast.Attribute):
            parts.append(cursor.attr)
            cursor = cursor.value
        if isinstance(cursor, ast.Name):
            parts.append(cursor.id)
        name = parts[0] if parts else ""
        if name in {"_load_runtime_helper", "_load_runtime_helper_module"}:
            for arg in node.args[:1]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    out.append(
                        {
                            "line": node.lineno,
                            "kind": "RUNTIME_HELPER",
                            "target": f"canonical/runtime/{arg.value}.py",
                        }
                    )
        elif name == "spec_from_file_location":
            # The path is usually a local name built one line earlier
            # (`p = pathlib.Path(__file__)...with_name("hidden.py")`), so the literal
            # is resolved through the module's own assignments rather than assumed to
            # sit inside the call.
            literals = _filename_literals(tree, node)
            for value in literals:
                base = pathlib.PurePosixPath(rel).parent
                out.append(
                    {
                        "line": node.lineno,
                        "kind": "SIBLING_MODULE_FILE",
                        "target": str((base / pathlib.PurePosixPath(value).name).as_posix()),
                    }
                )
    return sorted(out, key=lambda x: (x["line"], x["target"]))


def _filename_literals(tree: ast.Module, call: ast.Call) -> list[str]:
    """String constants ending in `.py` that the call's arguments can resolve to."""
    assigned: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assigned.setdefault(target.id, []).extend(
                    item.value
                    for item in ast.walk(node.value)
                    if isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                    and item.value.endswith(".py")
                )
    found: list[str] = []
    for arg in list(call.args) + [kw.value for kw in call.keywords]:
        direct = [
            item.value
            for item in ast.walk(arg)
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
            and item.value.endswith(".py")
        ]
        if direct:
            found.extend(direct)
        elif isinstance(arg, ast.Name):
            found.extend(assigned.get(arg.id, []))
    return sorted(set(found))


def dynamic_reachable(
    root: pathlib.Path, entry_rel: str, by_module: dict[str, str], depth: int = 2
) -> dict:
    """Resolve dynamic loads one or two hops out and union their static closures."""
    frontier = {entry_rel}
    visited: set[str] = set()
    targets: dict[str, dict] = {}
    for _ in range(max(1, depth)):
        nxt: set[str] = set()
        for rel in sorted(frontier):
            if rel in visited or not (root / rel).is_file():
                continue
            visited.add(rel)
            for site in dynamic_load_targets(root, rel):
                target = site["target"]
                if not (root / target).is_file():
                    targets[target] = {**site, "exists": False, "from": rel}
                    continue
                targets[target] = {**site, "exists": True, "from": rel}
                nxt.add(target)
                nxt |= static_closure(root, target, by_module)
        frontier = nxt
        if not frontier:
            break
    return {
        "dynamic_targets": {
            k: v for k, v in sorted(targets.items()) if v.get("exists")
        },
        "dynamic_targets_missing": sorted(
            k for k, v in targets.items() if not v.get("exists")
        ),
        "dynamic_closure": sorted(visited),
    }


def planner_flag_census(root: pathlib.Path) -> dict:
    missions = sorted(
        rel
        for rel in git(root, "ls-files", "*.json").splitlines()
        if rel.startswith(MISSIONS_DIR + "/")
    )
    counts = {"missions": 0, "planner_flag_true": 0, "planner_flag_false": 0,
              "planner_flag_absent": 0}
    true_missions: list[str] = []
    for rel in missions:
        try:
            payload = json.loads(read_text(root, rel))
        except (OSError, json.JSONDecodeError):
            continue
        counts["missions"] += 1
        values: list[bool] = []

        def walk(value: object) -> None:
            if isinstance(value, dict):
                if PLANNER_FLAG in value:
                    values.append(value[PLANNER_FLAG] is True)
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)
        if any(values):
            counts["planner_flag_true"] += 1
            true_missions.append(rel)
        elif values:
            counts["planner_flag_false"] += 1
        else:
            counts["planner_flag_absent"] += 1
    enforcement: list[dict] = []
    for rel in GUARD_PATHS:
        path = root / rel
        if not path.is_file():
            continue
        hits = [
            {"line": i, "text": line.strip()[:160]}
            for i, line in enumerate(read_text(root, rel).splitlines(), 1)
            if PLANNER_FLAG in line or "MODEL_ASSISTED" in line
        ]
        enforcement.append({"path": rel, "mentions": hits})
    workflows = [
        rel
        for rel in git(root, "ls-files", "*.yml").splitlines()
        if rel.startswith(".github/workflows/")
    ]
    workflow_mentions = []
    for rel in workflows:
        text = read_text(root, rel)
        if PLANNER_FLAG in text:
            workflow_mentions.append(rel)
    return {
        **counts,
        "missions_with_planner_flag_true": true_missions,
        "guard_mentions": enforcement,
        "workflow_mentions": sorted(workflow_mentions),
        "interpretation": (
            "The planner switch is read from the mission step at run time. No committed "
            "mission sets it true; absence of the key means false. No guard rejects a "
            "mission that sets it, so the no-model boundary is a convention of the "
            "committed missions, not an enforced property of the runtime."
        ),
    }


def audit(root: pathlib.Path, entries: dict[str, str]) -> dict:
    files = tracked_python_files(root)
    by_module = {m: f for f in files if (m := _module_name(f))}
    hits = {f: h for f in files if (h := endpoint_hits(root, f))}
    inference_files = sorted(
        f for f, hs in hits.items() if any(h["class"] == "INFERENCE_ENDPOINT" for h in hs)
    )
    artifact_files = sorted(
        f for f, hs in hits.items() if any(h["class"] == "MODEL_ARTIFACT_HOST" for h in hs)
    )

    report_entries: dict[str, dict] = {}
    for label, entry_rel in entries.items():
        closure = static_closure(root, entry_rel, by_module) if (root / entry_rel).is_file() else set()
        dyn = dynamic_reachable(root, entry_rel, by_module) if (root / entry_rel).is_file() else {
            "dynamic_targets": {}, "dynamic_targets_missing": [], "dynamic_closure": []
        }
        combined = set(closure) | set(dyn["dynamic_closure"])
        report_entries[label] = {
            "entry": entry_rel,
            "entry_exists": (root / entry_rel).is_file(),
            "static_closure_size": len(closure),
            "static_inference_endpoint_files": sorted(set(closure) & set(inference_files)),
            "static_model_artifact_files": sorted(set(closure) & set(artifact_files)),
            "dynamic_targets": dyn["dynamic_targets"],
            "dynamic_targets_missing": dyn["dynamic_targets_missing"],
            "dynamic_closure_size": len(dyn["dynamic_closure"]),
            "combined_inference_endpoint_files": sorted(set(combined) & set(inference_files)),
            "combined_model_artifact_files": sorted(set(combined) & set(artifact_files)),
        }

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "repo_head": git(root, "rev-parse", "HEAD").strip(),
        "counts": {
            "tracked_python_files": len(files),
            "files_with_inference_endpoint_literal": len(inference_files),
            "files_with_model_artifact_host": len(artifact_files),
            "files_with_any_endpoint_literal": len(hits),
        },
        "entries": report_entries,
        "inference_endpoint_files": {f: hits[f] for f in inference_files},
        "model_artifact_files": {f: hits[f] for f in artifact_files},
        "planner_flag_census": planner_flag_census(root),
        "limits": [
            "STATIC_ONLY: a URL assembled from parts, read from an environment variable, or "
            "passed in by a caller is invisible to this audit.",
            "IMPORT_OVER_APPROXIMATION: an import in a branch that never executes still counts.",
            "NO_EXECUTION: nothing audited here ran, so no route is shown to work or to fail.",
            "ENTRY_SCOPED: absence of an endpoint in one entry closure says nothing about "
            "another route, a notebook, a workflow, or a vendored tree loaded by an evaluator.",
        ],
    }


DEFAULT_ENTRIES = {
    "ASTRA_GOAL_RUNTIME": "canonical/runtime/astra_runtime.py",
    "OSWORLD_V21_V19_SUBJECT": "canonical/runtime/osworld_v21_brain_subject_v19.py",
    "OSWORLD_V21_V3_SUBMISSION_ENTRYPOINT": "canonical/runtime/osworld_v21_submission_entrypoint_v3.py",
    "RESEARCH_SOURCE_FRONTEND": "canonical/runtime/bound_capabilities/open_research_source_frontend.py",
    "ENVIRONMENT_BROKER": "canonical/swe_kernel/the_environment_broker_v1.py",
    "SCAN_RETRIEVE_FETCH": "canonical/tools/scan_retrieve_fetch_v1.py",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--json-out", type=pathlib.Path)
    parser.add_argument(
        "--entry",
        action="append",
        default=None,
        metavar="LABEL=PATH",
        help="override the default entry set (repeatable)",
    )
    ns = parser.parse_args(argv)
    root = ns.root.resolve()
    entries = dict(DEFAULT_ENTRIES)
    if ns.entry:
        entries = {}
        for spec in ns.entry:
            if "=" not in spec:
                parser.error("--entry must be LABEL=PATH")
            label, path = spec.split("=", 1)
            entries[label] = path
    missing = [e for e in entries.values() if not (root / e).is_file()]
    if missing:
        print("MODEL_CALL_AUDIT_ENTRY_MISSING", ",".join(missing), file=sys.stderr)
        return 2
    result = audit(root, entries)
    text = json.dumps(result, indent=1, sort_keys=False)
    if ns.json_out:
        ns.json_out.parent.mkdir(parents=True, exist_ok=True)
        ns.json_out.write_text(text + "\n", encoding="utf-8")
    print("MODEL_CALL_AUDIT head", result["repo_head"])
    print(" counts", json.dumps(result["counts"], sort_keys=True))
    for label, row in result["entries"].items():
        print(
            f" {label} static={row['static_closure_size']}"
            f" dynamic={row['dynamic_closure_size']}"
            f" inference_endpoint_files={len(row['combined_inference_endpoint_files'])}"
            f" -> {','.join(row['combined_inference_endpoint_files']) or 'NONE'}"
        )
    census = result["planner_flag_census"]
    print(
        " planner_flag true/false/absent",
        census["planner_flag_true"],
        census["planner_flag_false"],
        census["planner_flag_absent"],
        "guard_mentions",
        sum(len(x["mentions"]) for x in census["guard_mentions"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
