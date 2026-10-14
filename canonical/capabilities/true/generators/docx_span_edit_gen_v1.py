"""Fresh-instance generators for the DOCX span editors.  Must not import a solver.

* generate_span         -> DOCX_RUN_SPAN_REPLACE_V1       (one target, may span several runs)
* generate_transaction  -> DOCX_TEXT_EDIT_TRANSACTION_V1  (1-6 targets, atomic; overlaps planted)
* generate_story        -> DOCX_STORY_PART_REPLACE_V1     (target inside a header/footer/footnotes part)

Packages are small but structurally real WordprocessingML (content types, package
and document relationships, styles, core properties, optional media, optional
header/footer/footnotes parts).  Targets are cut from the visible paragraph text
at run boundaries or across them, so a target usually covers 1-3 w:t nodes.  The
generator does not decide the expected outcome; the oracles derive it from the
package.
"""
from __future__ import annotations

import base64
import io
import random
import zipfile
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORDS = ("invoice", "total", "Zürich", "naïve", "résumé", "quarter", "Q3", "2026", "∑ risk", "日本語", "عربي",
         "alpha", "beta", "gamma", "<tag>", "a&b", "\"quoted\"", "it's", "x = 1", "tab\tsep", "net 30", "draft")
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

CT_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
           '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
           '<Default Extension="xml" ContentType="application/xml"/>'
           '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
           '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
           '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>')
STORY_CT = {
    "header": "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
    "footer": "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
    "footnotes": "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
    "endnotes": "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml",
    "comments": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
}
STORY_ROOT = {"header": "hdr", "footer": "ftr", "footnotes": "footnotes", "endnotes": "endnotes", "comments": "comments"}
PACKAGE_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '</Relationships>')
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')


def _core(rng: random.Random) -> str:
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>doc %d</dc:title><dc:creator>gen</dc:creator></cp:coreProperties>' % rng.randrange(10**6))


def _phrase(rng: random.Random) -> str:
    words = [rng.choice(WORDS) for _ in range(rng.randint(1, 4))]
    if rng.random() < 0.5:  # numbered tokens keep the vocabulary from repeating itself inside one document
        words[rng.randrange(len(words))] += str(rng.randint(0, 9999))
    return " ".join(words)


def _run(text: str, rng: random.Random) -> str:
    rpr = ""
    if rng.random() < 0.4:
        rpr = "<w:rPr>" + rng.choice(("<w:b/>", "<w:i/>", '<w:sz w:val="28"/>', '<w:color w:val="FF0000"/>')) + "</w:rPr>"
    space = ' xml:space="preserve"' if (text != text.strip() or rng.random() < 0.3) else ""
    return f"<w:r>{rpr}<w:t{space}>{escape(text)}</w:t></w:r>"


def _paragraphs_xml(paragraphs: list[list[str]], rng: random.Random) -> str:
    return "".join("<w:p>" + ("<w:pPr><w:jc w:val=\"center\"/></w:pPr>" if rng.random() < 0.2 else "") +
                   "".join(_run(t, rng) for t in runs) + "</w:p>" for runs in paragraphs)


def _document(paragraphs: list[list[str]], rng: random.Random, story_refs: list[str]) -> str:
    refs = "".join(f'<w:{kind}Reference w:type="default" r:id="{rid}"/>' for kind, rid in
                   ((("header" if n.startswith("word/header") else "footer"), f"rId{10 + i}") for i, n in enumerate(story_refs) if n.startswith(("word/header", "word/footer"))))
    sect = f"<w:sectPr>{refs}</w:sectPr>" if refs else "<w:sectPr/>"
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<w:body>{_paragraphs_xml(paragraphs, rng)}{sect}</w:body></w:document>')


def _story_part(kind: str, paragraphs: list[list[str]], rng: random.Random) -> str:
    root = STORY_ROOT[kind]
    inner = _paragraphs_xml(paragraphs, rng)
    if kind in ("footnotes", "endnotes"):
        tag = "footnote" if kind == "footnotes" else "endnote"
        inner = "".join(f'<w:{tag} w:id="{i}">' + "<w:p>" + "".join(_run(t, rng) for t in runs) + "</w:p>" + f"</w:{tag}>" for i, runs in enumerate(paragraphs))
    if kind == "comments":
        inner = "".join(f'<w:comment w:id="{i}" w:author="gen">' + "<w:p>" + "".join(_run(t, rng) for t in runs) + "</w:p>" + "</w:comment>" for i, runs in enumerate(paragraphs))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:{root} xmlns:w="{W}">{inner}</w:{root}>')


