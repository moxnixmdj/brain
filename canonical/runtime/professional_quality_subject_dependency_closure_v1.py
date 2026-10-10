"""Professional-quality declared-system dependency closure compiler V1.

Starting from the current scoped-evidence reusable compilers, recursively derive
Brain-owned Python runtime dependencies and literal canonical configuration
files that can change mechanism behavior. Verification/evidence receipts remain
external unless executable code actually references them.

The compiler is diagnostic only. It grants no root, quality, acceptance,
promotion, ownership, or terminal authority.
"""
from __future__ import annotations

import ast
from collections import deque
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_V1"
REGISTRY_PATH = "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
WORKLIST_PATH = "canonical/governance/PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_WORKLIST_20261010_V1.json"

EXPECTED_ROOTS = (
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
)


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode("utf-8") + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "dependency_classification_authority": False,
        "root_subject_binding_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _resolve(root: Path, raw: str) -> Path | None:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        return None
    p = (root / raw).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p


def _read_json(root: Path, rel: str) -> dict[str, Any] | None:
    p = _resolve(root, rel)
    if p is None or not p.is_file() or p.is_symlink():
        return None
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _module_candidates(node: ast.AST) -> list[str]:
    modules: list[str] = []
    if isinstance(node, ast.Import):
        modules.extend(alias.name for alias in node.names if alias.name.startswith("canonical."))
    elif isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        if mod == "canonical.runtime":
            modules.extend(f"canonical.runtime.{alias.name}" for alias in node.names if alias.name != "*")
        elif mod.startswith("canonical."):
            modules.append(mod)
    return modules


def _module_to_rel(module: str) -> str:
    return module.replace(".", "/") + ".py"


