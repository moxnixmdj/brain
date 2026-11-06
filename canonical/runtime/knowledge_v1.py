#!/usr/bin/env python3
"""Everything the creature has ever established, held inside the creature.

Twenty logs measured ten synthetic worlds. Meanwhile this repository accumulated 2,666 verification
records and twenty-one log entries, and **the creature had read none of them**. Every lesson those
logs contain was transferred by hand: I read the repo, I decided what it meant, and I wrote it into
a module. The knowledge lived in me and in prose. The system held nothing.

That is the static thing underneath every previous log. A creature that cannot answer a question
about its own record, and cannot recognise a claim it has already falsified, is not accumulating
knowledge -- it is being reprogrammed each time by whoever is holding the pen.

So this module ingests the whole record, not a curated slice:

  harvest()    every JSON under canonical/verification, plus every verdict row in the plan. Files
               that cannot be represented are LISTED WITH A REASON, never silently skipped, because
               "knows everything" is only meaningful if it can also say exactly what it does not know.
  ask()        a question against the record, answered with provenance. When the record does not
               contain the answer, the answer is `unknown` -- a real outcome, not a failure.
  conflicts()  a candidate claim, checked against everything already recorded as FALSE. This is the
               seed of unaided closure: you cannot catch your own regression if you do not remember
               what you once disproved.
  refresh()    what arrived since the last snapshot, so the record can grow without being rebuilt.

Honest about what this is NOT: it knows that a record exists, when it was made, and what status it
reported. It does not know what any of it MEANS. Retrieval is token overlap, so a paraphrase is
`unknown`. That limit is tested rather than hidden.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_KNOWLEDGE_V1"
EVIDENCE_DIR = "canonical/verification"
PLAN = "OPTIMAL_PLAN_20261102_V1.md"
SNAPSHOT = "canonical/verification/KNOWLEDGE_V1.json"

VERDICT_FIELDS = ("verified", "proved", "terminal_truth")
STOP_WORDS = frozenset("""a an the of to in on for and or is are was were be been it its this that
these those with without by as at from not no into over under than then so if but does do did what
which who how many much all any each more most some such only own same very can will just should
now record records say says said reported report log logs""".split())


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_]{3,}", str(text).lower())
    return {word for word in words if word not in STOP_WORDS}


def _verdict_of(data: dict) -> str | None:
    """TRUE / FALSE / None, taken from the fields the corpus actually uses, in priority order."""
    for field in VERDICT_FIELDS:
        if field in data and isinstance(data[field], bool):
            return "TRUE" if data[field] else "FALSE"
    status = str(data.get("status") or "").upper()
    if not status:
        return None
    if "FAIL" in status or "REJECT" in status or "REFUT" in status:
        return "FALSE"
    if "PASS" in status or "VERIFIED" in status or "PROVEN" in status:
        return "TRUE"
    return None


def _record(path: str, data: dict) -> dict:
    fields = {key: data.get(key) for key in
              ("schema", "subject", "date", "status", "verified", "proved", "authority",
               "promotion_authority", "incremental_spend_usd", "capability_credit_delta")}
    schema = str(data.get("schema") or Path(path).stem)
    blob = " ".join(str(value) for value in fields.values() if value is not None)
    return {
        "kind": "evidence",
        "source": path,
        "schema": schema,
        "date": fields["date"],
        "status": fields["status"],
        "verdict": _verdict_of(data),
        "fields": {key: value for key, value in fields.items() if value is not None},
        "terms": sorted(_terms(schema) | _terms(blob) | _terms(Path(path).stem)),
    }


PLAN_ROW = re.compile(r"^\|\s*(?P<claim>[^|]+?)\s*\|\s*\*\*(?P<verdict>TRUE|FALSE|PARTIAL|STILL)"
                      r"[^*]*\*\*\s*\|\s*(?P<measure>[^|]*?)\s*\|", re.IGNORECASE)
LOG_REF = re.compile(r"\blog\s*#?\s*(\d{1,2})\b", re.IGNORECASE)


def plan_claims(root: Path = ROOT) -> tuple[list[dict], int]:
    """Every verdict row in the plan, with the log it belongs to. The system's own conclusions."""
    path = root / PLAN
    if not path.exists():
        return [], 0
    claims, log = [], "?"
    total_rows = 0
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            log = line[3:].strip()
        elif line.startswith("|"):
            total_rows += 1
            found = PLAN_ROW.match(line)
            if not found:
                continue
            verdict = found.group("verdict").strip().upper()
            claims.append({
                "kind": "log_claim",
                "source": f"{PLAN}:{log}",
                "log": log,
                "claim": found.group("claim").strip(),
                "verdict": "FALSE" if verdict.startswith("FALSE") else
                           "TRUE" if verdict.startswith("TRUE") else verdict,
                "raw_verdict": verdict,
                "measurement": found.group("measure").strip(),
                "terms": sorted(_terms(found.group("claim")) | _terms(log)),
            })
    return claims, total_rows


