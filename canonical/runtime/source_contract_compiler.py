"""Lossless source-to-contract coverage compiler.

This kernel does not pretend to solve arbitrary natural-language semantics.
It proves that every byte range in an authoritative textual source is accounted
for, that normative/high-risk atoms cannot silently disappear, and that semantic
ambiguity becomes an explicit blocking hole rather than an invented requirement.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

NORMATIVE_RE = re.compile(
    r"\b(must|mustn't|must not|shall|shall not|required|requires|should|should not|"
    r"need to|needs to|only|exactly|at least|at most|never|always|do not|don't|"
    r"forbidden|prohibited|ensure|produce|write|return|output|use)\b",
    re.I,
)
HIGH_RISK_RE = re.compile(
    r"\b(any|all|every|each|future|arbitrary|different|optional|unless|except|"
    r"if|when|before|after|within|without|only|exactly|minimum|maximum)\b",
    re.I,
)
DISPOSITIONS = {
    "BEHAVIOR",
    "ENVIRONMENT",
    "RESOURCE",
    "SOURCE_BOUNDARY",
    "EVALUATION",
    "INFORMATIVE",
    "AMBIGUOUS",
}


@dataclass(frozen=True)
class SourceAtom:
    atom_id: str
    source: str
    start: int
    end: int
    text: str
    sha256: str
    normative: bool
    high_risk: bool


def _atom_id(source: str, start: int, end: int, text: str) -> str:
    h = hashlib.sha256(
        (source + "\0" + str(start) + "\0" + str(end) + "\0" + text).encode("utf-8")
    ).hexdigest()[:20]
    return "SRC-" + h


def atomize_source(text: str, source: str) -> list[SourceAtom]:
    """Partition source losslessly into non-overlapping atoms.

    Atoms are line-preserving chunks ending at newline boundaries. Semantic
    splitting is downstream, while byte coverage is exact and mechanically
    provable.
    """
    if not isinstance(text, str) or not text:
        raise ValueError("source text must be non-empty")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source name must be non-empty")

    atoms: list[SourceAtom] = []
    start = 0
    for m in re.finditer(r".*?(?:\n|$)", text, re.S):
        chunk = m.group(0)
        if not chunk:
            continue
        end = start + len(chunk)
        atoms.append(
            SourceAtom(
                atom_id=_atom_id(source, start, end, chunk),
                source=source,
                start=start,
                end=end,
                text=chunk,
                sha256=hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                normative=bool(NORMATIVE_RE.search(chunk)),
                high_risk=bool(HIGH_RISK_RE.search(chunk)),
            )
        )
        start = end
        if start >= len(text):
            break
    if start != len(text):
        raise AssertionError("atomizer did not cover source exactly")
    return atoms


def reconstruct_source(atoms: Sequence[SourceAtom]) -> str:
    if not atoms:
        return ""
    ordered = sorted(atoms, key=lambda a: a.start)
    cursor = 0
    out: list[str] = []
    for a in ordered:
        if a.start != cursor:
            raise ValueError(f"SOURCE_ATOM_GAP_OR_OVERLAP:{cursor}:{a.start}")
        if a.end != a.start + len(a.text):
            raise ValueError(f"SOURCE_ATOM_RANGE_MISMATCH:{a.atom_id}")
        if hashlib.sha256(a.text.encode("utf-8")).hexdigest() != a.sha256:
            raise ValueError(f"SOURCE_ATOM_HASH_MISMATCH:{a.atom_id}")
        out.append(a.text)
        cursor = a.end
    return "".join(out)


def validate_contract_coverage(
    *,
    source_text: str,
    atoms: Sequence[SourceAtom],
    dispositions: Sequence[Mapping[str, Any]],
    requirements: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Validate lossless source coverage and bidirectional traceability."""
    errors: list[str] = []
    try:
        reconstructed = reconstruct_source(atoms)
    except ValueError as exc:
        return [str(exc)]
    if reconstructed != source_text:
        errors.append("SOURCE_RECONSTRUCTION_MISMATCH")

    by_atom = {a.atom_id: a for a in atoms}
    if len(by_atom) != len(atoms):
        errors.append("SOURCE_ATOM_ID_DUPLICATE")

    disp_by_atom: dict[str, Mapping[str, Any]] = {}
    for d in dispositions:
        aid = d.get("atom_id")
        if aid not in by_atom:
            errors.append(f"UNKNOWN_DISPOSITION_ATOM:{aid}")
            continue
        if aid in disp_by_atom:
            errors.append(f"DUPLICATE_ATOM_DISPOSITION:{aid}")
            continue
        kind = d.get("kind")
        if kind not in DISPOSITIONS:
            errors.append(f"INVALID_DISPOSITION_KIND:{aid}:{kind}")
        disp_by_atom[aid] = d

    req_by_id: dict[str, Mapping[str, Any]] = {}
    for r in requirements:
        rid = r.get("id")
        if not isinstance(rid, str) or not rid.strip():
            errors.append("REQUIREMENT_ID_MISSING")
            continue
        if rid in req_by_id:
            errors.append(f"REQUIREMENT_ID_DUPLICATE:{rid}")
            continue
        req_by_id[rid] = r

    cited_atoms: set[str] = set()
    for rid, r in req_by_id.items():
        refs = r.get("source_atom_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"REQUIREMENT_WITHOUT_SOURCE_ATOMS:{rid}")
            continue
        for aid in refs:
            if aid not in by_atom:
                errors.append(f"REQUIREMENT_UNKNOWN_SOURCE_ATOM:{rid}:{aid}")
            else:
                cited_atoms.add(aid)

    for aid, atom in by_atom.items():
        d = disp_by_atom.get(aid)
        if d is None:
            errors.append(f"UNACCOUNTED_SOURCE_ATOM:{aid}")
            continue
        kind = d.get("kind")
        rationale = d.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"DISPOSITION_RATIONALE_MISSING:{aid}")

        req_ids = d.get("requirement_ids", [])
        if req_ids is None:
            req_ids = []
        if not isinstance(req_ids, list):
            errors.append(f"DISPOSITION_REQUIREMENT_IDS_INVALID:{aid}")
            req_ids = []
        for rid in req_ids:
            if rid not in req_by_id:
                errors.append(f"DISPOSITION_UNKNOWN_REQUIREMENT:{aid}:{rid}")
            else:
                refs = req_by_id[rid].get("source_atom_ids") or []
                if aid not in refs:
                    errors.append(f"TRACEABILITY_NOT_BIDIRECTIONAL:{aid}:{rid}")

        if kind in {"BEHAVIOR", "ENVIRONMENT", "RESOURCE", "SOURCE_BOUNDARY", "EVALUATION"}:
            if not req_ids:
                errors.append(f"OPERATIVE_ATOM_WITHOUT_REQUIREMENT:{aid}")

        if kind == "INFORMATIVE" and (atom.normative or atom.high_risk):
            errors.append(f"NORMATIVE_OR_HIGH_RISK_ATOM_MARKED_INFORMATIVE:{aid}")

        if kind == "AMBIGUOUS":
            interpretations = d.get("interpretations")
            discriminator = d.get("discriminator")
            if not isinstance(interpretations, list) or len(interpretations) < 2:
                errors.append(f"AMBIGUITY_WITHOUT_ALTERNATIVES:{aid}")
            if not isinstance(discriminator, str) or not discriminator.strip():
                errors.append(f"AMBIGUITY_WITHOUT_DISCRIMINATOR:{aid}")
            errors.append(f"OPEN_SPECIFICATION_HOLE:{aid}")

        if atom.normative and kind not in {
            "BEHAVIOR", "ENVIRONMENT", "RESOURCE", "SOURCE_BOUNDARY", "EVALUATION", "AMBIGUOUS"
        }:
            errors.append(f"NORMATIVE_ATOM_NOT_OPERATIVE:{aid}")

    for aid in cited_atoms:
        d = disp_by_atom.get(aid)
        if d and d.get("kind") == "INFORMATIVE":
            errors.append(f"REQUIREMENT_CITES_INFORMATIVE_ATOM:{aid}")

    return sorted(set(errors))


def admission_ready(errors: Iterable[str]) -> bool:
    return not any(True for _ in errors)