def _package(paragraphs: list[list[str]], rng: random.Random, stories: dict[str, list[list[str]]] | None = None) -> bytes:
    stories = stories or {}
    names = sorted(stories)
    ct = CT_HEAD
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    members: list[tuple[str, bytes | str]] = []
    for i, name in enumerate(names):
        kind = next(k for k in STORY_CT if name.startswith("word/" + k))
        ct += f'<Override PartName="/{name}" ContentType="{STORY_CT[kind]}"/>'
        rels += f'<Relationship Id="rId{10 + i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}" Target="{name[5:]}"/>'
        members.append((name, _story_part(kind, stories[name], rng)))
    ct += "</Types>"
    rels += "</Relationships>"
    members += [("[Content_Types].xml", ct), ("_rels/.rels", PACKAGE_RELS), ("word/document.xml", _document(paragraphs, rng, names)),
                ("word/_rels/document.xml.rels", rels), ("word/styles.xml", STYLES), ("docProps/core.xml", _core(rng))]
    if rng.random() < 0.5:
        members.append(("word/media/blob.bin", bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 64)))))
    rng.shuffle(members)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=rng.choice((zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED))) as z:
        for name, data in members:
            z.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
    return buf.getvalue()


def _cut_span(paragraphs: list[list[str]], rng: random.Random, pidx: int | None = None) -> tuple[int, str]:
    """Cut a 3-30 character target from one paragraph's visible text, usually across run boundaries."""
    if pidx is None:
        pidx = rng.randrange(len(paragraphs))
    runs = paragraphs[pidx]
    text = "".join(runs)
    if len(text) < 3:
        return pidx, text or runs[0]
    bounds = []
    pos = 0
    for r in runs[:-1]:
        pos += len(r)
        bounds.append(pos)
    if bounds and rng.random() < 0.7:
        b = rng.choice(bounds)
        start = max(0, b - rng.randint(1, 14))
        end = min(len(text), b + rng.randint(2, 14))
    else:
        start = rng.randrange(0, max(1, len(text) - 2))
        end = min(len(text), start + rng.randint(5, 30))
    while end - start < 8 and (start > 0 or end < len(text)):  # short cuts are rarely unique; widen when possible
        start, end = max(0, start - 1), min(len(text), end + 1)
    return pidx, text[start:end] or text[:3]


def _new_text(rng: random.Random, old: str) -> str:
    new = rng.choice(("", _phrase(rng), old.upper(), "replaced " + _phrase(rng), old + " (rev)"))
    return new if new != old else "replaced " + old


def _body(rng: random.Random) -> list[list[str]]:
    return [[_phrase(rng) for _ in range(rng.randint(1, 5))] for _ in range(rng.randint(1, 12))]


def _plant(paragraphs: list[list[str]], text: str, rng: random.Random) -> None:
    p = rng.randrange(len(paragraphs))
    paragraphs[p].insert(rng.randint(0, len(paragraphs[p])), text)


def _self_overlapping(paragraphs: list[list[str]], rng: random.Random) -> str:
    """Plant a periodic string u*3 (split over 1-2 runs) and return the target u*2, which occurs twice when
    overlapping occurrences are counted and once when they are not."""
    unit = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(2, 4)))
    text = unit * 3
    p = rng.randrange(len(paragraphs))
    at = rng.randint(0, len(paragraphs[p]))
    if rng.random() < 0.5:
        k = rng.randint(1, len(text) - 1)
        paragraphs[p][at:at] = [text[:k], text[k:]]
    else:
        paragraphs[p].insert(at, text)
    return unit * 2


def _touching_pair(paragraphs: list[list[str]], rng: random.Random) -> tuple[str, str] | None:
    """Two adjacent targets text[s:m] and text[m:e] from one paragraph (touching spans must be accepted)."""
    pidx = rng.randrange(len(paragraphs))
    text = "".join(paragraphs[pidx])
    if len(text) < 6:
        return None
    s = rng.randrange(0, len(text) - 5)
    m = rng.randint(s + 2, min(len(text) - 2, s + 15))
    e = rng.randint(m + 2, min(len(text), m + 15))
    return text[s:m], text[m:e]