def plan_sections(root: Path = ROOT) -> list[dict]:
    """Every log section as a whole, not only its verdict rows.

    Measured 2026-11-06: ingesting only table rows left the store unable to answer `xor3 parity
    separability`, even though both logs discuss it at length. The prose IS the record.
    """
    path = root / PLAN
    if not path.exists():
        return []
    sections, title, body = [], None, []
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            if title and body:
                sections.extend(_section(title, body))
            title, body = line[3:].strip(), []
        elif title:
            body.append(line)
    if title and body:
        sections.extend(_section(title, body))
    return sections


def _section(title: str, body: list[str]) -> list[dict]:
    """One item per paragraph, not one per log.

    Measured 2026-11-06: with a whole log as one document, nearly every word occurred in exactly one
    document and therefore scored maximally rare, so rarity stopped discriminating and
    "who won the football match" matched on the single word `match`. Paragraph granularity restores
    the difference between a term that recurs inside a log and one that appears once.
    """
    paragraphs, current = [], []
    for line in body + [""]:
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            text = " ".join(current)
            if len(text) >= 120:
                paragraphs.append({
                    "kind": "log_text", "source": f"{PLAN}:{title}", "log": title,
                    "claim": text[:400], "verdict": None, "measurement": "",
                    "terms": sorted(_terms(title) | _terms(text))})
            current = []
    return paragraphs


def harvest(root: Path = ROOT) -> dict:
    """Read the entire record. No enumeration of which files matter -- that is the whole point."""
    root = Path(root)
    records, unrepresented = [], []
    files = sorted(glob.glob(str(root / EVIDENCE_DIR / "*.json")))
    for path in files:
        relative = str(Path(path).relative_to(root))
        try:
            data = json.load(open(path))
        except Exception as error:                                   # noqa: BLE001
            unrepresented.append({"source": relative, "why": f"unparseable: {type(error).__name__}"})
            continue
        if not isinstance(data, dict):
            unrepresented.append({"source": relative, "why": f"top-level {type(data).__name__}"})
            continue
        records.append(_record(relative, data))

    claims, table_rows = plan_claims(root)
    sections = plan_sections(root)
    covered = {record["source"] for record in records}
    return {
        "schema": SCHEMA,
        "records": records,
        "claims": claims,
        "sections": sections,
        "unrepresented": unrepresented,
        "coverage": {
            "evidence_files": len(files),
            "represented": len(covered),
            "unrepresented": len(unrepresented),
            "log_claims": len(claims),
            "log_sections": len(sections),
            "plan_table_rows": table_rows,
            "fraction_represented": round(len(covered) / len(files), 4) if files else 0.0,
        },
    }


def _inverse_frequency(store: dict) -> dict[str, float]:
    """How much a term narrows the record. "the" tells you nothing; "xor3" tells you a lot."""
    import math
    items = store["records"] + store["claims"] + store.get("sections", [])
    frequency: dict[str, int] = {}
    for item in items:
        for term in set(item["terms"]):
            frequency[term] = frequency.get(term, 0) + 1
    total = max(1, len(items))
    return {term: math.log(1 + total / (1 + count)) for term, count in frequency.items()}


