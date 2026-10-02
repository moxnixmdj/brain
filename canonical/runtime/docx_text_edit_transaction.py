"""Atomic fail-closed DOCX visible-text edit transaction.

Scope: multiple unique exact visible-text replacements, each wholly contained in a
single Word paragraph. Targets may span multiple w:t nodes/runs. All targets are
preflighted against the original document, overlaps are rejected, then edits are
applied from right to left inside each paragraph so original offsets remain valid.

The transaction is all-or-nothing: no output is left on failure. Non-document ZIP
members are preserved byte-for-byte. This does not claim arbitrary OOXML editing,
visual-layout equivalence, or semantic document understanding.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Sequence
import xml.etree.ElementTree as ET
import zipfile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
P_TAG = f"{{{W_NS}}}p"
T_TAG = f"{{{W_NS}}}t"
XML_SPACE = f"{{{XML_NS}}}space"
MAX_EDITS = 64


@dataclass(frozen=True)
class TextEdit:
    old: str
    new: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _paragraphs(root: ET.Element):
    rows = []
    for p in root.iter(P_TAG):
        nodes = [n for n in p.iter(T_TAG)]
        rows.append((nodes, "".join(n.text or "" for n in nodes)))
    return rows


def _occurrences(text: str, needle: str) -> list[int]:
    out = []
    start = 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def _set_text(node: ET.Element, text: str) -> None:
    node.text = text
    if text[:1].isspace() or text[-1:].isspace():
        node.set(XML_SPACE, "preserve")
    elif XML_SPACE in node.attrib:
        # Preserve only when still required by the rewritten text.
        node.attrib.pop(XML_SPACE, None)


def _replace_span(nodes: list[ET.Element], start: int, end: int, new: str) -> bool:
    spans = []
    cursor = 0
    for idx, node in enumerate(nodes):
        text = node.text or ""
        nxt = cursor + len(text)
        if max(cursor, start) < min(nxt, end):
            spans.append((idx, cursor, nxt, node, text))
        cursor = nxt
    if not spans:
        return False

    first_idx, first_start, _, first_node, first_text = spans[0]
    last_idx, last_start, _, last_node, last_text = spans[-1]
    first_local = start - first_start
    last_local_end = end - last_start
    if first_local < 0 or last_local_end < 0 or last_local_end > len(last_text):
        return False

    prefix = first_text[:first_local]
    suffix = last_text[last_local_end:]
    if first_idx == last_idx:
        _set_text(first_node, prefix + new + suffix)
    else:
        _set_text(first_node, prefix + new)
        for _, _, _, node, _ in spans[1:-1]:
            _set_text(node, "")
        _set_text(last_node, suffix)
    return True


def apply_text_edit_transaction(
    input_path: str | Path,
    output_path: str | Path,
    *,
    edits: Sequence[TextEdit],
) -> dict:
    src = Path(input_path)
    dst = Path(output_path)

    if not isinstance(edits, Sequence) or not edits or len(edits) > MAX_EDITS:
        return {"status": "FAIL_CLOSED", "reason": "EDIT_SET_INVALID_OR_TOO_LARGE"}
    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}

    clean: list[TextEdit] = []
    for i, edit in enumerate(edits):
        if not isinstance(edit, TextEdit) or not isinstance(edit.old, str) or not edit.old or not isinstance(edit.new, str):
            return {"status": "FAIL_CLOSED", "reason": f"EDIT_INVALID:{i}"}
        clean.append(edit)

    try:
        with zipfile.ZipFile(src, "r") as zin:
            infos = zin.infolist()
            original = {info.filename: zin.read(info.filename) for info in infos}
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "INVALID_ZIP_PACKAGE", "error": type(exc).__name__}

    if "word/document.xml" not in original:
        return {"status": "FAIL_CLOSED", "reason": "DOCX_DOCUMENT_PART_MISSING"}

    try:
        root = ET.fromstring(original["word/document.xml"])
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "DOCUMENT_XML_INVALID", "error": type(exc).__name__}

    rows = _paragraphs(root)
    before_texts = [text for _, text in rows]
    planned: list[tuple[int, int, int, str, str]] = []

    for eidx, edit in enumerate(clean):
        matches: list[tuple[int, int]] = []
        for pidx, (_, text) in enumerate(rows):
            for start in _occurrences(text, edit.old):
                matches.append((pidx, start))
        if len(matches) != 1:
            return {
                "status": "FAIL_CLOSED",
                "reason": "EDIT_TARGET_NOT_UNIQUE_WITHIN_SINGLE_PARAGRAPH",
                "edit_index": eidx,
                "match_count": len(matches),
            }
        pidx, start = matches[0]
        planned.append((pidx, start, start + len(edit.old), edit.old, edit.new))

    by_paragraph: dict[int, list[tuple[int, int, str, str]]] = {}
    for pidx, start, end, old, new in planned:
        by_paragraph.setdefault(pidx, []).append((start, end, old, new))

    for pidx, spans in by_paragraph.items():
        ordered = sorted(spans, key=lambda x: (x[0], x[1]))
        for left, right in zip(ordered, ordered[1:]):
            if right[0] < left[1]:
                return {
                    "status": "FAIL_CLOSED",
                    "reason": "EDIT_TARGETS_OVERLAP",
                    "paragraph_index": pidx,
                }

    expected = list(before_texts)
    for pidx, spans in by_paragraph.items():
        text = expected[pidx]
        for start, end, old, new in sorted(spans, key=lambda x: x[0], reverse=True):
            if text[start:end] != old:
                return {"status": "FAIL_CLOSED", "reason": "PREFLIGHT_OFFSET_INCONSISTENCY"}
            text = text[:start] + new + text[end:]
        expected[pidx] = text

    for pidx, spans in by_paragraph.items():
        nodes = rows[pidx][0]
        for start, end, old, new in sorted(spans, key=lambda x: x[0], reverse=True):
            current = "".join(node.text or "" for node in nodes)
            if current[start:end] != old:
                dst.unlink(missing_ok=True)
                return {"status": "FAIL_CLOSED", "reason": "MUTATION_OFFSET_INCONSISTENCY"}
            if not _replace_span(nodes, start, end, new):
                dst.unlink(missing_ok=True)
                return {"status": "FAIL_CLOSED", "reason": "TARGET_RANGE_MAPPING_FAILED"}

    edited_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
            for info in zin.infolist():
                data = edited_xml if info.filename == "word/document.xml" else zin.read(info.filename)
                zout.writestr(info, data)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "WRITE_FAILED", "error": type(exc).__name__}

    try:
        with zipfile.ZipFile(dst, "r") as zout:
            after = {info.filename: zout.read(info.filename) for info in zout.infolist()}
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "OUTPUT_PACKAGE_INVALID", "error": type(exc).__name__}

    if set(after) != set(original):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "PACKAGE_MEMBER_SET_CHANGED"}

    changed = [name for name in sorted(original) if _sha(original[name]) != _sha(after[name])]
    if changed != ["word/document.xml"]:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "UNRELATED_PACKAGE_MEMBER_MUTATED",
            "changed_members": changed,
        }

    try:
        check_root = ET.fromstring(after["word/document.xml"])
        after_texts = [text for _, text in _paragraphs(check_root)]
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_XML_INVALID", "error": type(exc).__name__}

    if after_texts != expected:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_VISIBLE_TEXT_SCOPE_MISMATCH"}

    return {
        "status": "PASS",
        "output_path": str(dst),
        "edit_count": len(clean),
        "edited_paragraph_count": len(by_paragraph),
        "changed_members": changed,
        "preserved_member_count": len(original) - 1,
        "scope": "ATOMIC_MULTIPLE_UNIQUE_EXACT_VISIBLE_TEXT_REPLACEMENTS_EACH_WITHIN_ONE_PARAGRAPH_ACROSS_W_T_NODES",
        "visual_layout_authority": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
