"""Fail-closed exact DOCX text replacement across one or more Word text runs.

Scope: one unique exact visible-text occurrence contained within a single paragraph.
The target may span multiple w:t nodes/runs. Non-document ZIP members are preserved
byte-for-byte, paragraph text outside the target paragraph is unchanged, and run
properties are not rewritten intentionally.

This does not claim visual-layout equivalence, arbitrary OOXML editing, or semantic
document understanding.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
P_TAG = f"{{{W_NS}}}p"
T_TAG = f"{{{W_NS}}}t"
XML_SPACE = f"{{{XML_NS}}}space"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _paragraph_text_nodes(root: ET.Element):
    out = []
    for p in root.iter(P_TAG):
        nodes = [n for n in p.iter(T_TAG)]
        out.append((p, nodes, "".join(n.text or "" for n in nodes)))
    return out


def _occurrences(text: str, needle: str) -> list[int]:
    starts = []
    i = 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            return starts
        starts.append(j)
        i = j + 1


def _set_text(node: ET.Element, text: str) -> None:
    node.text = text
    if text[:1].isspace() or text[-1:].isspace():
        node.set(XML_SPACE, "preserve")


def replace_unique_paragraph_span(
    input_path: str | Path,
    output_path: str | Path,
    *,
    old: str,
    new: str,
) -> dict:
    src = Path(input_path)
    dst = Path(output_path)

    if not isinstance(old, str) or not old or not isinstance(new, str):
        return {"status": "FAIL_CLOSED", "reason": "INVALID_TEXT_ARGUMENT"}
    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}

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

    paragraphs = _paragraph_text_nodes(root)
    matches: list[tuple[int, int]] = []
    before_texts = [text for _, _, text in paragraphs]
    for pidx, (_, _, text) in enumerate(paragraphs):
        for start in _occurrences(text, old):
            matches.append((pidx, start))

    if len(matches) != 1:
        return {
            "status": "FAIL_CLOSED",
            "reason": "TARGET_VISIBLE_TEXT_NOT_UNIQUE_WITHIN_SINGLE_PARAGRAPH",
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
        after_paragraphs = _paragraph_text_nodes(check_root)
        after_texts = [text for _, _, text in after_paragraphs]
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_XML_INVALID", "error": type(exc).__name__}

    if len(after_texts) != len(before_texts):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "PARAGRAPH_STRUCTURE_COUNT_CHANGED"}

    expected = list(before_texts)
    expected[pidx] = paragraph_text[:start] + new + paragraph_text[end:]
    if after_texts != expected:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "ROUNDTRIP_VISIBLE_TEXT_SCOPE_MISMATCH",
        }

    return {
        "status": "PASS",
        "output_path": str(dst),
        "changed_members": changed,
        "paragraph_index": pidx,
        "spanned_text_node_count": len(spans),
        "preserved_member_count": len(original) - 1,
        "scope": "UNIQUE_EXACT_VISIBLE_TEXT_OCCURRENCE_WITHIN_ONE_PARAGRAPH_ACROSS_ONE_OR_MORE_W_T_NODES",
        "visual_layout_authority": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
