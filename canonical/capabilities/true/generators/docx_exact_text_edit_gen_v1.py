"""Fresh-instance generator for DOCX_EXACT_TEXT_EDIT_V1.  Must not import the solver.

Each instance is a small but structurally real WordprocessingML package built
from scratch (content types, package rels, document rels, styles, core
properties, document.xml) with 1-12 paragraphs, 1-5 runs per paragraph, random
run properties, xml:space="preserve" on some runs, Unicode text, and a target
text node that occurs exactly once (70 %), zero times (15 %) or 2-3 times
(15 %).  The expected behaviour for the last two is FAIL_CLOSED.
"""
from __future__ import annotations

import base64
import io
import random
import zipfile
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORDS = ("invoice", "total", "Zürich", "naïve", "résumé", "quarter", "Q3", "2026", "∑ risk", "日本語", "عربي",
         "alpha", "beta", "gamma", "<tag>", "a&b", "\"quoted\"", "it's", "x = 1", "tab\tsep")

CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                 '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                 '</Types>')
PACKAGE_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '</Relationships>')
DOCUMENT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                 '</Relationships>')
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')


def _core(rng: random.Random) -> str:
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>doc %d</dc:title><dc:creator>gen</dc:creator></cp:coreProperties>' % rng.randrange(10**6))


def _phrase(rng: random.Random) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 4)))


def _run(text: str, rng: random.Random) -> str:
    rpr = ""
    if rng.random() < 0.4:
        rpr = "<w:rPr>" + rng.choice(("<w:b/>", "<w:i/>", '<w:sz w:val="28"/>', '<w:color w:val="FF0000"/>')) + "</w:rPr>"
    space = ' xml:space="preserve"' if (text != text.strip() or rng.random() < 0.3) else ""
    return f"<w:r>{rpr}<w:t{space}>{escape(text)}</w:t></w:r>"


def _document(paragraphs: list[list[str]], rng: random.Random) -> str:
    body = "".join("<w:p>" + ("<w:pPr><w:jc w:val=\"center\"/></w:pPr>" if rng.random() < 0.2 else "") +
                   "".join(_run(t, rng) for t in runs) + "</w:p>" for runs in paragraphs)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{W}"><w:body>{body}<w:sectPr/></w:body></w:document>')


def _package(paragraphs: list[list[str]], rng: random.Random) -> bytes:
    buf = io.BytesIO()
    members = [("[Content_Types].xml", CONTENT_TYPES), ("_rels/.rels", PACKAGE_RELS), ("word/document.xml", _document(paragraphs, rng)),
               ("word/_rels/document.xml.rels", DOCUMENT_RELS), ("word/styles.xml", STYLES), ("docProps/core.xml", _core(rng))]
    if rng.random() < 0.5:
        members.append(("word/media/blob.bin", bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 64)))))
    rng.shuffle(members)
    with zipfile.ZipFile(buf, "w", compression=rng.choice((zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED))) as z:
        for name, data in members:
            z.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
    return buf.getvalue()


def generate(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        paragraphs = [[_phrase(rng) for _ in range(rng.randint(1, 5))] for _ in range(rng.randint(1, 12))]
        target = "TARGET-" + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(rng.randint(3, 12)))
        if rng.random() < 0.3:
            target = target + " " + rng.choice(WORDS)
        roll = rng.random()
        occurrences = 1 if roll < 0.70 else (0 if roll < 0.85 else rng.randint(2, 3))
        for _ in range(occurrences):
            p = rng.randrange(len(paragraphs))
            paragraphs[p].insert(rng.randint(0, len(paragraphs[p])), target)
        new = rng.choice(("", _phrase(rng), target.upper(), "replaced " + _phrase(rng)))
        if new == target:  # a no-op edit is outside the input class (the kernel fails closed on it by design)
            new = "replaced " + target
        out.append({"docx_b64": base64.b64encode(_package(paragraphs, rng)).decode("ascii"),
                    "old": target, "new": new, "expected_occurrences": occurrences})
    return out
