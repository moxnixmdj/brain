"""Oracles for the DOCX span editors.  Must not import a solver.

Visible paragraph text is derived with namespace-aware xml.dom.minidom (a different
parser from the solvers): for every {wordprocessingml}p element, the concatenation
of its descendant {wordprocessingml}t text.  "Unique" means exactly one start
position over all paragraphs of the edited part, counting overlapping
occurrences, because a self-overlapping target is ambiguous.

  oracles_span         EXPECTED_OUTCOME / PACKAGE_INTEGRITY / INVERSE_EDIT_RESTORES
  oracles_transaction  EXPECTED_OUTCOME / PACKAGE_INTEGRITY / ATOMICITY_AND_INVERSE
  oracles_story        EXPECTED_OUTCOME / PACKAGE_INTEGRITY / INVERSE_EDIT_RESTORES
"""
from __future__ import annotations

import base64
import io
import re
import zipfile
from xml.dom import minidom

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
STORY_PART = re.compile(r"^word/(?:header[1-9][0-9]*|footer[1-9][0-9]*|footnotes|endnotes|comments)\.xml$")


def _members(blob: bytes) -> list[tuple[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return [(i.filename, z.read(i.filename)) for i in z.infolist()]


def _para_texts(xml: bytes) -> list[str]:
    dom = minidom.parseString(xml)
    out = []
    for p in dom.getElementsByTagNameNS(W_NS, "p"):
        out.append("".join("".join(c.data for c in t.childNodes if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE))
                           for t in p.getElementsByTagNameNS(W_NS, "t")))
    return out


def _t_count(xml: bytes) -> int:
    return len(minidom.parseString(xml).getElementsByTagNameNS(W_NS, "t"))


def _starts(text: str, needle: str) -> list[int]:
    out, i = [], 0
    while needle:
        j = text.find(needle, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1
    return out


def _matches(texts: list[str], needle: str) -> list[tuple[int, int]]:
    return [(p, s) for p, t in enumerate(texts) for s in _starts(t, needle)]


def _blob(inst, key="docx_b64") -> bytes:
    return base64.b64decode(inst[key])


def _expected_after(texts: list[str], plan: list[tuple[int, int, int, str]]) -> list[str]:
    """plan: (paragraph, start, end, new) with non-overlapping spans; applied right-to-left per paragraph."""
    out = list(texts)
    by_p: dict[int, list[tuple[int, int, str]]] = {}
    for p, s, e, new in plan:
        by_p.setdefault(p, []).append((s, e, new))
    for p, spans in by_p.items():
        text = out[p]
        for s, e, new in sorted(spans, reverse=True):
            text = text[:s] + new + text[e:]
        out[p] = text
    return out


def _fail_closed_ok(out) -> bool:
    return out.get("status") == "FAIL_CLOSED" and out.get("output_docx_b64") is None and not out.get("output_file_left_behind_on_failure")


def _integrity(src: bytes, dst: bytes, edited_part: str):
    with zipfile.ZipFile(io.BytesIO(dst)) as z:
        if z.testzip() is not None:
            return False, "corrupt member"
    a, b = _members(src), _members(dst)
    if [n for n, _ in a] != [n for n, _ in b]:
        return False, "member names/order changed"
    for (n1, d1), (n2, d2) in zip(a, b):
        if n1 != edited_part and d1 != d2:
            return False, f"member {n1} mutated"
    try:
        minidom.parseString(dict(b)[edited_part])
    except Exception as exc:  # noqa: BLE001
        return False, f"{edited_part} not well-formed: {type(exc).__name__}"
    if _t_count(dict(a)[edited_part]) != _t_count(dict(b)[edited_part]):
        return False, "text node count changed"
    if len(_para_texts(dict(a)[edited_part])) != len(_para_texts(dict(b)[edited_part])):
        return False, "paragraph count changed"
    return True, "package intact"


# ----------------------------------------------------------------------------- one span
def _single_target_oracles(part_of, extra_key=None):
    """Shared oracle set for 'replace one unique span in part X'."""

    def expected_outcome(inst, out, solve):
        part = part_of(inst)
        src = dict(_members(_blob(inst)))
        if part is None or part not in src:
            return _fail_closed_ok(out), f"part {part!r} not editable/present: status={out.get('status')} reason={out.get('reason')}"
        texts = _para_texts(src[part])
        m = _matches(texts, inst["old"])
        if len(m) != 1:
            return _fail_closed_ok(out), f"{len(m)} occurrences: status={out.get('status')} reason={out.get('reason')}"
        if out.get("status") != "PASS" or not out.get("output_docx_b64"):
            return False, f"unique target but status={out.get('status')} reason={out.get('reason')}"
        p, s = m[0]
        expected = _expected_after(texts, [(p, s, s + len(inst["old"]), inst["new"])])
        got = _para_texts(dict(_members(_blob(out, "output_docx_b64")))[part])
        return got == expected, "paragraph texts " + ("match" if got == expected else "differ")

    def package_integrity(inst, out, solve):
        if out.get("status") != "PASS":
            return True, "not applicable"
        return _integrity(_blob(inst), _blob(out, "output_docx_b64"), part_of(inst))

    def inverse_edit_restores(inst, out, solve):
        if out.get("status") != "PASS":
            return True, "not applicable"
        if inst["new"] == "":
            return True, "not applicable (empty replacement has no inverse target)"
        part = part_of(inst)
        dst = _blob(out, "output_docx_b64")
        if len(_matches(_para_texts(dict(_members(dst))[part]), inst["new"])) != 1:
            return True, "not applicable (new text not unique in output)"
        back_inst = dict(inst, docx_b64=out["output_docx_b64"], old=inst["new"], new=inst["old"])
        back = solve(back_inst)
        if back.get("status") != "PASS":
            return False, f"inverse edit failed: {back.get('reason')}"
        orig = _para_texts(dict(_members(_blob(inst)))[part])
        restored = _para_texts(dict(_members(_blob(back, "output_docx_b64")))[part])
        return orig == restored, "restored" if orig == restored else "paragraph texts not restored"

    return [
        {"id": "EXPECTED_OUTCOME", "check": expected_outcome},
        {"id": "PACKAGE_INTEGRITY", "check": package_integrity},
        {"id": "INVERSE_EDIT_RESTORES", "check": inverse_edit_restores},
    ]


def oracles_span():
    return _single_target_oracles(lambda inst: "word/document.xml")


def oracles_story():
    def part_of(inst):
        name = inst.get("part_name")
        return name if isinstance(name, str) and STORY_PART.fullmatch(name) else None
    return _single_target_oracles(part_of)


# ----------------------------------------------------------------------------- transaction
def _plan(texts: list[str], edits: list[dict]):
    """Returns (plan, reason). reason is None when every target is unique and no two spans overlap."""
    plan = []
    for e in edits:
        if not e["old"]:
            return None, "empty target"
        m = _matches(texts, e["old"])
        if len(m) != 1:
            return None, f"target {e['old']!r} has {len(m)} occurrences"
        p, s = m[0]
        plan.append((p, s, s + len(e["old"]), e["new"]))
    by_p: dict[int, list[tuple[int, int]]] = {}
    for p, s, e, _ in plan:
        by_p.setdefault(p, []).append((s, e))
    for p, spans in by_p.items():
        spans.sort()
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            if s2 < e1:
                return None, f"overlap in paragraph {p}"
    return plan, None


def oracles_transaction():
    def expected_outcome(inst, out, solve):
        src = dict(_members(_blob(inst)))
        texts = _para_texts(src["word/document.xml"])
        if not inst["edits"] or len(inst["edits"]) > 64:
            return _fail_closed_ok(out), "edit set outside 1..64"
        plan, reason = _plan(texts, inst["edits"])
        if plan is None:
            return _fail_closed_ok(out), f"{reason}: status={out.get('status')} reason={out.get('reason')}"
        if out.get("status") != "PASS" or not out.get("output_docx_b64"):
            return False, f"all targets unique and disjoint but status={out.get('status')} reason={out.get('reason')}"
        expected = _expected_after(texts, plan)
        got = _para_texts(dict(_members(_blob(out, "output_docx_b64")))["word/document.xml"])
        return got == expected, f"{len(plan)} edits: paragraph texts " + ("match" if got == expected else "differ")

    def package_integrity(inst, out, solve):
        if out.get("status") != "PASS":
            return True, "not applicable"
        return _integrity(_blob(inst), _blob(out, "output_docx_b64"), "word/document.xml")

    def atomicity_and_inverse(inst, out, solve):
        """Appending one impossible edit must fail the whole transaction with nothing written; and when every
        replacement is non-empty and unique in the output, the inverse transaction restores the original text."""
        src = dict(_members(_blob(inst)))
        texts = _para_texts(src["word/document.xml"])
        poisoned = dict(inst, edits=list(inst["edits"]) + [{"old": "NEVER-PRESENT-\u2603-" + str(len(texts)), "new": "x"}])
        bad = solve(poisoned)
        if not _fail_closed_ok(bad):
            return False, f"transaction with an impossible edit did not fail closed cleanly: {bad.get('status')} left_behind={bad.get('output_file_left_behind_on_failure')}"
        if out.get("status") != "PASS":
            return True, "atomic refusal verified; no inverse (instance fails closed)"
        dst_texts = _para_texts(dict(_members(_blob(out, "output_docx_b64")))["word/document.xml"])
        if any(e["new"] == "" or len(_matches(dst_texts, e["new"])) != 1 for e in inst["edits"]):
            return True, "atomic refusal verified; inverse not applicable (empty or non-unique replacement)"
        back_plan, reason = _plan(dst_texts, [{"old": e["new"], "new": e["old"]} for e in inst["edits"]])
        if back_plan is None:
            return True, f"atomic refusal verified; inverse not applicable ({reason})"
        back = solve({"docx_b64": out["output_docx_b64"], "edits": [{"old": e["new"], "new": e["old"]} for e in inst["edits"]]})
        if back.get("status") != "PASS":
            return False, f"inverse transaction failed: {back.get('reason')}"
        restored = _para_texts(dict(_members(_blob(back, "output_docx_b64")))["word/document.xml"])
        return restored == texts, "atomic refusal verified; " + ("restored" if restored == texts else "inverse did not restore the text")

    return [
        {"id": "EXPECTED_OUTCOME", "check": expected_outcome},
        {"id": "PACKAGE_INTEGRITY", "check": package_integrity},
        {"id": "ATOMICITY_AND_INVERSE", "check": atomicity_and_inverse},
    ]