def generate_span(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        paragraphs = _body(rng)
        roll = rng.random()
        if roll < 0.68:
            _, old = _cut_span(paragraphs, rng)
        elif roll < 0.80:
            old = "ABSENT-" + "".join(rng.choice(ALPHABET) for _ in range(rng.randint(3, 10)))
        elif roll < 0.93:
            _, old = _cut_span(paragraphs, rng)
            for _ in range(rng.randint(1, 2)):
                _plant(paragraphs, old, rng)
        else:
            old = _self_overlapping(paragraphs, rng)
        out.append({"docx_b64": base64.b64encode(_package(paragraphs, rng)).decode("ascii"), "old": old, "new": _new_text(rng, old)})
    return out


def generate_transaction(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        paragraphs = _body(rng)
        edits = []
        free = list(range(len(paragraphs)))
        rng.shuffle(free)
        for _ in range(rng.randint(1, min(6, len(paragraphs) + 1))):
            pidx = free.pop() if (free and rng.random() < 0.9) else None  # mostly distinct paragraphs
            _, old = _cut_span(paragraphs, rng, pidx)
            edits.append({"old": old, "new": _new_text(rng, old)})
        roll = rng.random()
        if roll < 0.12:
            # planted overlap: a second target cut from inside the first one's paragraph text, sharing characters
            victim = rng.choice(edits)["old"]
            if len(victim) >= 4:
                k = rng.randint(1, len(victim) - 1)
                edits.append({"old": victim[k:] + "" if rng.random() < 0.5 else victim[:k], "new": _phrase(rng)})
        elif roll < 0.20:
            edits.append({"old": "ABSENT-" + "".join(rng.choice(ALPHABET) for _ in range(6)), "new": _phrase(rng)})
        elif roll < 0.28:
            dup = rng.choice(edits)["old"]
            _plant(paragraphs, dup, rng)
        elif roll < 0.43:
            pair = _touching_pair(paragraphs, rng)
            if pair:
                edits = [{"old": pair[0], "new": _new_text(rng, pair[0])}, {"old": pair[1], "new": _new_text(rng, pair[1])}] + edits[:2]
        elif roll < 0.48:
            old = _self_overlapping(paragraphs, rng)
            edits.append({"old": old, "new": _new_text(rng, old)})
        edits = [e for e in edits if e["old"]]
        rng.shuffle(edits)
        out.append({"docx_b64": base64.b64encode(_package(paragraphs, rng)).decode("ascii"), "edits": edits})
    return out


def generate_story(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        paragraphs = _body(rng)
        kinds = rng.sample(list(STORY_CT), k=rng.randint(1, 3))
        stories = {}
        for kind in kinds:
            name = f"word/{kind}{rng.randint(1, 3)}.xml" if kind in ("header", "footer") else f"word/{kind}.xml"
            stories[name] = [[_phrase(rng) for _ in range(rng.randint(1, 4))] for _ in range(rng.randint(1, 5))]
        part = rng.choice(sorted(stories))
        roll = rng.random()
        if roll < 0.65:
            _, old = _cut_span(stories[part], rng)
            if rng.random() < 0.3:
                _plant(paragraphs, old, rng)  # same text in the main document must not count
        elif roll < 0.75:
            old = "ABSENT-" + "".join(rng.choice(ALPHABET) for _ in range(6))
        elif roll < 0.85:
            _, old = _cut_span(stories[part], rng)
            _plant(stories[part], old, rng)
        elif roll < 0.90:
            _, old = _cut_span(stories[part], rng)
            part = rng.choice(("word/header9.xml", "word/footer7.xml", "word/endnotes.xml"))  # allowed name, possibly missing
        elif roll < 0.94:
            old = _self_overlapping(stories[part], rng)
        elif roll < 0.98:
            _, old = _cut_span(paragraphs, rng)  # present in the body, but the body is not a story part
            part = "word/document.xml"
        else:
            _, old = _cut_span(stories[part], rng)
            part = rng.choice(("word/styles.xml", "word/header0.xml", "docProps/core.xml", "word/Header1.xml"))  # not a story part
        out.append({"docx_b64": base64.b64encode(_package(paragraphs, rng, stories)).decode("ascii"),
                    "part_name": part, "old": old, "new": _new_text(rng, old)})
    return out
