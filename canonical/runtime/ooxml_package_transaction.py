"""Atomic exact OOXML/ZIP package transaction executor.

The engine executes only predeclared low-level package edits. It is intentionally
format-agnostic across DOCX/XLSX/PPTX because all are ZIP packages with XML parts.

Supported bounded operations:
- exact XML element text mutation by child-index path,
- exact XML attribute mutation by child-index path,
- exact XML subtree replacement by child-index path,
- whole-member replace/add/delete with optional SHA-256 preconditions.

Every operation is preconditioned against the current transaction state. The output
is written only after all operations validate. Every undeclared member is preserved
byte-for-byte, changed XML parts must parse after mutation, and the written package
is round-tripped and compared to the planned bytes.

This owns package mechanics only. It does not infer which low-level patch implements
a user's semantic request and makes no visual-layout or terminal-capability claim.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Sequence
import xml.etree.ElementTree as ET
import zipfile

MAX_OPERATIONS = 64


@dataclass(frozen=True)
class XmlSetText:
    member: str
    path: tuple[int, ...]
    text: str
    expected_tag: str | None = None


@dataclass(frozen=True)
class XmlSetAttribute:
    member: str
    path: tuple[int, ...]
    key: str
    value: str
    expected_tag: str | None = None


@dataclass(frozen=True)
class XmlReplaceSubtree:
    member: str
    path: tuple[int, ...]
    fragment_xml: str
    expected_tag: str | None = None


@dataclass(frozen=True)
class ReplaceMember:
    member: str
    data: bytes
    expected_sha256: str | None = None


@dataclass(frozen=True)
class AddMember:
    member: str
    data: bytes


@dataclass(frozen=True)
class DeleteMember:
    member: str
    expected_sha256: str | None = None


Operation = XmlSetText | XmlSetAttribute | XmlReplaceSubtree | ReplaceMember | AddMember | DeleteMember


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_member(name: object) -> bool:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        return False
    parts = name.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _valid_sha(value: str | None) -> bool:
    if value is None:
        return True
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _node_at(root: ET.Element, path: tuple[int, ...]) -> ET.Element:
    node = root
    for index in path:
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(node):
            raise IndexError("invalid child-index path")
        node = node[index]
    return node


def _serialize(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _parse_member(working: dict[str, bytes], member: str) -> ET.Element:
    if member not in working:
        raise KeyError("member missing")
    return ET.fromstring(working[member])


def _check_expected_tag(node: ET.Element, expected_tag: str | None) -> None:
    if expected_tag is not None and node.tag != expected_tag:
        raise ValueError("expected tag mismatch")


def _apply_xml_op(working: dict[str, bytes], op: XmlSetText | XmlSetAttribute | XmlReplaceSubtree) -> None:
    root = _parse_member(working, op.member)
    node = _node_at(root, op.path)
    _check_expected_tag(node, op.expected_tag)

    if isinstance(op, XmlSetText):
        if not isinstance(op.text, str):
            raise TypeError("text must be str")
        node.text = op.text
    elif isinstance(op, XmlSetAttribute):
        if not isinstance(op.key, str) or not op.key or not isinstance(op.value, str):
            raise TypeError("attribute key/value invalid")
        node.set(op.key, op.value)
    elif isinstance(op, XmlReplaceSubtree):
        if not op.path:
            raise ValueError("root subtree replacement must use ReplaceMember")
        if not isinstance(op.fragment_xml, str) or not op.fragment_xml.strip():
            raise TypeError("fragment invalid")
        replacement = ET.fromstring(op.fragment_xml.encode("utf-8"))
        parent = _node_at(root, op.path[:-1])
        index = op.path[-1]
        old = parent[index]
        replacement.tail = old.tail
        parent[index] = replacement
    else:
        raise TypeError("unsupported xml operation")

    working[op.member] = _serialize(root)


def apply_ooxml_transaction(
    input_path: str | Path,
    output_path: str | Path,
    *,
    operations: Sequence[Operation],
) -> dict:
    src = Path(input_path)
    dst = Path(output_path)

    if not isinstance(operations, Sequence) or not operations or len(operations) > MAX_OPERATIONS:
        return {"status": "FAIL_CLOSED", "reason": "OPERATION_SET_INVALID_OR_TOO_LARGE"}
    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}

    try:
        with zipfile.ZipFile(src, "r") as zin:
            infos = zin.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                return {"status": "FAIL_CLOSED", "reason": "DUPLICATE_PACKAGE_MEMBERS"}
            original = {info.filename: zin.read(info.filename) for info in infos}
            info_by_name = {info.filename: info for info in infos}
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "INVALID_ZIP_PACKAGE", "error": type(exc).__name__}

    working = dict(original)
    touched: set[str] = set()

    try:
        for index, op in enumerate(operations):
            member = getattr(op, "member", None)
            if not _valid_member(member):
                raise ValueError(f"invalid member at operation {index}")

            if isinstance(op, (XmlSetText, XmlSetAttribute, XmlReplaceSubtree)):
                _apply_xml_op(working, op)
                touched.add(op.member)

            elif isinstance(op, ReplaceMember):
                if op.member not in working:
                    raise KeyError("replace member missing")
                if not isinstance(op.data, bytes) or not _valid_sha(op.expected_sha256):
                    raise ValueError("replace member arguments invalid")
                if op.expected_sha256 is not None and _sha(working[op.member]) != op.expected_sha256:
                    raise ValueError("replace member sha mismatch")
                working[op.member] = op.data
                touched.add(op.member)

            elif isinstance(op, AddMember):
                if op.member in working:
                    raise ValueError("add member already exists")
                if not isinstance(op.data, bytes):
                    raise TypeError("add data must be bytes")
                working[op.member] = op.data
                touched.add(op.member)

            elif isinstance(op, DeleteMember):
                if op.member not in working:
                    raise KeyError("delete member missing")
                if not _valid_sha(op.expected_sha256):
                    raise ValueError("delete member sha invalid")
                if op.expected_sha256 is not None and _sha(working[op.member]) != op.expected_sha256:
                    raise ValueError("delete member sha mismatch")
                del working[op.member]
                touched.add(op.member)

            else:
                raise TypeError(f"unsupported operation type at {index}")

        for member in sorted(touched):
            if member in working and (member.endswith(".xml") or member.endswith(".rels")):
                ET.fromstring(working[member])

        for member, data in original.items():
            if member not in touched and working.get(member) != data:
                raise RuntimeError("untouched member mutated")

    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {
            "status": "FAIL_CLOSED",
            "reason": "TRANSACTION_PREFLIGHT_OR_MUTATION_FAILED",
            "error": type(exc).__name__,
            "detail": str(exc),
        }

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dst, "w") as zout:
            for name in names:
                if name not in working:
                    continue
                zout.writestr(info_by_name[name], working[name])
            for name in sorted(set(working) - set(names)):
                zout.writestr(name, working[name])
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "WRITE_FAILED", "error": type(exc).__name__}

    try:
        with zipfile.ZipFile(dst, "r") as zout:
            roundtrip_names = [info.filename for info in zout.infolist()]
            if len(roundtrip_names) != len(set(roundtrip_names)):
                raise ValueError("duplicate output members")
            after = {info.filename: zout.read(info.filename) for info in zout.infolist()}
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "OUTPUT_PACKAGE_INVALID", "error": type(exc).__name__}

    if set(after) != set(working) or any(after[name] != data for name, data in working.items()):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_PACKAGE_BYTES_MISMATCH"}

    unchanged = sorted(name for name in original if name not in touched and name in after)
    if any(after[name] != original[name] for name in unchanged):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "UNDECLARED_MEMBER_MUTATED"}

    changed = sorted(
        name for name in set(original) | set(after)
        if original.get(name) != after.get(name)
    )
    return {
        "status": "PASS",
        "output_path": str(dst),
        "operation_count": len(operations),
        "declared_touched_members": sorted(touched),
        "changed_members": changed,
        "unchanged_member_count": len(unchanged),
        "scope": "EXACT_PREDECLARED_OOXML_ZIP_MEMBER_AND_XML_CHILD_INDEX_PATCH_TRANSACTION",
        "semantic_authority": False,
        "visual_layout_authority": False,
        "terminal_authority": False,
    }
