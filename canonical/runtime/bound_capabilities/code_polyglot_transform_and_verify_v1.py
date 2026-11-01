"""Bound capability adapter `code.polyglot.transform_and_verify.v1`.

Compiler-, CST-, SQLite-, TOML-, Make-, and YAML-verified polyglot code, build,
and CI workflow transformer. Refuses closed with structured `RuntimeError`
whenever no defect/applicable transform exists or tool/schema verification fails.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.swe_kernel import polyglot_build_ci_engine_v1 as engine


def _safe_path(repo: pathlib.Path, raw: str, *, must_exist: bool = False) -> pathlib.Path:
    if not raw or not isinstance(raw, str):
        raise RuntimeError("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / raw).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + raw)
    if must_exist and not p.exists():
        raise RuntimeError("PATH_MISSING:" + raw)
    return p


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    op = str(args.get("operation") or "").strip()
    target_raw = str(args.get("target_path") or "").strip()
    out_raw = str(args.get("output_path") or "").strip()
    goal_spec = str(args.get("request_spec") or op).strip()

    if not op or not target_raw or not out_raw:
        raise RuntimeError("POLYGLOT_MISSING_REQUIRED_ARGUMENTS")

    must_exist = op not in {"create_pyproject", "create_ci_workflow", "create_sql_migration"}
    target = _safe_path(repo, target_raw, must_exist=must_exist)
    out_path = _safe_path(repo, out_raw, must_exist=False)

    if op in {"cpp_repair", "cpp_fix_off_by_one"}:
        res = engine.cpp_transform_and_verify(target, goal_spec)
    elif op == "rust_add_function":
        res = engine.rust_transform_and_verify(target, goal_spec)
    elif op == "go_add_function":
        res = engine.go_transform_and_verify(target, goal_spec)
    elif op == "java_add_method":
        res = engine.java_transform_and_verify(target, goal_spec)
    elif op in {"ts_rename_symbol", "ts_add_function"}:
        proj_raw = str(args.get("project_root") or "").strip()
        proj_dir = _safe_path(repo, proj_raw, must_exist=True) if proj_raw and proj_raw not in {".", "auto"} else target.parent
        res = engine.ts_transform_and_verify(target, goal_spec, project_root=proj_dir)
    elif op == "sql_ddl_transform":
        res = engine.sql_transform_and_verify(target, goal_spec)
    elif op in {"create_pyproject", "pyproject_add_dependency", "pyproject_pin_dependencies", "pyproject_bump_version", "requirements_add_dependency"}:
        if op == "requirements_add_dependency":
            import re as _re
            m_req = _re.search(r"\bdependency\s+`?([A-Za-z0-9_.-]+(?:[><=~!]+[0-9A-Za-z_.*+-]+)?)`?", goal_spec, _re.IGNORECASE)
            dep_pkg = m_req.group(1) if m_req else ""
            if not dep_pkg:
                raise RuntimeError("POLYGLOT_REFUSED:REQUIREMENTS_DEPENDENCY_NOT_STATED")
            req_dir = target if target.is_dir() else target.parent
            req_file = req_dir / "requirements.txt"
            existing_req = req_file.read_text(encoding="utf-8") if req_file.is_file() else ""
            if dep_pkg not in existing_req.splitlines():
                new_req = (existing_req.rstrip() + "\n" + dep_pkg + "\n").lstrip("\n")
                req_file.write_text(new_req, encoding="utf-8")
            res = {
                "verified": True,
                "gate": "PASS",
                "language": "requirements",
                "operation": "requirements_add_dependency",
                "dependency": dep_pkg,
                "target_file": str(req_file),
                "target_sha256": hashlib.sha256(req_file.read_bytes()).hexdigest(),
            }
        else:
            if op == "create_pyproject" and target.is_dir():
                proj_dir = target
                target = (target.parent if target.name in {"pkg", "app", "src"} else target) / "pyproject.toml"
            else:
                proj_dir = target.parent
            res = engine.pyproject_transform_and_verify(target, goal_spec, project_dir=proj_dir)
    elif op == "makefile_add_target":
        res = engine.makefile_transform_and_verify(target, goal_spec)
    elif op == "vendor_dependencies":
        proj_dir = (target.parent if target.name in {"pkg", "app", "src"} else target) if target.is_dir() else target.parent
        # The "is there anything to vendor" question belongs to the engine that reads the
        # manifest, not to a substring test on the file -- and its answer can be "no, and that
        # is fine", which is a verdict this adapter used to throw away by pre-refusing here.
        res = engine.vendor_dependencies_and_verify(proj_dir, goal_spec)
    elif op in {"create_ci_workflow", "ci_fix_workflow", "ci_add_matrix", "ci_add_cache"}:
        if target.is_dir():
            proj_dir = target.parent if target.name in {"tests", "pkg", "app", "src"} else target
            target = proj_dir / ".github" / "workflows" / "ci.yml"
        else:
            proj_dir = None
        res = engine.ci_workflow_transform_and_verify(target, goal_spec, project_dir=proj_dir)
    elif op == "quarantine_flaky_tests":
        res = engine.quarantine_flaky_tests(target)
    elif op == "build_wheel":
        res = engine.build_wheel_and_verify(target, goal_spec)
    elif op == "lock_requirements":
        res = engine.lock_requirements_and_verify(target, goal_spec)
    elif op == "create_sql_migration":
        res = engine.sql_migration_create_and_verify(target, goal_spec)
    elif op == "generate_sbom":
        res = engine.generate_cyclonedx_sbom_and_verify(target, goal_spec)
    elif op == "write_pr_description":
        res = engine.write_pr_description_and_verify(target, goal_spec)
    elif op in {"ts_generate_declarations", "port_python_to_js", "port_python_to_go", "port_python_to_rust"}:
        proj_raw = str(args.get("project_root") or "").strip()
        dest_p = None
        if op == "port_python_to_js" and proj_raw and proj_raw not in {".", "auto"} and proj_raw.endswith((".js", ".mjs")):
            dest_p = _safe_path(repo, proj_raw, must_exist=False)
        res = engine.polyglot_port_and_dts_verify(target, goal_spec, dest_path=dest_p)
    else:
        raise RuntimeError("POLYGLOT_UNSUPPORTED_OPERATION:" + op)

    if res.get("gate") == "ALREADY_SATISFIED":
        # AN ANSWER, NOT A REFUSAL, AND THE DOOR HAS A STATUS FOR IT.
        #
        # The engine proved the end state the sentence asks for already holds (measured, not
        # assumed: the declared dependency list it read).  Raising POLYGLOT_REFUSED here made the
        # door report a missing capability -- measured 2026-11-01, two of the advanced census's
        # fourteen refusals were requests whose work was already done.  The evidence rides on the
        # exception because the door's already-satisfied path is what records it.
        raise RuntimeError("ALREADY_SATISFIED:" + json.dumps(
            {"operation": op, "reason": str(res.get("reason") or "ALREADY_SATISFIED"),
             "evidence": res.get("evidence") or {}}, sort_keys=True))

    if not res.get("verified") or res.get("gate") != "PASS":
        raise RuntimeError("POLYGLOT_REFUSED:" + str(res.get("reason") or "UNVERIFIED"))

    written_target = pathlib.Path(str(res.get("target_file") or target)).resolve()
    if out_path == written_target:
        out_path = out_path.with_name(out_path.name + ".report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "PROJECT_BRAIN_POLYGLOT_TRANSFORM_VERIFY_V1",
        "adapter": "code_polyglot_transform_and_verify_v1",
        **res,
        "target_relpath": written_target.relative_to(repo).as_posix(),
        "output_verified": True,
    }
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(raw)
    return {
        **report,
        "output_path": out_path.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
    }
