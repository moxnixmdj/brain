from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_LOSSLESS_TASK_INGRESS_V1"
TASK_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
SECTION_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_SECTION_BYTES = 2_000_000


class IngressError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_rel(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IngressError(label + "_INVALID")
    raw = value.strip().replace("\\", "/")
    p = PurePosixPath(raw)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise IngressError(label + "_UNSAFE")
    return p.as_posix()


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise IngressError(label + "_INVALID")
    out = [_safe_rel(item, label + "_MEMBER") for item in value]
    if len(out) != len(set(out)):
        raise IngressError(label + "_DUPLICATE")
    return out


def _section_atoms(section_id: str, text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not SECTION_ID.fullmatch(section_id):
        raise IngressError("SECTION_ID_INVALID:" + section_id)
    if not isinstance(text, str) or not text.strip():
        raise IngressError("SECTION_TEXT_INVALID:" + section_id)
    raw = text.encode("utf-8")
    if len(raw) > MAX_SECTION_BYTES:
        raise IngressError("SECTION_TOO_LARGE:" + section_id)
    lines = text.splitlines(keepends=True)
    atoms = []
    byte_cursor = 0
    for line_number, line in enumerate(lines, 1):
        encoded = line.encode("utf-8")
        start = byte_cursor
        byte_cursor += len(encoded)
        if not line.strip():
            continue
        exact = line.rstrip("\r\n")
        material = f"{section_id}\0{line_number}\0{start}\0{byte_cursor}\0{exact}".encode("utf-8")
        atoms.append({
            "obligation_id": "AAO:" + _sha(material),
            "section_id": section_id,
            "line_number": line_number,
            "byte_start": start,
            "byte_end": byte_cursor,
            "text": exact,
            "text_sha256": _sha(exact.encode("utf-8")),
        })
    if not atoms:
        raise IngressError("SECTION_HAS_NO_NONEMPTY_OBLIGATIONS:" + section_id)
    meta = {
        "section_id": section_id,
        "raw_sha256": _sha(raw),
        "size_bytes": len(raw),
        "nonempty_line_count": len(atoms),
    }
    return atoms, meta


def inventory_source_roots(source_roots: Mapping[str, str | Path]) -> list[dict[str, Any]]:
    if not isinstance(source_roots, Mapping) or not source_roots:
        raise IngressError("SOURCE_ROOTS_REQUIRED")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for logical_root in sorted(source_roots):
        if logical_root not in {"shared", "week"}:
            raise IngressError("SOURCE_ROOT_LABEL_INVALID:" + str(logical_root))
        root = Path(source_roots[logical_root]).resolve()
        if not root.is_dir():
            raise IngressError("SOURCE_ROOT_NOT_DIRECTORY:" + logical_root)
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise IngressError("SOURCE_SYMLINK_FORBIDDEN:" + str(path))
            if not path.is_file():
                continue
            rel_inner = path.relative_to(root).as_posix()
            logical = _safe_rel(logical_root + "/" + rel_inner, "SOURCE_PATH")
            if logical in seen:
                raise IngressError("SOURCE_PATH_DUPLICATE:" + logical)
            seen.add(logical)
            raw = path.read_bytes()
            rows.append({
                "path": logical,
                "sha256": _sha(raw),
                "size_bytes": len(raw),
            })
    if not rows:
        raise IngressError("NO_MOUNTED_SOURCE_FILES")
    return rows


def compile_ingress(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise IngressError("BUNDLE_INVALID")
    task_id = bundle.get("task_id")
    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        raise IngressError("TASK_ID_INVALID")

    task_text = bundle.get("task_text")
    if not isinstance(task_text, str) or not task_text.strip():
        raise IngressError("TASK_TEXT_INVALID")

    context_sections = bundle.get("context_sections") or {}
    if not isinstance(context_sections, Mapping):
        raise IngressError("CONTEXT_SECTIONS_INVALID")
    sections: list[tuple[str, str]] = []
    for sid in sorted(context_sections):
        if sid == "task_brief":
            raise IngressError("TASK_BRIEF_SECTION_RESERVED")
        value = context_sections[sid]
        if not isinstance(sid, str) or not isinstance(value, str):
            raise IngressError("CONTEXT_SECTION_INVALID")
        sections.append((sid, value))
    sections.append(("task_brief", task_text))

    deliverables = _unique_strings(bundle.get("deliverables"), "DELIVERABLES")

    source_files = bundle.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        raise IngressError("SOURCE_FILES_REQUIRED")
    sources = []
    seen = set()
    for index, row in enumerate(source_files):
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256", "size_bytes"}:
            raise IngressError(f"SOURCE_ROW_FIELDS_INVALID:{index}")
        path = _safe_rel(row.get("path"), f"SOURCE_PATH:{index}")
        if path in seen:
            raise IngressError("SOURCE_PATH_DUPLICATE:" + path)
        seen.add(path)
        digest = row.get("sha256")
        size = row.get("size_bytes")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise IngressError("SOURCE_SHA256_INVALID:" + path)
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise IngressError("SOURCE_SIZE_INVALID:" + path)
        sources.append({"path": path, "sha256": digest, "size_bytes": size, "required": True})

    obligations: list[dict[str, Any]] = []
    section_manifest = []
    for sid, text in sections:
        atoms, meta = _section_atoms(sid, text)
        obligations.extend(atoms)
        section_manifest.append(meta)

    material = {
        "schema": SCHEMA,
        "task_id": task_id,
        "raw_task_sha256": next(x["raw_sha256"] for x in section_manifest if x["section_id"] == "task_brief"),
        "context_sections": section_manifest,
        "context_set_sha256": _sha(_canon(section_manifest)),
        "deliverables": sorted(deliverables),
        "source_files": sorted(sources, key=lambda x: x["path"]),
        "obligations": obligations,
        "obligation_count": len(obligations),
        "source_count": len(sources),
        "deliverable_count": len(deliverables),
        "all_nonempty_context_and_task_lines_preserved_exactly": True,
        "all_declared_source_files_preserved_by_path_hash_and_size": True,
        "semantic_completeness_claimed": False,
        "hidden_rubric_information_used": False,
        "terminal_authority": False,
    }
    return {**material, "ingress_sha256": _sha(_canon(material))}


def compile_harness_ingress(
    *,
    task_id: str,
    scenario_overview: str,
    week_overview: str,
    task_brief: str,
    deliverables: Sequence[str],
    shared_root: str | Path,
    week_root: str | Path,
) -> dict[str, Any]:
    source_files = inventory_source_roots({"shared": shared_root, "week": week_root})
    return compile_ingress({
        "task_id": task_id,
        "task_text": task_brief,
        "context_sections": {
            "scenario_overview": scenario_overview,
            "week_overview": week_overview,
        },
        "deliverables": list(deliverables),
        "source_files": source_files,
    })
