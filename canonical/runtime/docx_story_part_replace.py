"""Fail-closed byte-preserving text replacement in explicit DOCX Word story parts.

Supported parts:
- word/headerN.xml
- word/footerN.xml
- word/footnotes.xml
- word/endnotes.xml
- word/comments.xml

Scope: one unique exact visible-text occurrence contained within a single w:p in the
selected part. The target may span multiple w:t nodes/runs. Every other ZIP member
must remain byte-identical. This does not edit relationships, fields, drawings,
tracked-deletion text, or arbitrary OOXML structure.
"""
from __future__ import annotations

import re
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from canonical.runtime.docx_run_span_replace import (
    _occurrences,
    _paragraph_text_nodes,
    _set_text,
    _sha,
)

_ALLOWED = re.compile(
    r"^word/(?:header[1-9][0-9]*|footer[1-9][0-9]*|footnotes|endnotes|comments)\.xml$"
)


def _allowed_story_part(part_name: str) -> bool:
    return isinstance(part_name, str) and bool(_ALLOWED.fullmatch(part_name))


def replace_unique_story_part_span(
    input_path: str | Path,
    output_path: str | Path,
    *,
    part_name: str,
    old: str,
    new: str,
) -> dict:
    src = Path(input_path)
    dst = Path(output_path)

    if not _allowed_story_part(part_name):
        return {"status": "FAIL_CLOSED", "reason": "STORY_PART_NOT_ALLOWED"}
    if not isinstance(old, str) or not old or not isinstance(new, str):
        return {"status": "FAIL_CLOSED", "reason": "INVALID_TEXT_ARGUMENT"}
    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}

    try:
        with zipfile.ZipFile(src, "r") as zin:
            infos = zin.infolist()
            original = {info.filename: zin.read(info.filename) for info in infos}
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "reason": "INVALID_ZIP_PACKAGE",
            "error": type(exc).__name__,
        }

    if part_name not in original:
        return {"status": "FAIL_CLOSED", "reason": "STORY_PART_MISSING"}

    try:
        root = ET.fromstring(original[part_name])
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "reason": "STORY_PART_XML_INVALID",
            "error": type(exc).__name__,
        }

    paragraphs = _paragraph_text_nodes(root)
    before_texts = [text for _, _, text in paragraphs]
    matches: list[tuple[int, int]] = []
    for pidx, (_, _, text) in enumerate(paragraphs):
        for start in _occurrences(text, old):
            matches.append((pidx, start))

    if len(matches) != 1:
        return {
            "status": "FAIL_CLOSED",
            "reason": "TARGET_VISIBLE_TEXT_NOT_UNIQUE_WITHIN_SELECTED_STORY_PART_PARAGRAPH",
            "match_count": len(matches),
        }

    pidx, start = matches[0]
    _, nodes, paragraph_text = paragraphs[pidx]
    end = start + len(old)
    if not nodes:
        return {"status": "FAIL_CLOSED", "reason": "TARGET_PARAGRAPH_HAS_NO_TEXT_NODES"}

    spans = []
    cursor = 0
    for idx, node in enumerate(nodes):
        text = node.text or ""
        nxt = cursor + len(text)
        if max(cursor, start) < min(nxt, end):
            spans.append((idx, cursor, nxt, node, text))
        cursor = nxt
    if not spans:
        return {"status": "FAIL_CLOSED", "reason": "TARGET_RANGE_MAPPING_FAILED"}

    first_idx, first_start, _, first_node, first_text = spans[0]
    last_idx, last_start, _, last_node, last_text = spans[-1]
    first_local = start - first_start
    last_local_end = end - last_start
    prefix = first_text[:first_local]
    suffix = last_text[last_local_end:]

    if first_idx == last_idx:
        _set_text(first_node, prefix + new + suffix)
    else:
        _set_text(first_node, prefix + new)
        for _, _, _, node, _ in spans[1:-1]:
            _set_text(node, "")
        _set_text(last_node, suffix)

    edited_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
            for info in zin.infolist():
                data = edited_xml if info.filename == part_name else zin.read(info.filename)
                zout.writestr(info, data)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "WRITE_FAILED", "error": type(exc).__name__}

    try:
        with zipfile.ZipFile(dst, "r") as zout:
            after = {info.filename: zout.read(info.filename) for info in zout.infolist()}
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "OUTPUT_PACKAGE_INVALID",
            "error": type(exc).__name__,
        }

    if set(after) != set(original):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "PACKAGE_MEMBER_SET_CHANGED"}

    changed = [name for name in sorted(original) if _sha(original[name]) != _sha(after[name])]
    if changed != [part_name]:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "UNRELATED_PACKAGE_MEMBER_MUTATED",
            "changed_members": changed,
        }

    try:
        check_root = ET.fromstring(after[part_name])
        after_texts = [text for _, _, text in _paragraph_text_nodes(check_root)]
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "ROUNDTRIP_XML_INVALID",
            "error": type(exc).__name__,
        }

    expected = list(before_texts)
    expected[pidx] = paragraph_text[:start] + new + paragraph_text[end:]
    if after_texts != expected:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_VISIBLE_TEXT_SCOPE_MISMATCH"}

    return {
        "status": "PASS",
        "output_path": str(dst),
        "part_name": part_name,
        "changed_members": changed,
        "paragraph_index": pidx,
        "spanned_text_node_count": len(spans),
        "preserved_member_count": len(original) - 1,
        "scope": "UNIQUE_EXACT_VISIBLE_TEXT_OCCURRENCE_WITHIN_ONE_EXPLICIT_WORD_STORY_PART_PARAGRAPH",
        "visual_layout_authority": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
