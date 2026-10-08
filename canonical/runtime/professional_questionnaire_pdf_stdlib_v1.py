#!/usr/bin/env python3
"""Pure-stdlib deterministic renderer for simple professional questionnaires.

The renderer accepts a typed three-page questionnaire specification and emits
a minimal valid PDF using only built-in Type1 Helvetica. It intentionally
supports a narrow, auditable surface: title, page heading, intro text,
questions, answer lines, and page numbers.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import textwrap
import unicodedata
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUESTIONNAIRE_SPEC_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUESTIONNAIRE_PDF_RESULT_V1"


class QuestionnairePDFError(RuntimeError):
    pass


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    root = root.resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise QuestionnairePDFError("PATH_OUTSIDE_ROOT")
    return p


def _ascii(value: Any) -> str:
    text = str(value or "")
    text = (
        text.replace("’", "'").replace("‘", "'")
        .replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-")
        .replace("•", "-")
    )
    return unicodedata.normalize("NFKD", text).encode("ascii", "replace").decode("ascii")


def _pdf_escape(text: str) -> str:
    return _ascii(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _validate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping) or spec.get("schema") != SCHEMA:
        raise QuestionnairePDFError("SPEC_SCHEMA_INVALID")
    title = str(spec.get("title") or "").strip()
    if not title:
        raise QuestionnairePDFError("TITLE_REQUIRED")
    pages = spec.get("pages")
    if not isinstance(pages, list) or len(pages) != 3:
        raise QuestionnairePDFError("EXACTLY_THREE_PAGES_REQUIRED")
    normalized = []
    question_count = 0
    for i, raw in enumerate(pages, 1):
        if not isinstance(raw, Mapping):
            raise QuestionnairePDFError(f"PAGE_{i}_INVALID")
        heading = str(raw.get("heading") or "").strip()
        intro = str(raw.get("intro") or "").strip()
        qs = raw.get("questions")
        if not heading or not isinstance(qs, list) or not qs:
            raise QuestionnairePDFError(f"PAGE_{i}_CONTENT_REQUIRED")
        questions = []
        for j, q in enumerate(qs, 1):
            if isinstance(q, str):
                label, answer_lines = q.strip(), 1
            elif isinstance(q, Mapping):
                label = str(q.get("label") or "").strip()
                answer_lines = int(q.get("answer_lines", 1))
            else:
                raise QuestionnairePDFError(f"PAGE_{i}_QUESTION_{j}_INVALID")
            if not label or answer_lines < 1 or answer_lines > 3:
                raise QuestionnairePDFError(f"PAGE_{i}_QUESTION_{j}_INVALID")
            questions.append({"label": label, "answer_lines": answer_lines})
        question_count += len(questions)
        normalized.append({"heading": heading, "intro": intro, "questions": questions})
    return {"title": title, "pages": normalized, "question_count": question_count}


def _text(stream: list[str], x: int, y: int, size: int, value: str) -> None:
    stream.append(f"BT /F1 {size} Tf {x} {y} Td ({_pdf_escape(value)}) Tj ET")


def _line(stream: list[str], x1: int, y1: int, x2: int, y2: int) -> None:
    stream.append(f"{x1} {y1} m {x2} {y2} l S")


def _wrap(value: str, width: int) -> list[str]:
    return textwrap.wrap(_ascii(value), width=width, break_long_words=False, break_on_hyphens=False) or [""]


def _page_stream(title: str, page: Mapping[str, Any], page_number: int) -> bytes:
    s: list[str] = ["0.45 w"]
    y = 748
    _text(s, 54, y, 17, title)
    y -= 25
    _text(s, 54, y, 12, str(page["heading"]))
    y -= 18
    if page.get("intro"):
        for line in _wrap(str(page["intro"]), 88):
            _text(s, 54, y, 9, line)
            y -= 12
        y -= 4
    qn = 1
    for q in page["questions"]:
        wrapped = _wrap(f"{qn}. {q['label']}", 92)
        need = len(wrapped) * 12 + int(q["answer_lines"]) * 15 + 10
        if y - need < 46:
            raise QuestionnairePDFError(f"PAGE_{page_number}_OVERFLOW_AT_QUESTION_{qn}")
        for line in wrapped:
            _text(s, 54, y, 9, line)
            y -= 12
        for _ in range(int(q["answer_lines"])):
            y -= 5
            _line(s, 58, y, 554, y)
            y -= 10
        y -= 5
        qn += 1
    _text(s, 286, 28, 8, f"Page {page_number} of 3")
    return ("\n".join(s) + "\n").encode("ascii")


def _build_pdf(spec: Mapping[str, Any]) -> bytes:
    n = _validate(spec)
    streams = [_page_stream(n["title"], p, i + 1) for i, p in enumerate(n["pages"])]

    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [3 0 R 5 0 R 7 0 R] /Count 3 >>"
    objects[9] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for idx, stream in enumerate(streams):
        page_obj = 3 + idx * 2
        stream_obj = page_obj + 1
        objects[page_obj] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 9 0 R >> >> /Contents {stream_obj} 0 R >>"
        ).encode("ascii")
        objects[stream_obj] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    out = bytearray(b"%PDF-1.4\n%PBQ1\n")
    offsets = {0: 0}
    for obj_id in range(1, 10):
        offsets[obj_id] = len(out)
        out.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        out.extend(objects[obj_id])
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(b"xref\n0 10\n")
    out.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, 10):
        out.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    out.extend(b"trailer\n<< /Size 10 /Root 1 0 R >>\n")
    out.extend(f"startxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(out)


def render(spec: Mapping[str, Any], output_path: pathlib.Path) -> dict[str, Any]:
    normalized = _validate(spec)
    raw = _build_pdf(spec)
    if not raw.startswith(b"%PDF-1.4") or raw.count(b"/Type /Page ") != 3:
        raise QuestionnairePDFError("PDF_STRUCTURAL_VERIFICATION_FAILED")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__DETERMINISTIC_THREE_PAGE_PDF",
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_bytes": len(raw),
        "page_count": 3,
        "question_count": normalized["question_count"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "output_verified": True,
    }


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    rootp = pathlib.Path(root)
    spec_path = _safe(rootp, str(args.get("spec_path") or ""))
    output_path = _safe(rootp, str(args.get("output_path") or ""))
    if not spec_path.is_file():
        raise QuestionnairePDFError("SPEC_FILE_MISSING")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    return render(spec, output_path)
