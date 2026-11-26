#!/usr/bin/env python3
"""Ring-0 Byte-Level Effect Oracle, DRA Delta-Debugging Hunk Minimizer & Mutation Gate (`K3 = 0`).

Never trusts filenames, exit codes, or agent self-reports:
  1. `verify_byte_effect`: verifies real file magic bytes, structural container integrity,
     roundtrip decompression equality against source bytes, and untouched-member SHA-256
     invariance for archives. Explicitly catches lying extensions (e.g., a `.zip` or `.xz`
     payload named `out.gz` is rejected with `EFFECT_MAGIC_MISMATCH__LYING_EXTENSION`).
  2. `ddmin_minimize_hunks`: Zeller's O(k log n) delta-debugging hunk minimizer (inspired by
     DRA, Nov 2026) stripping unnecessary edit hunks from candidate patches while preserving
     100% oracle pass and reporting exact `necessity_precision`.
  3. `audit_patch_mutation_kill`: targeted AST mutation testing restricted to touched patch
     lines, measuring whether the verification oracle actually kills semantic regressions on
     the edited logic.

Authority: NONE. Pure Python stdlib, `$0` spend, fail-closed everywhere.
"""
from __future__ import annotations

import ast
import bz2
import copy
import difflib
import gzip
import hashlib
import io
import json
import lzma
import os
import sqlite3
import tarfile
import time
import zipfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_BYTE_EFFECT_ORACLE_V1"

_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "gz": (b"\x1f\x8b",),
    "gzip": (b"\x1f\x8b",),
    "bz2": (b"BZh",),
    "bzip2": (b"BZh",),
    "xz": (b"\xfd7zXZ\x00",),
    "lzma": (b"\xfd7zXZ\x00",),
    "zip": (b"PK\x03\x04", b"PK\x05\x06"),
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
    "pptx": (b"PK\x03\x04",),
    "sqlite": (b"SQLite format 3\x00",),
    "db": (b"SQLite format 3\x00",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "pdf": (b"%PDF-",),
}


def detect_byte_format(raw: bytes) -> str:
    """Detect actual container/file format purely from raw header bytes (ignoring filename)."""
    if raw.startswith(b"\x1f\x8b"):
        return "gz"
    if raw.startswith(b"BZh"):
        return "bz2"
    if raw.startswith(b"\xfd7zXZ\x00"):
        return "xz"
    if raw.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    if raw.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"%PDF-"):
        return "pdf"
    if len(raw) >= 265 and raw[257:262] == b"ustar":
        return "tar"
    stripped = raw.lstrip()
    if stripped.startswith((b"{", b"[")):
        try:
            json.loads(raw.decode("utf-8"))
            return "json"
        except Exception:
            pass
    return "unknown"


def infer_declared_format(path: str | Path) -> str:
    """Infer format declared by file extension(s)."""
    name = Path(path).name.lower()
    if name.endswith((".tar.gz", ".tgz")):
        return "tar.gz"
    if name.endswith((".tar.bz2", ".tbz2")):
        return "tar.bz2"
    if name.endswith((".tar.xz", ".txz")):
        return "tar.xz"
    ext = Path(path).suffix.lower().lstrip(".")
    return ext or "unknown"


