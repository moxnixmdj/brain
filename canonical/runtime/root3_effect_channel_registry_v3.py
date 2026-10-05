"""Root3 C1 V3 finite effect-carrier classifier.

This is a zero-credit classifier. It computes the recursive repo-local import
closure from the current C1 V2 runtime roots, binds declared carrier modules to
exact git blobs, and fails closed on newly observed network, subprocess,
filesystem-mutation, non-stdlib-import, or unconstrained dynamic-import edges.
It does not prove mediation or graph dominance.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_C1_EFFECT_CARRIER_CLASSIFIER_V3"
MANIFEST_SCHEMA = "PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V3"


class C1Error(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _qname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qname(node.value)
        return None if parent is None else parent + "." + node.attr
    return None


def _module_to_local_path(root: Path, module: str) -> Path | None:
    top = module.split(".")[0]
    candidates = [
        root / "canonical" / "runtime" / (top + ".py"),
        root / "canonical" / "runtime" / top / "__init__.py",
    ]
    if module.startswith("canonical.runtime."):
        rel = module[len("canonical.runtime."):].replace(".", "/")
        candidates = [
            root / "canonical" / "runtime" / (rel + ".py"),
            root / "canonical" / "runtime" / rel / "__init__.py",
        ] + candidates
    for p in candidates:
        if p.is_file():
            return p.resolve()
    return None


def _imports(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def _calls(tree: ast.Module) -> list[tuple[str, ast.Call]]:
    out: list[tuple[str, ast.Call]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            q = _qname(node.func)
            if q:
                out.append((q, node))
    return out


def _write_effect(q: str, node: ast.Call) -> bool:
    if q.endswith((".write_text", ".write_bytes", ".mkdir", ".unlink", ".rename", ".touch", ".save")):
        return True
    if q in {"sqlite3.connect", "xlsxwriter.Workbook"}:
        return True
    if q == "open":
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
            return any(ch in node.args[1].value for ch in "wax+")
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return any(ch in kw.value.value for ch in "wax+")
    return False


def _seed_paths(root: Path, parent: dict[str, Any]) -> set[Path]:
    e = parent["expected_repo_dynamic_universe"]
    rels = set(e["fixed_loader_sites"].values())
    rels.update("canonical/runtime/" + x + ".py" for x in e["literal_runtime_helpers"])
    rels.update("canonical/runtime/bound_capabilities/" + x + ".py" for x in e["ordinary_adapter_modules"])
    rels.add(parent["subject"]["astra_runtime"]["path"])
    out = set()
    for rel in rels:
        p = (root / rel).resolve()
        if not p.is_file():
            raise C1Error("SEED_FILE_MISSING:" + rel)
        out.add(p)
    return out


def _recursive_closure(root: Path, seeds: set[Path]) -> set[Path]:
    seen: set[Path] = set()
    queue = list(seeds)
    while queue:
        p = queue.pop()
        if p in seen:
            continue
        seen.add(p)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except Exception as exc:
            raise C1Error("AST_PARSE_FAILED:" + str(p.relative_to(root)) + ":" + type(exc).__name__) from exc
        for module in _imports(tree):
            local = _module_to_local_path(root, module)
            if local is not None and local not in seen:
                queue.append(local)
    return seen


def _declared_blob_map(manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("network_modules", "child_process_modules", "local_filesystem_write_modules"):
        for path, sha in manifest.get(key, {}).items():
            prior = out.get(path)
            if prior is not None and prior != sha:
                raise C1Error("DECLARED_BLOB_CONFLICT:" + path)
            out[path] = sha
    for path in manifest.get("inprocess_third_party_imports", {}):
        if path not in out:
            # third-party-only modules may be read-only, so bind their exact current blob here.
            psha = manifest.get("third_party_module_blobs", {}).get(path)
            if psha:
                out[path] = psha
    return out


def audit(repo_root: str | Path, manifest_rel: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    manifest_path = (root / manifest_rel).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise C1Error("MANIFEST_SCHEMA_INVALID")

    parent_info = manifest["parent"]
    parent_path = (root / parent_info["path"]).resolve()
    parent_raw = parent_path.read_bytes()
    if git_blob_sha(parent_raw) != parent_info["git_blob_sha"]:
        raise C1Error("PARENT_BLOB_DRIFT")
    parent = json.loads(parent_raw.decode("utf-8"))

    reg_info = manifest["bound_registry"]
    reg_path = (root / reg_info["path"]).resolve()
    reg_raw = reg_path.read_bytes()
    if git_blob_sha(reg_raw) != reg_info["git_blob_sha"]:
        raise C1Error("REGISTRY_BLOB_DRIFT")
    registry = json.loads(reg_raw.decode("utf-8"))

    seeds = _seed_paths(root, parent)
    closure = _recursive_closure(root, seeds)

    network_decl = set(manifest.get("network_modules", {}))
    child_decl = set(manifest.get("child_process_modules", {}))
    write_decl = set(manifest.get("local_filesystem_write_modules", {}))
    third_decl = {k: set(v) for k, v in manifest.get("inprocess_third_party_imports", {}).items()}

    network_observed: set[str] = set()
    child_observed: set[str] = set()
    write_observed: set[str] = set()
    third_observed: dict[str, set[str]] = {}
    dynamic_import_modules: set[str] = set()

    stdlib = set(getattr(sys, "stdlib_module_names", set()))
    local_top = {p.stem for p in (root / "canonical" / "runtime").glob("*.py")}

    for p in sorted(closure):
        rel = p.relative_to(root).as_posix()
        raw = p.read_bytes()
        declared_sha = _declared_blob_map(manifest).get(rel)
        if declared_sha is not None and git_blob_sha(raw) != declared_sha:
            raise C1Error("DECLARED_MODULE_BLOB_DRIFT:" + rel)

        tree = ast.parse(raw.decode("utf-8"), filename=rel)
        imports = _imports(tree)
        external = set()
        for module in imports:
            top = module.split(".")[0]
            if top in stdlib or top in {"canonical"} or top in local_top:
                continue
            if _module_to_local_path(root, module) is not None:
                continue
            external.add(top)
        if external:
            third_observed[rel] = external

        for q, node in _calls(tree):
            if q in {
                "urllib.request.urlopen",
                "socket.socket",
                "requests.get", "requests.post", "requests.request",
                "httpx.get", "httpx.post", "httpx.request",
            }:
                network_observed.add(rel)
            if q in {
                "subprocess.run", "subprocess.Popen",
                "subprocess.check_call", "subprocess.check_output",
                "os.system", "os.popen",
            }:
                child_observed.add(rel)
            if _write_effect(q, node):
                write_observed.add(rel)
            if q == "importlib.import_module":
                dynamic_import_modules.add(rel)

    errors = []
    if network_observed - network_decl:
        errors.append("UNCLASSIFIED_NETWORK:" + ",".join(sorted(network_observed - network_decl)))
    if child_observed - child_decl:
        errors.append("UNCLASSIFIED_CHILD_PROCESS:" + ",".join(sorted(child_observed - child_decl)))
    if write_observed - write_decl:
        errors.append("UNCLASSIFIED_LOCAL_WRITE:" + ",".join(sorted(write_observed - write_decl)))

    all_third_paths = set(third_observed) | set(third_decl)
    for rel in sorted(all_third_paths):
        obs = third_observed.get(rel, set())
        dec = third_decl.get(rel, set())
        if obs != dec:
            errors.append(
                "THIRD_PARTY_IMPORT_SET_MISMATCH:" + rel + ":OBS=" + ",".join(sorted(obs)) + ":DECL=" + ",".join(sorted(dec))
            )

    allowed_dynamic = set(manifest.get("registry_constrained_dynamic_imports", {}))
    if dynamic_import_modules - allowed_dynamic:
        errors.append("UNCLASSIFIED_DYNAMIC_IMPORT:" + ",".join(sorted(dynamic_import_modules - allowed_dynamic)))

    # Prove registry-constrained dynamic imports are literal at the credited call boundary.
    caps = registry.get("capabilities", {})
    for rel, rows in manifest.get("registry_constrained_dynamic_imports", {}).items():
        for row in rows:
            adapter = row["adapter_module"]
            expected = (row["module"], row["factory"])
            matched = []
            for cid, entry in caps.items():
                if entry.get("adapter_module") != adapter:
                    continue
                args = (entry.get("action_template") or {}).get("args") or {}
                matched.append((cid, args.get("module"), args.get("factory")))
            if not matched:
                errors.append("DYNAMIC_ADAPTER_UNUSED:" + adapter)
            for cid, module, factory in matched:
                if (module, factory) != expected:
                    errors.append("DYNAMIC_IMPORT_REGISTRY_MISMATCH:" + cid)

    status = "PASS__FINITE_CARRIER_CLASSIFICATION" if not errors else "FAIL_CLOSED__C1_CLASSIFICATION_MISMATCH"
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": not errors,
        "repo_local_import_closure_file_count": len(closure),
        "network_modules_observed": sorted(network_observed),
        "child_process_modules_observed": sorted(child_observed),
        "local_filesystem_write_modules_observed": sorted(write_observed),
        "inprocess_third_party_imports_observed": {k: sorted(v) for k, v in sorted(third_observed.items())},
        "dynamic_import_modules_observed": sorted(dynamic_import_modules),
        "errors": errors,
        "c1_scope_complete": False,
        "remaining": [
            "C2_MEDIATOR_BINDINGS",
            "NONREPO_LIBRARY_INTERNAL_EFFECT_MEDIATION_OR_SANDBOX_BOUNDARY",
            "CHILD_PROCESS_INTERNAL_EFFECT_MEDIATION_OR_SANDBOX_BOUNDARY",
            "EXTERNAL_TOOL_BRIDGE_EFFECT_MEDIATION",
            "C3_DOMINATOR_PROOF",
            "C4_EXACT_RUNTIME_BIND",
            "C5_INDEPENDENT_RECEIPT"
        ],
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--manifest",
        default="canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V3.json",
    )
    ns = ap.parse_args()
    try:
        out = audit(ns.repo_root, ns.manifest)
        print(json.dumps(out, indent=2, sort_keys=True))
        raise SystemExit(0 if out["pass"] else 2)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__C1_AUDITOR_ERROR",
            "pass": False,
            "error": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }, indent=2, sort_keys=True))
        raise SystemExit(3)
