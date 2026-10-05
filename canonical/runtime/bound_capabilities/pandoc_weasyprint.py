#!/usr/bin/env python3
"""Markdown-to-PDF conversion with typed parent-only durable finalization."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess

from canonical.runtime import root3_typed_artifact_finalizer_v1 as finalizer

CAPABILITY_ID = "document.convert.markdown_pdf.pandoc_weasyprint"


def _safe_input_path(root, raw):
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path != root and root not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return path


def _declared_output_path(root, raw):
    root = pathlib.Path(root).resolve()
    value = str(raw or "")
    if not value or "\x00" in value or "\\" in value:
        raise RuntimeError("OUTPUT_PATH_INVALID")
    path = pathlib.Path(value)
    if path.is_absolute():
        lexical = pathlib.Path(os.path.abspath(path))
    else:
        pure = pathlib.PurePosixPath(value)
        if any(part in {"", ".", ".."} for part in pure.parts):
            raise RuntimeError("OUTPUT_PATH_INVALID")
        lexical = pathlib.Path(os.path.abspath(root / path))
    try:
        relative = lexical.relative_to(pathlib.Path(os.path.abspath(root))).as_posix()
    except ValueError as exc:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY") from exc
    if pathlib.PurePosixPath(relative).suffix.lower() != ".pdf":
        raise RuntimeError("PDF_OUTPUT_REQUIRED")
    return relative


def _toolchain_binding(root):
    registry_path = pathlib.Path(root) / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = (registry.get("capabilities") or {}).get(CAPABILITY_ID)
    source = entry.get("source") if isinstance(entry, dict) else None
    if not isinstance(source, dict) or source.get("type") != "apt":
        raise RuntimeError("BOUND_TOOLCHAIN_SOURCE_INVALID")
    packages = source.get("packages")
    if not isinstance(packages, list):
        raise RuntimeError("BOUND_TOOLCHAIN_PACKAGES_INVALID")
    normalized = []
    for item in packages:
        if not isinstance(item, dict):
            raise RuntimeError("BOUND_TOOLCHAIN_PACKAGE_INVALID")
        name = str(item.get("name") or "")
        version = str(item.get("version") or "")
        digest = str(item.get("sha256") or "").lower()
        if (
            name not in {"pandoc", "weasyprint"}
            or not version
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise RuntimeError("BOUND_TOOLCHAIN_PACKAGE_INVALID")
        normalized.append({"name": name, "version": version, "sha256": digest})
    if sorted(x["name"] for x in normalized) != ["pandoc", "weasyprint"]:
        raise RuntimeError("BOUND_TOOLCHAIN_PACKAGE_SET_INVALID")
    normalized.sort(key=lambda x: x["name"])
    contract = {
        "capability_id": CAPABILITY_ID,
        "packages": normalized,
        "command_contract": [
            "pandoc",
            "<MARKDOWN_PATH>",
            "-o",
            "-",
            "--pdf-engine=weasyprint",
        ],
    }
    encoded = json.dumps(
        contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run(args, root):
    root = pathlib.Path(root).resolve()
    source = _safe_input_path(root, args.get("markdown_path"))
    output_path = _declared_output_path(root, args.get("output_path"))
    if not source.is_file() or source.suffix.lower() not in {".md", ".markdown"}:
        raise RuntimeError("MARKDOWN_INPUT_REQUIRED")

    input_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    toolchain_binding_sha256 = _toolchain_binding(root)
    expected_pre_sha256 = finalizer.observe_prestate(root, output_path)

    argv = ["pandoc", str(source), "-o", "-", "--pdf-engine=weasyprint"]
    proc = subprocess.run(
        argv,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        timeout=max(1, min(int(args.get("timeout_s", 120)), 300)),
    )
    stderr = bytes(proc.stderr or b"").decode("utf-8", "replace")
    if proc.returncode != 0:
        raise RuntimeError("PANDOC_PDF_FAILED:" + stderr[-2000:])

    payload = bytes(proc.stdout or b"")
    plan = finalizer.build_plan(
        output_path=output_path,
        payload=payload,
        expected_pre_sha256=expected_pre_sha256,
        input_sha256=input_sha256,
        toolchain_binding_sha256=toolchain_binding_sha256,
    )
    receipt = finalizer.commit(root, plan, payload)
    if (
        receipt.get("status") != "COMMITTED"
        or receipt.get("post_sha256") != hashlib.sha256(payload).hexdigest()
    ):
        raise RuntimeError("PDF_FINALIZATION_FAILED")

    return {
        "adapter": "pandoc_weasyprint",
        "argv": argv,
        "returncode": 0,
        "input_path": str(source.relative_to(root)),
        "input_sha256": input_sha256,
        "output_path": output_path,
        "output_bytes": len(payload),
        "output_sha256": receipt["post_sha256"],
        "output_verified": True,
        "child_durable_output_path_authority": False,
        "typed_parent_finalization": True,
        "artifact_finalizer_plan_sha256": receipt["plan_sha256"],
        "toolchain_binding_sha256": toolchain_binding_sha256,
        "stderr": stderr[-4000:],
    }