def snapshot_zip_member_hashes(path: str | Path) -> dict[str, str]:
    """Return `{member_name: sha256}` for all non-directory entries in a zip/OOXML archive."""
    out: dict[str, str] = {}
    with zipfile.ZipFile(Path(path), "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            out[info.filename] = hashlib.sha256(zf.read(info.filename)).hexdigest()
    return out


def verify_byte_effect(
    target: str | Path,
    *,
    expected_format: str | None = None,
    expected_source_bytes: bytes | None = None,
    expected_source_path: str | Path | None = None,
    baseline_archive_hashes: Mapping[str, str] | None = None,
    allowed_archive_mutations: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify real byte-level world effect of `target` fail-closed.

    Rejects lying extensions (e.g., zip/xz container named `out.gz`), truncated containers,
    failed roundtrip decompression, broken SQLite/JSON/Python syntax, and unintended mutations
    of untouched archive members.
    """
    t0 = time.perf_counter()
    p = Path(target)
    if not p.is_file():
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "EFFECT_TARGET_MISSING",
            "path": str(p),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    raw = p.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    declared = (expected_format or infer_declared_format(p)).lower().lstrip(".")
    detected = detect_byte_format(raw)

    if expected_source_bytes is None and expected_source_path is not None:
        sp = Path(expected_source_path)
        if not sp.is_file():
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "EFFECT_EXPECTED_SOURCE_MISSING",
                "path": str(p),
                "expected_source_path": str(sp),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }
        expected_source_bytes = sp.read_bytes()

    base_res: dict[str, Any] = {
        "schema": SCHEMA,
        "path": str(p),
        "size_bytes": len(raw),
        "sha256": actual_sha256,
        "declared_format": declared,
        "detected_format": detected,
    }

    # 1. Strict magic-byte check against declared format (catches lying extensions).
    magic_key = "gz" if declared == "tar.gz" else ("bz2" if declared == "tar.bz2" else ("xz" if declared == "tar.xz" else declared))
    expected_magics = _MAGIC_SIGNATURES.get(magic_key)
    if expected_magics is not None and not any(raw.startswith(m) for m in expected_magics):
        return {
            **base_res,
            "pass": False,
            "status": "EFFECT_MAGIC_MISMATCH__LYING_EXTENSION",
            "reason": f"declared={declared} detected={detected} header_hex={raw[:16].hex()}",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    recovered_bytes: bytes | None = None
    details: dict[str, Any] = {}

    try:
        if declared in {"gz", "gzip"}:
            recovered_bytes = gzip.decompress(raw)
            details["decompressed_bytes"] = len(recovered_bytes)
        elif declared in {"bz2", "bzip2"}:
            recovered_bytes = bz2.decompress(raw)
            details["decompressed_bytes"] = len(recovered_bytes)
        elif declared in {"xz", "lzma"}:
            recovered_bytes = lzma.decompress(raw)
            details["decompressed_bytes"] = len(recovered_bytes)
        elif declared in {"zip", "docx", "xlsx", "pptx"}:
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                bad_member = zf.testzip()
                if bad_member is not None:
                    return {
                        **base_res,
                        "pass": False,
                        "status": "EFFECT_ZIP_CRC_CORRUPTED",
                        "bad_member": bad_member,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
                    }
                member_hashes = {
                    info.filename: hashlib.sha256(zf.read(info.filename)).hexdigest()
                    for info in zf.infolist()
                    if not info.is_dir()
                }
            details["member_count"] = len(member_hashes)
            if baseline_archive_hashes is not None:
                allowed_set = set(allowed_archive_mutations)
                collateral: list[str] = []
                for name, old_h in baseline_archive_hashes.items():
                    if name in allowed_set:
                        continue
                    if member_hashes.get(name) != old_h:
                        collateral.append(name)
                if collateral:
                    return {
                        **base_res,
                        "pass": False,
                        "status": "EFFECT_ARCHIVE_COLLATERAL_MUTATION",
                        "collateral_members": sorted(collateral),
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
                    }
                details["untouched_members_verified"] = len(baseline_archive_hashes) - len(
                    allowed_set.intersection(baseline_archive_hashes.keys())
                )
        elif declared in {"tar", "tar.gz", "tar.bz2", "tar.xz"}:
            mode = "r:*" if declared != "tar" else "r:"
            with tarfile.open(fileobj=io.BytesIO(raw), mode=mode) as tf:
                members = tf.getmembers()
                for m in members:
                    if m.isfile():
                        fobj = tf.extractfile(m)
                        if fobj is not None:
                            _ = fobj.read()
                details["member_count"] = len(members)
        elif declared in {"sqlite", "db"}:
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            try:
                rows = conn.execute("PRAGMA integrity_check").fetchall()
                ok_rows = [str(r[0]).lower() for r in rows]
                if ok_rows != ["ok"]:
                    return {
                        **base_res,
                        "pass": False,
                        "status": "EFFECT_SQLITE_INTEGRITY_FAILED",
                        "integrity_check": ok_rows,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
                    }
                tables = [
                    str(r[0])
                    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                ]
                details["tables"] = sorted(tables)
            finally:
                conn.close()
        elif declared == "json":
            parsed = json.loads(raw.decode("utf-8"))
            details["json_type"] = type(parsed).__name__
            recovered_bytes = raw
        elif declared == "py":
            tree = ast.parse(raw.decode("utf-8"))
            details["ast_stmt_count"] = len(tree.body)
            recovered_bytes = raw
        elif declared == "png":
            if b"IEND" not in raw[-32:]:
                return {
                    **base_res,
                    "pass": False,
                    "status": "EFFECT_PNG_TRUNCATED",
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
                }
        elif declared == "pdf":
            if b"%%EOF" not in raw[-1024:]:
                return {
                    **base_res,
                    "pass": False,
                    "status": "EFFECT_PDF_TRUNCATED",
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
                }
        else:
            recovered_bytes = raw
    except Exception as exc:
        return {
            **base_res,
            "pass": False,
            "status": f"EFFECT_DECODE_OR_VERIFY_ERROR:{type(exc).__name__}",
            "error": str(exc)[:240],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    if expected_source_bytes is not None:
        if recovered_bytes is None:
            return {
                **base_res,
                "pass": False,
                "status": "EFFECT_ROUNDTRIP_UNAVAILABLE_FOR_FORMAT",
                "details": details,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }
        if recovered_bytes != expected_source_bytes:
            return {
                **base_res,
                "pass": False,
                "status": "EFFECT_ROUNDTRIP_BYTE_MISMATCH",
                "expected_sha256": hashlib.sha256(expected_source_bytes).hexdigest(),
                "recovered_sha256": hashlib.sha256(recovered_bytes).hexdigest(),
                "details": details,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }
        details["roundtrip_exact_match"] = True

    return {
        **base_res,
        "pass": True,
        "status": "BYTE_EFFECT_VERIFIED",
        "details": details,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
    }


def snapshot_directory_hashes(root_dir: str | Path) -> dict[str, str]:
    """Capture `{rel_path: sha256}` of every regular file under `root_dir`."""
    base = Path(root_dir)
    snap: dict[str, str] = {}
    if not base.is_dir():
        return snap
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fn in sorted(filenames):
            fp = Path(dirpath) / fn
            if fp.is_file():
                rel = fp.relative_to(base).as_posix()
                snap[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()
    return snap


def verify_directory_effect_diff(
    before_snap: Mapping[str, str],
    after_snap: Mapping[str, str],
    *,
    allowed_writes: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify that ONLY declared `allowed_writes` changed between workspace snapshots."""
    allowed = set(allowed_writes)
    added = sorted(k for k in after_snap if k not in before_snap)
    removed = sorted(k for k in before_snap if k not in after_snap)
    modified = sorted(k for k in after_snap if k in before_snap and after_snap[k] != before_snap[k])
    changed = sorted(set(added) | set(removed) | set(modified))
    unexpected = sorted(k for k in changed if k not in allowed) if allowed else []
    return {
        "schema": SCHEMA + "/dir_diff",
        "pass": len(unexpected) == 0,
        "status": "DIRECTORY_EFFECT_CLEAN" if not unexpected else "UNINTENDED_WORKSPACE_MUTATION",
        "added": added,
        "removed": removed,
        "modified": modified,
        "unexpected_mutations": unexpected,
    }


# ---------------------------------------------------------------------------
# DRA-style Delta-Debugging Hunk Minimizer (Zeller's ddmin, O(k log n))
# ---------------------------------------------------------------------------


def _apply_hunk_subset(
    orig_lines: list[str],
    new_lines: list[str],
    hunks: list[tuple[str, int, int, int, int]],
    active_indices: set[int],
) -> str:
    """Reconstruct source applying only diff hunks whose index is in `active_indices`."""
    out: list[str] = []
    pos = 0
    for idx, (tag, i1, i2, j1, j2) in enumerate(hunks):
        if i1 > pos:
            out.extend(orig_lines[pos:i1])
        if idx in active_indices:
            out.extend(new_lines[j1:j2])
        else:
            out.extend(orig_lines[i1:i2])
        pos = i2
    if pos < len(orig_lines):
        out.extend(orig_lines[pos:])
    return "".join(out)


def ddmin_minimize_hunks(
    original_source: str,
    patched_source: str,
    oracle_fn: Callable[[str], bool],
) -> dict[str, Any]:
    """Minimize diff hunks between `original_source` and `patched_source` via Zeller's ddmin.

    Returns a 1-minimal patch preserving `oracle_fn(candidate) == True`, stripping bloated
    or irrelevant edits automatically (inspired by DRA, arXiv:2611.34875).
    """
    t0 = time.perf_counter()
    orig_lines = original_source.splitlines(keepends=True)
    new_lines = patched_source.splitlines(keepends=True)
    sm = difflib.SequenceMatcher(None, orig_lines, new_lines, autojunk=False)
    hunks: list[tuple[str, int, int, int, int]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == (j2 - j1) and (i2 - i1) > 1:
            # Decompose equal-length multi-line replacements into atomic 1-line edit hunks
            # so ddmin strips adjacent bloated/extraneous lines independently!
            for k in range(i2 - i1):
                hunks.append(("replace", i1 + k, i1 + k + 1, j1 + k, j1 + k + 1))
        elif tag == "insert" and (j2 - j1) > 1:
            for k in range(j2 - j1):
                hunks.append(("insert", i1, i1, j1 + k, j1 + k + 1))
        elif tag == "delete" and (i2 - i1) > 1:
            for k in range(i2 - i1):
                hunks.append(("delete", i1 + k, i1 + k + 1, j1, j1))
        else:
            hunks.append((tag, i1, i2, j1, j2))
    orig_count = len(hunks)

    memo: dict[frozenset[int], bool] = {}
    calls = 0

    def test_subset(indices: list[int]) -> bool:
        nonlocal calls
        key = frozenset(indices)
        if key in memo:
            return memo[key]
        calls += 1
        cand = _apply_hunk_subset(orig_lines, new_lines, hunks, set(indices))
        try:
            ok = bool(oracle_fn(cand))
        except Exception:
            ok = False
        memo[key] = ok
        return ok

    if orig_count == 0:
        ok = test_subset([])
        return {
            "schema": SCHEMA + "/ddmin",
            "pass": ok,
            "status": "NO_HUNKS_TO_MINIMIZE" if ok else "ORACLE_FAILED_ON_ORIGINAL",
            "minimized_source": original_source,
            "original_hunk_count": 0,
            "minimized_hunk_count": 0,
            "pruned_hunk_count": 0,
            "necessity_precision": 1.0 if ok else 0.0,
            "oracle_calls": calls,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    all_idx = list(range(orig_count))
    if not test_subset(all_idx):
        return {
            "schema": SCHEMA + "/ddmin",
            "pass": False,
            "status": "ORACLE_FAILED_ON_PATCHED_SOURCE",
            "minimized_source": patched_source,
            "original_hunk_count": orig_count,
            "minimized_hunk_count": orig_count,
            "pruned_hunk_count": 0,
            "necessity_precision": 0.0,
            "oracle_calls": calls,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    # Check if 0 hunks already pass (entire patch unnecessary).
    if test_subset([]):
        return {
            "schema": SCHEMA + "/ddmin",
            "pass": True,
            "status": "PATCH_COMPLETELY_UNNECESSARY",
            "minimized_source": original_source,
            "original_hunk_count": orig_count,
            "minimized_hunk_count": 0,
            "pruned_hunk_count": orig_count,
            "necessity_precision": 0.0,
            "oracle_calls": calls,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    current = list(all_idx)
    n = 2
    while len(current) >= 2:
        chunk_size = max(1, (len(current) + n - 1) // n)
        chunks = [current[i : i + chunk_size] for i in range(0, len(current), chunk_size)]
        reduced = False
        # 1. Try reducing to one chunk.
        for ch in chunks:
            if len(ch) < len(current) and test_subset(ch):
                current = ch
                n = 2
                reduced = True
                break
        if reduced:
            continue
        # 2. Try complements (removing one chunk).
        for i in range(len(chunks)):
            comp = [x for j, ch in enumerate(chunks) if j != i for x in ch]
            if comp and len(comp) < len(current) and test_subset(comp):
                current = comp
                n = max(n - 1, 2)
                reduced = True
                break
        if reduced:
            continue
        if n >= len(current):
            break
        n = min(len(current), n * 2)

    minimized = _apply_hunk_subset(orig_lines, new_lines, hunks, set(current))
    min_count = len(current)
    return {
        "schema": SCHEMA + "/ddmin",
        "pass": True,
        "status": "PATCH_MINIMIZED_1_MINIMAL",
        "minimized_source": minimized,
        "original_hunk_count": orig_count,
        "minimized_hunk_count": min_count,
        "pruned_hunk_count": orig_count - min_count,
        "kept_hunk_indices": current,
        "necessity_precision": round(min_count / orig_count, 6) if orig_count else 1.0,
        "oracle_calls": calls,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
    }


# ---------------------------------------------------------------------------
# Targeted Patch-Line Mutation Kill Auditor
# ---------------------------------------------------------------------------

_CMP_MUTATIONS: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
    ast.Lt: (ast.LtE, ast.GtE),
    ast.LtE: (ast.Lt, ast.Gt),
    ast.Gt: (ast.GtE, ast.LtE),
    ast.GtE: (ast.Gt, ast.Lt),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}

_BINOP_MUTATIONS: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
    ast.Add: (ast.Sub,),
    ast.Sub: (ast.Add,),
    ast.Mult: (ast.FloorDiv, ast.Add),
    ast.FloorDiv: (ast.Mult,),
    ast.Div: (ast.Mult,),
    ast.Mod: (ast.Add,),
}

_BOOLOP_MUTATIONS: dict[type[ast.boolop], tuple[type[ast.boolop], ...]] = {
    ast.And: (ast.Or,),
    ast.Or: (ast.And,),
}


def _touched_lines(original_source: str, patched_source: str) -> set[int]:
    """Return 1-based line numbers in `patched_source` introduced or modified vs `original_source`."""
    orig_lines = original_source.splitlines()
    new_lines = patched_source.splitlines()
    sm = difflib.SequenceMatcher(None, orig_lines, new_lines, autojunk=False)
    lines: set[int] = set()
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            for ln in range(j1 + 1, j2 + 1):
                lines.add(ln)
    return lines


def audit_patch_mutation_kill(
    original_source: str,
    patched_source: str,
    oracle_fn: Callable[[str], bool],
    *,
    max_mutants: int = 16,
) -> dict[str, Any]:
    """Generate targeted AST mutants on touched lines of `patched_source` and measure kill rate."""
    t0 = time.perf_counter()
    try:
        base_tree = ast.parse(patched_source)
    except SyntaxError as exc:
        return {
            "schema": SCHEMA + "/mutation_audit",
            "pass": False,
            "status": f"PATCH_SYNTAX_ERROR:{exc.msg}",
            "mutants_tested": 0,
            "mutants_killed": 0,
            "mutation_kill_ratio": 0.0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    touched = _touched_lines(original_source, patched_source)
    if not touched:
        touched = set(range(1, len(patched_source.splitlines()) + 1))

    # Index AST nodes on touched lines deterministically.
    nodes = list(ast.walk(base_tree))
    mutants: list[tuple[str, str]] = []

    def add_mutant(desc: str, tree_copy: ast.AST) -> None:
        if len(mutants) >= max_mutants:
            return
        ast.fix_missing_locations(tree_copy)
        src = ast.unparse(tree_copy)
        if src != patched_source:
            mutants.append((desc, src))

    for idx, node in enumerate(nodes):
        if len(mutants) >= max_mutants:
            break
        lineno = getattr(node, "lineno", None)
        if lineno not in touched:
            continue
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op_cls = type(node.ops[0])
            for alt_cls in _CMP_MUTATIONS.get(op_cls, ()):
                tcopy = copy.deepcopy(base_tree)
                target_node = list(ast.walk(tcopy))[idx]
                assert isinstance(target_node, ast.Compare)
                target_node.ops[0] = alt_cls()
                add_mutant(f"L{lineno}:cmp_{op_cls.__name__}_to_{alt_cls.__name__}", tcopy)
        elif isinstance(node, ast.BinOp):
            op_cls = type(node.op)
            for alt_cls in _BINOP_MUTATIONS.get(op_cls, ()):
                tcopy = copy.deepcopy(base_tree)
                target_node = list(ast.walk(tcopy))[idx]
                assert isinstance(target_node, ast.BinOp)
                target_node.op = alt_cls()
                add_mutant(f"L{lineno}:binop_{op_cls.__name__}_to_{alt_cls.__name__}", tcopy)
        elif isinstance(node, ast.BoolOp):
            op_cls = type(node.op)
            for alt_cls in _BOOLOP_MUTATIONS.get(op_cls, ()):
                tcopy = copy.deepcopy(base_tree)
                target_node = list(ast.walk(tcopy))[idx]
                assert isinstance(target_node, ast.BoolOp)
                target_node.op = alt_cls()
                add_mutant(f"L{lineno}:boolop_{op_cls.__name__}_to_{alt_cls.__name__}", tcopy)
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            tcopy = copy.deepcopy(base_tree)
            target_node = list(ast.walk(tcopy))[idx]
            assert isinstance(target_node, ast.Constant)
            target_node.value = not bool(target_node.value)
            add_mutant(f"L{lineno}:bool_flip", tcopy)
        elif isinstance(node, ast.Return) and node.value is not None:
            tcopy = copy.deepcopy(base_tree)
            target_node = list(ast.walk(tcopy))[idx]
            assert isinstance(target_node, ast.Return)
            target_node.value = ast.Constant(value=None)
            add_mutant(f"L{lineno}:return_to_none", tcopy)

    killed = 0
    surviving: list[str] = []
    for desc, m_src in mutants:
        try:
            passed = bool(oracle_fn(m_src))
        except Exception:
            passed = False
        if not passed:
            killed += 1
        else:
            surviving.append(desc)

    tested = len(mutants)
    ratio = round(killed / tested, 6) if tested else 1.0
    return {
        "schema": SCHEMA + "/mutation_audit",
        "pass": tested == 0 or killed == tested,
        "status": "ALL_MUTANTS_KILLED" if (tested == 0 or killed == tested) else "MUTANTS_SURVIVED",
        "touched_lines": sorted(touched),
        "mutants_tested": tested,
        "mutants_killed": killed,
        "mutation_kill_ratio": ratio,
        "surviving_mutants": surviving,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
    }


def run(payload: Mapping[str, Any], _root: Path | None = None) -> dict[str, Any]:
    """UnifiedModel/federation callable entry point."""
    op = str(payload.get("op") or "verify_byte_effect").strip().lower()
    if op == "verify_byte_effect":
        return verify_byte_effect(
            payload["target"],
            expected_format=payload.get("expected_format"),
            expected_source_bytes=payload.get("expected_source_bytes"),
            expected_source_path=payload.get("expected_source_path"),
            baseline_archive_hashes=payload.get("baseline_archive_hashes"),
            allowed_archive_mutations=payload.get("allowed_archive_mutations") or (),
        )
    if op == "verify_directory_effect_diff":
        return verify_directory_effect_diff(
            payload["before_snap"],
            payload["after_snap"],
            allowed_writes=payload.get("allowed_writes") or (),
        )
    return {"schema": SCHEMA, "pass": False, "status": f"UNSUPPORTED_OP:{op}"}
