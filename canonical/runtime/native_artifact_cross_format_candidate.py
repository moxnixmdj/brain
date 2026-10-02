"""Brain-owned cross-format native artifact edit candidate.

This composes existing deterministic native transaction engines. The edit request is
explicit: format, exact old/new text, and (for PDF) page index. For OOXML formats
the candidate locates exactly one XML text node equal to the requested old text,
then delegates the atomic mutation to the existing package transaction. DOCX uses
the stronger run-spanning text transaction. PDF uses the existing native content-
stream transaction.

The candidate does not judge document quality, infer an ambiguous semantic target,
or claim visual equivalence. Those are oracle/higher-level concerns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import xml.etree.ElementTree as ET
import zipfile

from canonical.runtime.docx_text_edit_transaction import TextEdit, apply_text_edit_transaction
from canonical.runtime.ooxml_package_transaction import XmlSetText, apply_ooxml_transaction
from canonical.runtime.pdf_native_edit_transaction import replace_unique_pdf_text_operand


SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_CROSS_FORMAT_CANDIDATE_V1"


def _find_unique_xml_text(path: Path, old: str) -> tuple[str, tuple[int, ...], str]:
    matches: list[tuple[str, tuple[int, ...], str]] = []
    with zipfile.ZipFile(path, "r") as z:
        for member in sorted(z.namelist()):
            if not member.endswith(".xml"):
                continue
            try:
                root = ET.fromstring(z.read(member))
            except Exception:
                continue

            def walk(node: ET.Element, child_path: tuple[int, ...]) -> None:
                if node.text == old:
                    matches.append((member, child_path, node.tag))
                for i, child in enumerate(list(node)):
                    walk(child, child_path + (i,))

            walk(root, ())
    if len(matches) != 1:
        raise ValueError(f"XML_TEXT_TARGET_NOT_UNIQUE:{len(matches)}")
    return matches[0]


def apply_explicit_native_edit(
    input_path: str | Path,
    output_path: str | Path,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    src = Path(input_path)
    dst = Path(output_path)
    fmt = str(request.get("format") or "").lower()
    old = request.get("old")
    new = request.get("new")

    if fmt not in {"docx", "xlsx", "pptx", "pdf"}:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "FORMAT_UNSUPPORTED"}
    if not isinstance(old, str) or not old or not isinstance(new, str) or old == new:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TEXT_EDIT_INVALID"}

    if fmt == "docx":
        out = apply_text_edit_transaction(src, dst, edits=[TextEdit(old=old, new=new)])
    elif fmt in {"xlsx", "pptx"}:
        try:
            member, path, tag = _find_unique_xml_text(src, old)
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "TARGET_DISCOVERY_FAILED",
                "error": type(exc).__name__,
                "detail": str(exc),
            }
        out = apply_ooxml_transaction(
            src,
            dst,
            operations=[XmlSetText(member=member, path=path, text=new, expected_tag=tag)],
        )
        out = dict(out)
        out["target_member"] = member
    else:
        page_index = request.get("page_index", 0)
        out = replace_unique_pdf_text_operand(
            src,
            dst,
            page_index=page_index,
            old=old,
            new=new,
        )

    result = dict(out)
    result["schema"] = SCHEMA
    result["format"] = fmt
    result["semantic_authority"] = False
    result["terminal_authority"] = False
    result["capability_credit_delta"] = 0
    return result