def ask(store: dict, question: str, limit: int = 3, share: float = 0.55) -> dict:
    """Answer from the record, with provenance. `unknown` when the record does not contain it.

    Two corrections measured 2026-11-06, both against real misbehaviour:

    - Rarer terms must count more. Counting overlaps let "what did log 19 conclude about program
      synthesis" return a log-16 claim, because `program` and `synthesis` were common enough to win.
    - A question naming a log must be answered from that log, so `log 19` is a filter rather than
      three unimportant tokens.

    A word the record has never used counts as much as one it has: a question carried by its subject
    words is refused, and a match explaining under 55% of the question is `unknown` rather than an
    approximate answer. When the question names a log, the log reference IS the location, so the
    share test is replaced by "shares at least one rare term inside that log": an assistant that confidently returns an unrelated record is worse than one
    that admits it does not hold the answer.
    """
    import math
    wanted = _terms(question)
    if not wanted:
        return {"status": "unknown", "question": question,
                "reason": "the question contains no searchable terms"}

    pool = store["records"] + store["claims"] + store.get("sections", [])
    narrowed = []
    referenced = LOG_REF.findall(question)
    if referenced:
        narrowed = [claim for claim in store["claims"] + store.get("sections", [])
                    if any(reference in claim["log"] for reference in referenced)]
        if narrowed:
            pool = narrowed

    weights = _inverse_frequency(store)
    # A word the record has NEVER used is evidence against the answer, not a neutral absence: it is
    # usually the subject of the question ("cairo", "football"). It counts at half the weight of a
    # rarest known term, so a question carried by its subject words is refused while a question whose
    # subject the record does use survives its scaffolding ("conclude", "approach").
    present = [term for term in wanted if term in weights]
    absent = [term for term in wanted if term not in weights]
    rarest = max(weights.values(), default=0.0)
    total_weight = sum(weights[term] for term in present) + rarest * len(absent)
    distinctive = max((weights[term] for term in present), default=0.0)

    scored = []
    for item in pool:
        shared = wanted & set(item["terms"])
        if not shared:
            continue
        weight = sum(weights[term] for term in shared if term in weights)
        scored.append((weight, len(shared), item, sorted(shared)))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    if not scored or not present:
        return {"status": "unknown", "question": question,
                "reason": f"the record never mentions {sorted(wanted)[:6]}"}

    weight, shared_count, best, shared = scored[0]
    explained = weight / total_weight if total_weight else 0.0
    # A match made only of common words is not knowledge. Require the winning record to share at
    # least one term near the top of the rarity scale, so "the record about X" cannot be answered
    # by a section that merely uses the same filler.
    if not any(weights[term] >= 0.6 * distinctive for term in shared):
        return {"status": "unknown", "question": question,
                "reason": f"only common terms matched ({shared[:5]})",
                "closest": best["source"]}
    if not narrowed and explained < share:
        return {"status": "unknown", "question": question,
                "reason": f"the closest record explains only {explained:.2f} of the question "
                          f"(shared: {shared[:6]})",
                "closest": best["source"]}
    if best["kind"] == "log_text":
        answer = f"[{best['log']}] {best['claim'][:260]}"
    elif best["kind"] == "log_claim":
        answer = f"{best['raw_verdict']} -- {best['claim']} ({best['measurement']})"
    else:
        answer = f"status {best['status']}, verdict {best['verdict']}, schema {best['schema']}"
    return {"status": "known", "question": question, "answer": answer,
            "provenance": best["source"], "explained": round(explained, 3), "shared": shared[:8],
            "alternatives": [item["source"] for _, _, item, _ in scored[1:limit]]}


def conflicts(store: dict, candidate: dict, least_overlap: int = 2) -> list[dict]:
    """Everything already recorded that says the opposite of `candidate`.

    A claim the record falsified must not be admissible again without new evidence, and the system
    has to be the one to notice. Lexical, so this catches restatements, not rephrasings -- stated
    as a limitation in the probe rather than papered over.
    """
    wanted = _terms(candidate.get("claim") or candidate.get("text") or "")
    verdict = str(candidate.get("verdict", "")).upper()
    if verdict not in ("TRUE", "FALSE"):
        return []
    opposite = "FALSE" if verdict == "TRUE" else "TRUE"
    out = []
    for item in store["claims"] + store["records"]:
        if item.get("verdict") != opposite:
            continue
        shared = wanted & set(item["terms"])
        if len(shared) >= least_overlap:
            out.append({"source": item["source"], "verdict": item["verdict"],
                        "says": item.get("claim") or item.get("status"),
                        "shared": sorted(shared)})
    return out


def self_contradictions(store: dict) -> list[dict]:
    """Does the record disagree with itself? Same schema, opposite verdicts, no explanation."""
    grouped: dict[str, set[str]] = {}
    for record in store["records"]:
        if record["verdict"]:
            grouped.setdefault(record["schema"], set()).add(record["verdict"])
    return [{"schema": schema, "verdicts": sorted(verdicts)}
            for schema, verdicts in sorted(grouped.items()) if len(verdicts) > 1]


def refresh(previous: dict | None, root: Path = ROOT) -> dict:
    """What is new since the last snapshot -- the record growing without being rebuilt by hand."""
    current = harvest(root)
    if not previous:
        return {"new_evidence": [], "new_claims": [], "counts": current["coverage"]}
    known = {record["source"] for record in previous.get("records", [])}
    known_claims = {claim["source"] + claim["claim"] for claim in previous.get("claims", [])}
    return {
        "new_evidence": sorted({record["source"] for record in current["records"]} - known),
        "new_claims": sorted({claim["source"] + claim["claim"] for claim in current["claims"]}
                             - known_claims),
        "counts": current["coverage"],
        "current": current,
    }


def describe(store: dict) -> dict:
    verdicts: dict[str, int] = {}
    for item in store["claims"] + store["records"]:
        verdicts[str(item.get("verdict"))] = verdicts.get(str(item.get("verdict")), 0) + 1
    return {"schema": store["schema"], "coverage": store["coverage"], "verdicts": verdicts,
            "unrepresented": store["unrepresented"][:8],
            "self_contradictions": len(self_contradictions(store))}
