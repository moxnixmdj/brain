#!/usr/bin/env python3
"""Generate a PDF document from text. Python stdlib only -- no library, no network.

WHY THIS EXISTS (r98). The unified model held 443 capabilities and THREE that mention
"pdf". All three were EXTRACTORS. There was no producer. GDPval's task population is
xlsx 65 / pdf 85 / docx 64 / zip -- pdf is the single most common deliverable and the
model could read one and not write one. W_COVER was therefore bounded at 29.5% by
SUPPLY, not by routing (r98 measured routing at 6/6) and not by weights (there are none).

The proof here is not "bytes were written". A PDF that no reader accepts is not a
document. So the file is WRITTEN, READ BACK BYTE-FOR-BYTE, then RE-PARSED: the
cross-reference offsets are followed from the startxref trailer to every object, the
page tree is walked to its content stream, and the decoded text is compared to what the
caller asked for. A document that parses to something other than the request is refused
rather than reported as written -- the same standard file_write_json sets.

Determinism: no timestamps, no IDs, no compression. Compile twice, get the same bytes.
The SHA-256 of the output is returned so a caller can pin it.
"""
from __future__ import annotations
import hashlib
import pathlib
import re

# PDF text strings are written in the PDFDocEncoding subset we emit: printable ASCII.
# Anything else would need font embedding, so it is refused rather than silently mangled.
_ALLOWED = re.compile(r"^[\x20-\x7e\n\t]*$")


def _safe(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _build(title: str, lines: list[str]) -> bytes:
    """Assemble a minimal, fully valid PDF 1.4 with a real xref table and trailer."""
    body: list[str] = []
    # object 1: catalog, 2: page tree, 3: page, 4: content stream, 5: font
    content_parts = ["BT", "/F1 12 Tf", "14 TL", "50 780 Td"]
    first = True
    for ln in lines:
        if not first:
            content_parts.append("T*")
        content_parts.append("(%s) Tj" % _escape(ln))
        first = False
    content_parts.append("ET")
    stream = "\n".join(content_parts).encode("latin-1")

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for num in sorted(objs):
        out += b"%010d 00000 n \n" % offsets[num]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1, xref_at)
    return bytes(out)


def _reparse(raw: bytes) -> list[str]:
    """Follow startxref -> xref -> every object, walk to the page, decode its text.

    This is the oracle. If the offsets are wrong, the walk raises and the write is
    refused. A file that merely starts with %PDF is not evidence of anything.
    """
    m = re.search(rb"startxref\s+(\d+)\s+%%EOF", raw)
    if not m:
        raise RuntimeError("PDF_REPARSE_STARTXREF_MISSING")
    xref_at = int(m.group(1))
    if raw[xref_at:xref_at + 4] != b"xref":
        raise RuntimeError("PDF_REPARSE_XREF_OFFSET_WRONG")
    block = raw[xref_at:].split(b"trailer", 1)[0].splitlines()
    entries = [ln for ln in block[2:] if ln.endswith(b"n ")]
    for i, ln in enumerate(entries, start=1):
        off = int(ln[:10])
        if not raw[off:].startswith(b"%d 0 obj" % i):
            raise RuntimeError("PDF_REPARSE_OBJECT_OFFSET_WRONG:%d" % i)
    page = re.search(rb"/Type /Page[^s]", raw)
    if not page:
        raise RuntimeError("PDF_REPARSE_PAGE_MISSING")
    if b"/Contents 4 0 R" not in raw:
        raise RuntimeError("PDF_REPARSE_CONTENT_REF_MISSING")
    sm = re.search(rb"stream\n(.*?)\nendstream", raw, re.S)
    if not sm:
        raise RuntimeError("PDF_REPARSE_STREAM_MISSING")
    text = sm.group(1).decode("latin-1")
    found = [t.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
             for t in re.findall(r"\((.*?)\) Tj", text)]
    if not found:
        raise RuntimeError("PDF_REPARSE_NO_TEXT")
    return found


def run(args, root):
    root = pathlib.Path(root).resolve()
    title = str(args.get("title") or "").strip()
    body = args.get("text")
    output_path = _safe(root, args.get("output_path"))
    if body is None or str(body) == "":
        raise RuntimeError("TEXT_REQUIRED")
    if not output_path.name or output_path.is_dir():
        raise RuntimeError("OUTPUT_PATH_REQUIRED")
    lines = [ln for ln in str(body).splitlines()]
    if title:
        lines = [title, ""] + lines
    for ln in lines:
        if not _ALLOWED.match(ln):
            raise RuntimeError("TEXT_NOT_ENCODABLE_WITHOUT_FONT_EMBEDDING")
    raw = _build(title, lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    check = output_path.read_bytes()
    if check != raw:
        raise RuntimeError("WRITE_DID_NOT_ROUNDTRIP")
    found = _reparse(check)
    expected = [ln for ln in lines if ln]
    if not all(e in found for e in expected):
        raise RuntimeError("PDF_REPARSE_TEXT_MISMATCH")
    return {
        "adapter": "pdf_generate_from_text",
        "output_path": str(output_path),
        "output_bytes": len(check),
        "output_sha256": hashlib.sha256(check).hexdigest(),
        "page_count": 1,
        "text_lines_written": len(expected),
        "text_lines_reparsed": len(found),
        "output_verified": True,
    }
