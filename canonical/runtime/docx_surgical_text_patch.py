"""Brain-owned surgical DOCX paragraph text patching.

White-box mechanism source:
  genspark-ai/genoffice @ db347087628281d49e53d009183d2fb506c3a444
  packages/docx-engine/src/text-patch.ts (Apache-2.0)

Independent Python implementation of the bounded mechanism: preserve unchanged
paragraph/run XML, surgically rewrite only w:t spans covering a changed text
range, self-check the extracted target text, and fail closed when preservation
cannot be established. No general DOCX or visual-equivalence claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import hashlib
import re
import shutil
import zipfile

_PARA_TOKEN_RE = re.compile(r"<w:p(?:\s[^>]*)?/>|<w:p(?:\s[^>]*)?>|</w:p>")
_WT_RE = re.compile(r"<w:t(?:\s[^>]*)?>([\s\S]*?)</w:t>")
_ALLOWED_PART_RE = re.compile(
    r"^word/(?:document|comments|footnotes|endnotes|header\d+|footer\d+)\.xml$"
)


def _escape_xml_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass(frozen=True)
class _Slice:
    start: int
    end: int
    xml: str


@dataclass(frozen=True)
class _TextSlice:
    tag_start: int
    tag_end: int
    text: str


def _paragraph_slices(xml: str) -> list[_Slice]:
    out: list[_Slice] = []
    depth = 0
    start = -1
    for match in _PARA_TOKEN_RE.finditer(xml):
        token = match.group(0)
        if token == "</w:p>":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(_Slice(start, match.end(), xml[start:match.end()]))
                start = -1
        elif token.endswith("/>"):
            if depth == 0:
                out.append(_Slice(match.start(), match.end(), token))
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    return out


def _text_slices(paragraph_xml: str) -> list[_TextSlice]:
    return [
        _TextSlice(m.start(), m.end(), unescape(m.group(1)))
        for m in _WT_RE.finditer(paragraph_xml)
    ]


def _decoded_text(paragraph_xml: str) -> str:
    return "".join(s.text for s in _text_slices(paragraph_xml))


def _patch_one_paragraph(
    paragraph_xml: str,
    new_text: str,
    *,
    skip_leading_whitespace: bool,
) -> str | None:
    slices = _text_slices(paragraph_xml)
    if not slices:
        return None

    raw = "".join(s.text for s in slices)
    leading = len(raw) - len(raw.lstrip()) if skip_leading_whitespace else 0
    old_text = raw[leading:]
    if old_text == new_text:
        return paragraph_xml

    prefix = 0
    max_common = min(len(old_text), len(new_text))
    while prefix < max_common and old_text[prefix] == new_text[prefix]:
        prefix += 1

    suffix = 0
    while (
        suffix < max_common - prefix
        and old_text[len(old_text) - 1 - suffix] == new_text[len(new_text) - 1 - suffix]
    ):
        suffix += 1

    change_start = leading + prefix
    change_end = leading + len(old_text) - suffix
    replacement = new_text[prefix : len(new_text) - suffix if suffix else len(new_text)]

    bounds: list[tuple[int, int]] = []
    cursor = 0
    first = -1
    last = -1
    for i, s in enumerate(slices):
        start, end = cursor, cursor + len(s.text)
        bounds.append((start, end))
        touches = (
            start <= change_start <= end
            if change_start == change_end
            else start < change_end and end > change_start
        )
        if touches:
            if first < 0:
                first = i
            last = i
        cursor = end

    if first < 0:
        return None

    first_start, _ = bounds[first]
    last_start, _ = bounds[last]
    head = slices[first].text[: max(0, change_start - first_start)]
    tail = slices[last].text[max(0, change_end - last_start) :]
    replacements = {first: _escape_xml_text(head + replacement + tail)}
    for i in range(first + 1, last + 1):
        replacements[i] = ""

    out = paragraph_xml
    for i in range(last, first - 1, -1):
        s = slices[i]
        tag = '<w:t xml:space="preserve">' + replacements[i] + "</w:t>"
        out = out[: s.tag_start] + tag + out[s.tag_end :]
    return out


def patch_paragraph_texts_xml(
    entry_xml: str,
    new_text: str,
    *,
    strip_first_para_leading_space: bool = False,
) -> str | None:
    """Patch fixed-count top-level paragraphs while preserving untouched XML."""
    if not isinstance(entry_xml, str) or not isinstance(new_text, str):
        return None
    paras = _paragraph_slices(entry_xml)
    if not paras:
        return None

    old_texts: list[str] = []
    for i, para in enumerate(paras):
        text = _decoded_text(para.xml)
        if i == 0 and strip_first_para_leading_space:
            text = text.lstrip()
        old_texts.append(text)

    if "\n".join(old_texts) == new_text:
        return entry_xml
    new_texts = new_text.split("\n")
    if len(new_texts) != len(paras):
        return None

    chunks: list[str] = []
    cursor = 0
    for i, para in enumerate(paras):
        chunks.append(entry_xml[cursor:para.start])
        if old_texts[i] == new_texts[i]:
            chunks.append(para.xml)
        else:
            patched = _patch_one_paragraph(
                para.xml,
                new_texts[i],
                skip_leading_whitespace=(i == 0 and strip_first_para_leading_space),
            )
            if patched is None:
                return None
            chunks.append(patched)
        cursor = para.end
    chunks.append(entry_xml[cursor:])
    out = "".join(chunks)

    check: list[str] = []
    for i, para in enumerate(_paragraph_slices(out)):
        text = _decoded_text(para.xml)
        if i == 0 and strip_first_para_leading_space:
            text = text.lstrip()
        check.append(text)
    return out if "\n".join(check) == new_text else None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_docx_part_paragraph_texts(
    input_path: str | Path,
    output_path: str | Path,
    *,
    part_path: str,
    new_text: str,
    strip_first_para_leading_space: bool = False,
) -> dict:
    """Patch one supported Word XML part; unrelated ZIP member content must not change."""
    src, dst = Path(input_path), Path(output_path)
    if not _ALLOWED_PART_RE.fullmatch(part_path or ""):
        return {"status": "FAIL_CLOSED", "reason": "UNSUPPORTED_PART_PATH"}
    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}

    try:
        with zipfile.ZipFile(src, "r") as zin:
            infos = zin.infolist()
            original = {info.filename: zin.read(info.filename) for info in infos}
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "INVALID_ZIP_PACKAGE", "error": type(exc).__name__}

    if part_path not in original:
        return {"status": "FAIL_CLOSED", "reason": "TARGET_PART_MISSING"}
    try:
        source_xml = original[part_path].decode("utf-8")
    except UnicodeDecodeError:
        return {"status": "FAIL_CLOSED", "reason": "TARGET_PART_NOT_UTF8"}

    patched = patch_paragraph_texts_xml(
        source_xml,
        new_text,
        strip_first_para_leading_space=strip_first_para_leading_space,
    )
    if patched is None:
        return {"status": "ESCALATE", "reason": "SURGICAL_PATCH_NOT_PROVABLE"}
    if patched == source_xml:
        if src.resolve() != dst.resolve():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        return {"status": "PASS", "reason": "NO_CHANGE_REQUIRED", "changed_members": [], "terminal_authority": False}

    target_bytes = patched.encode("utf-8")
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
            for info in zin.infolist():
                zout.writestr(info, target_bytes if info.filename == part_path else zin.read(info.filename))
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "WRITE_FAILED", "error": type(exc).__name__}

    try:
        with zipfile.ZipFile(dst, "r") as zout:
            after = {info.filename: zout.read(info.filename) for info in zout.infolist()}
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "OUTPUT_INVALID_ZIP", "error": type(exc).__name__}

    if set(after) != set(original):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "PACKAGE_MEMBER_SET_CHANGED"}
    changed = [name for name in sorted(original) if _sha(original[name]) != _sha(after[name])]
    if changed != [part_path]:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "UNRELATED_PACKAGE_MEMBER_MUTATED", "changed": changed}

    verify_text: list[str] = []
    for i, para in enumerate(_paragraph_slices(after[part_path].decode("utf-8"))):
        text = _decoded_text(para.xml)
        if i == 0 and strip_first_para_leading_space:
            text = text.lstrip()
        verify_text.append(text)
    if "\n".join(verify_text) != new_text:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_CONTENT_MISMATCH"}

    return {
        "status": "PASS",
        "changed_members": changed,
        "preserved_member_count": len(original) - 1,
        "scope": "SUPPORTED_WORD_XML_PART__FIXED_PARAGRAPH_COUNT__SURGICAL_MULTI_RUN_TEXT_PATCH",
        "visual_layout_authority": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