def _scan_python(root: Path, rel: str) -> dict[str, Any]:
    path = _resolve(root, rel)
    if path is None or not path.is_file() or path.is_symlink():
        return {"ok": False, "reason": "RUNTIME_FILE_INVALID", "path": rel}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    except Exception as exc:
        return {"ok": False, "reason": "PYTHON_PARSE_FAILED", "path": rel, "error": type(exc).__name__}

    imports: set[str] = set()
    configs: set[str] = set()
    unresolved: set[str] = set()
    dynamic_import_seen = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for module in _module_candidates(node):
                candidate = _module_to_rel(module)
                p = _resolve(root, candidate)
                if p is not None and p.is_file() and not p.is_symlink():
                    imports.add(candidate)
                elif module.startswith("canonical.runtime"):
                    unresolved.add(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            raw = node.value
            if raw.startswith("canonical/") and raw.endswith((".json", ".py")):
                p = _resolve(root, raw)
                if p is not None and p.is_file() and not p.is_symlink():
                    configs.add(raw)
                else:
                    unresolved.add(raw)
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name in {"import_module", "__import__"}:
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    dynamic_import_seen = True

    return {
        "ok": True,
        "path": rel,
        "imports": sorted(imports),
        "literal_canonical_dependencies": sorted(configs),
        "unresolved": sorted(unresolved),
        "dynamic_import_seen": dynamic_import_seen,
    }


def _subject_from_worklist(root: Path, worklist: Mapping[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    candidate = worklist.get("candidate_subject")
    if not isinstance(candidate, Mapping):
        return None, None
    path = candidate.get("path")
    if not isinstance(path, str):
        return None, None
    return path, _read_json(root, path)


def compile_closure(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    registry = _read_json(root, REGISTRY_PATH)
    worklist = _read_json(root, WORKLIST_PATH)
    if registry is None or worklist is None:
        return _fail("CURRENT_REGISTRY_OR_WORKLIST_INVALID")

    subject_path, subject = _subject_from_worklist(root, worklist)
    if subject_path is None or subject is None:
        return _fail("CANDIDATE_SUBJECT_INVALID")
    material = subject.get("system_material")
    if not isinstance(material, Mapping):
        return _fail("CANDIDATE_SUBJECT_MATERIAL_INVALID")
    components = material.get("components")
    if not isinstance(components, list):
        return _fail("CANDIDATE_SUBJECT_COMPONENTS_INVALID")
    subject_components = {
        row.get("path")
        for row in components
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    }

    entries = registry.get("entries")
    if not isinstance(entries, list):
        return _fail("SCOPED_REGISTRY_ENTRIES_INVALID")

    by_root: dict[str, list[Mapping[str, Any]]] = {r: [] for r in EXPECTED_ROOTS}
    for entry in entries:
        if isinstance(entry, Mapping) and entry.get("root_id") in by_root:
            by_root[str(entry["root_id"])].append(entry)

    root_results: list[dict[str, Any]] = []
    global_missing: set[str] = set()
    global_unresolved: set[str] = set()

    for root_id in EXPECTED_ROOTS:
        rows = by_root[root_id]
        if not rows:
            return _fail("ROOT_SCOPED_SUPPORT_MISSING", root_id=root_id)

        initial: set[str] = set()
        external_evidence: set[str] = set()
        for row in rows:
            compiler = row.get("reusable_compiler")
            if isinstance(compiler, Mapping) and isinstance(compiler.get("path"), str):
                initial.add(str(compiler["path"]))
            for key in ("source_receipt", "scope_governance"):
                ref = row.get(key)
                if isinstance(ref, Mapping) and isinstance(ref.get("path"), str):
                    external_evidence.add(str(ref["path"]))

        queue = deque(sorted(initial))
        scanned: set[str] = set()
        system: set[str] = set(initial)
        unresolved: set[str] = set()
        dynamic: set[str] = set()
        scans: list[dict[str, Any]] = []

        while queue:
            rel = queue.popleft()
            if rel in scanned:
                continue
            scanned.add(rel)
            if not rel.endswith(".py"):
                continue
            result = _scan_python(root, rel)
            scans.append(result)
            if result.get("ok") is not True:
                unresolved.add(rel + "::" + str(result.get("reason")))
                continue
            for dep in result.get("imports", []):
                system.add(dep)
                if dep not in scanned:
                    queue.append(dep)
            for dep in result.get("literal_canonical_dependencies", []):
                system.add(dep)
                if dep.endswith(".py") and dep not in scanned:
                    queue.append(dep)
            unresolved.update(result.get("unresolved", []))
            if result.get("dynamic_import_seen") is True:
                dynamic.add(rel)

        missing = sorted(system - subject_components)
        global_missing.update(missing)
        global_unresolved.update(f"{root_id}:{x}" for x in unresolved)
        global_unresolved.update(f"{root_id}:DYNAMIC_IMPORT:{x}" for x in dynamic)

        root_results.append({
            "root_id": root_id,
            "scoped_support_count": len(rows),
            "entry_scope_ids": sorted(str(r.get("scope_id")) for r in rows),
            "system_material_dependencies": sorted(system),
            "already_in_subject": sorted(system & subject_components),
            "missing_subject_components": missing,
            "external_evidence_inputs": sorted(external_evidence - system),
            "unresolved_static_dependencies": sorted(unresolved),
            "dynamic_import_runtime_files": sorted(dynamic),
            "dependency_classification_complete": not unresolved and not dynamic,
            "scan_records": scans,
        })

    classification_complete = all(r["dependency_classification_complete"] for r in root_results)
    return _base(
        "PASS__STATIC_ROOT_DEPENDENCY_CLASSIFICATION_COMPLETE" if classification_complete else "OPEN__UNRESOLVED_DYNAMIC_OR_STATIC_DEPENDENCIES",
        passed=classification_complete,
        candidate_subject_path=subject_path,
        candidate_subject_git_blob_sha=git_blob_sha(_resolve(root, subject_path)),
        current_subject_component_count=len(subject_components),
        roots_total=len(root_results),
        roots_dependency_classified=sum(r["dependency_classification_complete"] for r in root_results),
        roots=root_results,
        unique_missing_subject_components=sorted(global_missing),
        unique_missing_subject_component_count=len(global_missing),
        unresolved_dependencies=sorted(global_unresolved),
        subject_dependency_closure_complete=classification_complete and not global_missing,
        external_receipts_do_not_become_subject_material_by_default=True,
    )


if __name__ == "__main__":
    print(json.dumps(compile_closure(), indent=2, sort_keys=True))
