"""The external evidence ledger: what the cited papers actually say, at which version.

Why this exists
---------------
Every strategic decision in this repository is steered by external research. Until 2026-11-13
that research was cited from memory: no version, no quoted sentence, no date. Two defects follow
mechanically, and both had already happened:

  * a paper is quoted without a version, so numbers from a superseded preprint keep being
    repeated as current fact (SkillsBench: +16.2 pp / 84 tasks is v1-v3; v4 says +16.6 pp / 87
    tasks and does not carry the self-generated arm at abstract level);
  * nothing separates "the abstract says this" from "the abstract is silent and I have this
    number from somewhere I cannot point at".

A ledger row is the smallest object that can be re-checked: id, version, date fetched, the claim
the repository is allowed to make, and the verbatim words that carry it. This tool does not
judge whether a paper is right. It judges whether the repository is allowed to say a thing.

What it enforces
----------------
  --check    structural invariants. Fails closed on a row that cannot be re-checked.
  --census   every arXiv citation in the tree, classified PINNED / UNPINNED / VERSION_MISMATCH.

The census is not a wall. The tree cites ~60 ids and this ledger audits the ones that carry a
decision. An UNPINNED id is a statement of account, not a failure: it says nobody has checked
that one yet.

Authority: NONE. Offline. No network, no model, no independent verifier. A row is one producer
reading one abstract on one date, and it is worth exactly that.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = ROOT / "canonical" / "research_sources" / "EXTERNAL_EVIDENCE_LEDGER_V1.json"

SCHEMA = "external_evidence_ledger_v1"
SUPPORT_LEVELS = ("ABSTRACT_CONFIRMS", "ABSTRACT_SILENT", "VERSION_DRIFT", "MISATTRIBUTED")
DRIFT_LEVELS = ("VERSION_DRIFT", "MISATTRIBUTED")
# An ABSTRACT_SILENT row may disclaim, but must not assert. This is the mechanical form of that
# rule: if the row says anything at all about what may be claimed, it must say the claim is not
# verified here.
SILENT_DISCLAIMER = "not verified"

ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
VERSION_RE = re.compile(r"^v\d+$")
CITATION_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?")

SCAN_SUFFIXES = (".md", ".py")
SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", ".mypy_cache"})
MAX_SCAN_BYTES = 2_000_000

# The instrument and its test carry synthetic ids on purpose (a citation that must come back
# UNPINNED, a version that must come back VERSION_MISMATCH). Counting them would make the census
# report its own fixtures as defects.
SKIP_FILES = frozenset({
    "canonical/tools/external_evidence_ledger_v1.py",
    "canonical/tests/test_external_evidence_ledger_v1.py",
})

PINNED = "PINNED"
UNPINNED = "UNPINNED"
VERSION_MISMATCH = "VERSION_MISMATCH"


# ---------------------------------------------------------------------------------------------
# Loading and structural validation
# ---------------------------------------------------------------------------------------------
def load(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else DEFAULT_LEDGER
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate(ledger: dict[str, Any]) -> list[str]:
    """Return a list of structural errors. Empty means the ledger can be relied on to re-check."""
    errors: list[str] = []

    if ledger.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, found {ledger.get('schema')!r}")

    sources = ledger.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty list")
        sources = []

    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(sources):
        where = f"sources[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{where} is not an object")
            continue
        sid = row.get("id")
        if not isinstance(sid, str) or not ID_RE.match(sid):
            errors.append(f"{where}.id {sid!r} is not an arXiv id of the form NNNN.NNNN[N]")
        version = row.get("version")
        level = row.get("support_level")
        if level not in SUPPORT_LEVELS:
            errors.append(f"{where}.support_level {level!r} not in {SUPPORT_LEVELS}")
        if version != "unverified" and not (isinstance(version, str) and VERSION_RE.match(version)):
            errors.append(f"{where}.version {version!r} is not v<N> and is not 'unverified'")
        if version == "unverified" and level != "ABSTRACT_SILENT":
            errors.append(f"{where}: an unaudited version may only be ABSTRACT_SILENT")
        if not str(row.get("title") or "").strip():
            errors.append(f"{where}.title is empty")
        if not str(row.get("fetched") or "").strip():
            errors.append(f"{where}.fetched is empty: a row with no read date cannot be re-checked")
        if level == "ABSTRACT_CONFIRMS" and not str(row.get("quote") or "").strip():
            errors.append(
                f"{where} ({sid}): ABSTRACT_CONFIRMS with no verbatim quote. "
                "That is exactly the failure this ledger exists to prevent."
            )
        if level == "ABSTRACT_SILENT":
            claim = str(row.get("claim_allowed") or "").strip()
            if claim and SILENT_DISCLAIMER not in claim.lower():
                errors.append(
                    f"{where} ({sid}): ABSTRACT_SILENT row states a claim without the words "
                    f"{SILENT_DISCLAIMER!r}. A silent abstract licenses nothing on its own."
                )
        if isinstance(sid, str) and isinstance(version, str):
            key = (sid, version)
            if key in seen:
                errors.append(f"{where}: duplicate row for {sid}{version}")
            seen.add(key)

    drift = ledger.get("drift", [])
    if not isinstance(drift, list):
        errors.append("drift must be a list")
        drift = []
    for i, row in enumerate(drift):
        where = f"drift[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{where} is not an object")
            continue
        sid = row.get("id")
        if not isinstance(sid, str) or not ID_RE.match(sid):
            errors.append(f"{where}.id {sid!r} is not an arXiv id")
        if row.get("support_level") not in DRIFT_LEVELS:
            errors.append(f"{where}.support_level must be one of {DRIFT_LEVELS}")
        if not str(row.get("what_broke") or "").strip():
            errors.append(f"{where}.what_broke is empty: name the defect, not just the drift")
        for doc in row.get("documents_repeating_the_stale_numbers", []):
            if not (ROOT / doc).exists():
                errors.append(f"{where}: named document {doc!r} does not exist in this tree")

    unsourced = ledger.get("claims_with_no_primary_source", [])
    if not isinstance(unsourced, list):
        errors.append("claims_with_no_primary_source must be a list")
        unsourced = []
    for i, row in enumerate(unsourced):
        where = f"claims_with_no_primary_source[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{where} is not an object")
            continue
        for key in ("text", "status", "correct_action"):
            if not str(row.get(key) or "").strip():
                errors.append(f"{where}.{key} is empty")

    return errors


# ---------------------------------------------------------------------------------------------
# Census: does the tree cite anything it has not audited?
# ---------------------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Citation:
    id: str
    version: str | None
    path: str
    line: int
    state: str


def iter_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in SCAN_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
        except OSError:
            continue
        yield path


def iter_citations(root: Path, ledger: dict[str, Any] | None = None) -> Iterator[Citation]:
    pinned: dict[str, set[str]] = {}
    if ledger:
        # A paper audited in the compact list is audited; the census must not call it unpinned.
        for section in ("sources", "audited_elsewhere"):
            for row in ledger.get(section, []):
                sid = row.get("id")
                ver = row.get("version")
                if isinstance(sid, str):
                    pinned.setdefault(sid, set())
                    if isinstance(ver, str) and ver != "unverified":
                        pinned[sid].add(ver)

    root = Path(root)
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        if rel in SKIP_FILES:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in CITATION_RE.finditer(line):
                sid, ver = match.group(1), match.group(2)
                if sid not in pinned:
                    state = UNPINNED
                elif ver and ver not in pinned[sid]:
                    state = VERSION_MISMATCH
                else:
                    state = PINNED
                yield Citation(sid, ver, rel, lineno, state)


@dataclasses.dataclass
class Census:
    pinned: int = 0
    unpinned: int = 0
    version_mismatch: int = 0
    unpinned_ids: dict[str, int] = dataclasses.field(default_factory=dict)
    mismatches: list[Citation] = dataclasses.field(default_factory=list)

    def note(self, c: Citation) -> None:
        if c.state == PINNED:
            self.pinned += 1
        elif c.state == UNPINNED:
            self.unpinned += 1
            self.unpinned_ids[c.id] = self.unpinned_ids.get(c.id, 0) + 1
        else:
            self.version_mismatch += 1
            self.mismatches.append(c)

    @property
    def total(self) -> int:
        return self.pinned + self.unpinned + self.version_mismatch

    def render(self) -> str:
        lines = [
            f"citations found : {self.total}",
            f"  PINNED         : {self.pinned}  (audited at the version cited)",
            f"  UNPINNED       : {self.unpinned}  over {len(self.unpinned_ids)} unaudited ids",
            f"  VERSION_MISMATCH: {self.version_mismatch}",
        ]
        if self.unpinned_ids:
            lines.append("")
            lines.append("unaudited ids, by how often the tree leans on them:")
            for sid, count in sorted(self.unpinned_ids.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"  {sid}  x{count}")
        if self.mismatches:
            lines.append("")
            lines.append("cited at a version the ledger does not pin:")
            for c in self.mismatches:
                lines.append(f"  {c.id}{c.version or ''}  {c.path}:{c.line}")
        return "\n".join(lines)


def census(root: Path, ledger: dict[str, Any]) -> Census:
    out = Census()
    for c in iter_citations(root, ledger):
        out.note(c)
    return out


# ---------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true", help="structural invariants; nonzero on error")
    ap.add_argument("--census", action="store_true", help="classify every arXiv citation in the tree")
    ap.add_argument("--strict", action="store_true", help="with --census: nonzero if anything is unpinned")
    args = ap.parse_args(argv)

    if not (args.check or args.census):
        ap.print_help()
        return 2

    ledger = load(args.ledger)
    errors = validate(ledger)
    if errors:
        print(f"LEDGER INVALID: {len(errors)} structural error(s)", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    if args.census:
        print(census(args.root, ledger).render())
        print()
        print(
            f"pinned sources: {len(ledger.get('sources', []))}"
            f" + {len(ledger.get('audited_elsewhere', []))} compact"
            f" | drift records: {len(ledger.get('drift', []))}"
            f" | unsourced claims recorded: {len(ledger.get('claims_with_no_primary_source', []))}"
        )

    if args.check and errors:
        return 1
    if args.strict and args.census:
        c = census(args.root, ledger)
        if c.unpinned or c.version_mismatch:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
