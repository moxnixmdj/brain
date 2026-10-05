"""Parent-side contract for Pandoc/WeasyPrint PDF artifact production.

This module performs no subprocess creation. It prepares an ephemeral .pdf
stdout proxy, binds the declared input/toolchain/output identity, and commits
only validated PDF bytes through the typed artifact finalizer.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any

from canonical.runtime import root3_typed_artifact_finalizer_v1 as finalizer

CAPABILITY_ID = "document.convert.markdown_pdf.pandoc_weasyprint"
STDOUT_PROXY_TARGET = "/proc/self/fd/1"


def _declared_output_path(root: pathlib.Path, raw: Any) -> str:
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


def _toolchain_binding(root: pathlib.Path) -> str:
    registry_path = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
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
            "<EPHEMERAL_PDF_STDOUT_PROXY>",
            "--pdf-engine=weasyprint",
        ],
        "stdout_proxy_target": STDOUT_PROXY_TARGET,
    }
    encoded = json.dumps(
        contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare(args: dict[str, Any], root: pathlib.Path, source: pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    if not source.is_file() or source.suffix.lower() not in {".md", ".markdown"}:
        raise RuntimeError("MARKDOWN_INPUT_REQUIRED")
    output_path = _declared_output_path(root, args.get("output_path"))
    input_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    toolchain_binding_sha256 = _toolchain_binding(root)
    expected_pre_sha256 = finalizer.observe_prestate(root, output_path)

    temp = tempfile.TemporaryDirectory(prefix="project-brain-pandoc-stdout-")
    try:
        proxy = pathlib.Path(temp.name) / "output.pdf"
        proxy.symlink_to(STDOUT_PROXY_TARGET)
        if not proxy.is_symlink() or os.readlink(proxy) != STDOUT_PROXY_TARGET:
            raise RuntimeError("PDF_STDOUT_PROXY_INVALID")
        return {
            "root": root,
            "source": source,
            "output_path": output_path,
            "input_sha256": input_sha256,
            "toolchain_binding_sha256": toolchain_binding_sha256,
            "expected_pre_sha256": expected_pre_sha256,
            "temp": temp,
            "proxy": proxy,
            "argv": [
                "pandoc",
                str(source),
                "-o",
                str(proxy),
                "--pdf-engine=weasyprint",
            ],
        }
    except Exception:
        temp.cleanup()
        raise


def abort(context: dict[str, Any]) -> None:
    temp = context.get("temp") if isinstance(context, dict) else None
    if temp is not None:
        temp.cleanup()


def finish(context: dict[str, Any], proc: Any) -> dict[str, Any]:
    temp = context.get("temp")
    proxy = context.get("proxy")
    try:
        if (
            not isinstance(proxy, pathlib.Path)
            or not proxy.is_symlink()
            or os.readlink(proxy) != STDOUT_PROXY_TARGET
        ):
            raise RuntimeError("PDF_STDOUT_PROXY_MUTATED")
        stderr = bytes(getattr(proc, "stderr", None) or b"").decode("utf-8", "replace")
        if int(getattr(proc, "returncode", -1)) != 0:
            raise RuntimeError("PANDOC_PDF_FAILED:" + stderr[-2000:])
        payload = bytes(getattr(proc, "stdout", None) or b"")
    finally:
        if temp is not None:
            temp.cleanup()

    plan = finalizer.build_plan(
        output_path=context["output_path"],
        payload=payload,
        expected_pre_sha256=context["expected_pre_sha256"],
        input_sha256=context["input_sha256"],
        toolchain_binding_sha256=context["toolchain_binding_sha256"],
    )
    receipt = finalizer.commit(context["root"], plan, payload)
    if (
        receipt.get("status") != "COMMITTED"
        or receipt.get("post_sha256") != hashlib.sha256(payload).hexdigest()
    ):
        raise RuntimeError("PDF_FINALIZATION_FAILED")

    root = context["root"]
    source = context["source"]
    return {
        "adapter": "pandoc_weasyprint",
        "argv_contract": [
            "pandoc",
            str(source.relative_to(root)),
            "-o",
            "<EPHEMERAL_PDF_STDOUT_PROXY>",
            "--pdf-engine=weasyprint",
        ],
        "returncode": 0,
        "input_path": str(source.relative_to(root)),
        "input_sha256": context["input_sha256"],
        "output_path": context["output_path"],
        "output_bytes": len(payload),
        "output_sha256": receipt["post_sha256"],
        "output_verified": True,
        "pdf_transport": "EPHEMERAL_PDF_SUFFIX_SYMLINK_TO_CHILD_STDOUT_FD1",
        "child_durable_output_path_authority": False,
        "typed_parent_finalization": True,
        "artifact_finalizer_plan_sha256": receipt["plan_sha256"],
        "toolchain_binding_sha256": context["toolchain_binding_sha256"],
        "stderr": stderr[-4000:],
    }
