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


# V2 semantic completeness hardening.
# Byte coverage alone is not semantic completeness: one physical line can encode
# multiple independent obligations. The functions below require two independent
# decompositions to agree on semantic span boundaries/classification/fingerprint,
# conservatively lower-bound the number of obligations in risky text, and bind
# every operative consensus unit bidirectionally to requirements.

MODAL_RE = re.compile(
    r"\b(must(?:\s+not)?|shall(?:\s+not)?|should(?:\s+not)?|required|requires|"
    r"need(?:s)?\s+to|do\s+not|never|always)\b",
    re.I,
)
ACTION_RE = re.compile(
    r"\b(ensure|produce|write|return|output|use|create|delete|reject|accept|"
    r"validate|verify|preserve|include|exclude|emit|raise|fail|read|store|save)\b",
    re.I,
)
CONSTRAINT_RE = re.compile(
    r"\b(only|exactly|at\s+least|at\s+most|minimum|maximum|without|before|after|"
    r"unless|except|each|every|all|any)\b",
    re.I,
)


def semantic_unit_id(atom_id: str, start: int, end: int) -> str:
    raw = f"{atom_id}\0{start}\0{end}".encode("utf-8")
    return "SEM-" + hashlib.sha256(raw).hexdigest()[:20]


def obligation_lower_bound(text: str) -> int:
    """Conservative deterministic lower bound on distinct obligations.

    This is not a semantic parser. It exists to make obvious compound obligations
    impossible to collapse into one unchecked semantic unit.
    """
    risky = bool(NORMATIVE_RE.search(text) or HIGH_RISK_RE.search(text))
    if not risky:
        return 0
    modal = len(list(MODAL_RE.finditer(text)))
    action = len(list(ACTION_RE.finditer(text)))
    constraint = len(list(CONSTRAINT_RE.finditer(text)))
    return max(1, modal, action, constraint)


def _non_ws_positions(text: str) -> set[int]:
    return {i for i, ch in enumerate(text) if not ch.isspace()}


def validate_semantic_consensus(
    *,
    source_text: str,
    atoms: Sequence[SourceAtom],
    extractor_units: Mapping[str, Sequence[Mapping[str, Any]]],
    requirements: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Prove dual-extractor span consensus and semantic-to-requirement closure.

    Each extractor independently decomposes risky source atoms into local spans.
    Consensus requires identical span boundaries, semantic class, and a canonical
    semantic fingerprint. Any disagreement is a blocking specification hole.
    """
    errors: list[str] = []
    try:
        if reconstruct_source(atoms) != source_text:
            errors.append("SOURCE_RECONSTRUCTION_MISMATCH")
    except ValueError as exc:
        return [str(exc)]

    by_atom = {a.atom_id: a for a in atoms}
    if len(by_atom) != len(atoms):
        errors.append("SOURCE_ATOM_ID_DUPLICATE")

    if not isinstance(extractor_units, Mapping) or len(extractor_units) < 2:
        return sorted(set(errors + ["INDEPENDENT_SEMANTIC_EXTRACTORS_LT_2"]))

    normalized: dict[str, dict[str, list[tuple[int, int, str, str, str]]]] = {}
    for extractor_id, units in extractor_units.items():
        if not isinstance(extractor_id, str) or not extractor_id.strip():
            errors.append("SEMANTIC_EXTRACTOR_ID_INVALID")
            continue
        if not isinstance(units, Sequence) or isinstance(units, (str, bytes)):
            errors.append(f"SEMANTIC_UNITS_INVALID:{extractor_id}")
            continue
        per_atom: dict[str, list[tuple[int, int, str, str, str]]] = {}
        seen_ids: set[str] = set()
        for i, unit in enumerate(units):
            if not isinstance(unit, Mapping):
                errors.append(f"SEMANTIC_UNIT_INVALID:{extractor_id}:{i}")
                continue
            aid = unit.get("atom_id")
            atom = by_atom.get(aid)
            if atom is None:
                errors.append(f"SEMANTIC_UNIT_UNKNOWN_ATOM:{extractor_id}:{aid}")
                continue
            start = unit.get("start")
            end = unit.get("end")
            if (
                not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or start < 0 or end <= start or end > len(atom.text)
            ):
                errors.append(f"SEMANTIC_SPAN_INVALID:{extractor_id}:{aid}:{i}")
                continue
            sid = semantic_unit_id(aid, start, end)
            if sid in seen_ids:
                errors.append(f"SEMANTIC_UNIT_DUPLICATE:{extractor_id}:{sid}")
                continue
            seen_ids.add(sid)
            span_text = atom.text[start:end]
            expected_hash = hashlib.sha256(span_text.encode("utf-8")).hexdigest()
            if unit.get("text_sha256") != expected_hash:
                errors.append(f"SEMANTIC_SPAN_HASH_MISMATCH:{extractor_id}:{sid}")
            kind = unit.get("kind")
            if kind not in DISPOSITIONS:
                errors.append(f"SEMANTIC_KIND_INVALID:{extractor_id}:{sid}:{kind}")
                continue
            fingerprint = unit.get("semantic_fingerprint")
            if not isinstance(fingerprint, str) or not fingerprint.strip():
                errors.append(f"SEMANTIC_FINGERPRINT_MISSING:{extractor_id}:{sid}")
                fingerprint = ""
            rationale = unit.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(f"SEMANTIC_RATIONALE_MISSING:{extractor_id}:{sid}")
            if kind == "INFORMATIVE" and (atom.normative or atom.high_risk):
                errors.append(f"RISKY_SEMANTIC_UNIT_MARKED_INFORMATIVE:{extractor_id}:{sid}")
            per_atom.setdefault(aid, []).append((start, end, str(kind), fingerprint, sid))

        for aid, rows in per_atom.items():
            rows.sort()
            previous_end = -1
            for start, end, *_ in rows:
                if start < previous_end:
                    errors.append(f"SEMANTIC_SPAN_OVERLAP:{extractor_id}:{aid}")
                previous_end = max(previous_end, end)

        # Every risky atom must be fully covered (ignoring whitespace) by each
        # extractor and decomposed into at least the conservative obligation bound.
        for aid, atom in by_atom.items():
            if not (atom.normative or atom.high_risk):
                continue
            rows = per_atom.get(aid, [])
            if len(rows) < obligation_lower_bound(atom.text):
                errors.append(
                    f"SEMANTIC_OBLIGATION_UNDERSEGMENTED:{extractor_id}:{aid}:"
                    f"{len(rows)}<{obligation_lower_bound(atom.text)}"
                )
            covered: set[int] = set()
            for start, end, *_ in rows:
                covered.update(range(start, end))
            missing = _non_ws_positions(atom.text) - covered
            if missing:
                errors.append(f"SEMANTIC_RISKY_TEXT_UNCOVERED:{extractor_id}:{aid}")
        normalized[extractor_id] = per_atom

    valid_extractors = sorted(normalized)
    if len(valid_extractors) < 2:
        errors.append("INDEPENDENT_SEMANTIC_EXTRACTORS_LT_2")
        return sorted(set(errors))

    # Exact consensus is intentionally strict. A boundary/class/fingerprint
    # disagreement means the source semantics are not frozen and must not drive
    # implementation or evidence spend.
    reference = normalized[valid_extractors[0]]
    consensus_units: dict[str, tuple[str, int, int, str, str]] = {}
    for aid, atom in by_atom.items():
        if not (atom.normative or atom.high_risk):
            continue
        ref_rows = reference.get(aid, [])
        ref_sig = [(s, e, k, fp) for s, e, k, fp, _ in ref_rows]
        for extractor_id in valid_extractors[1:]:
            rows = normalized[extractor_id].get(aid, [])
            sig = [(s, e, k, fp) for s, e, k, fp, _ in rows]
            if sig != ref_sig:
                errors.append(f"SEMANTIC_EXTRACTOR_DISAGREEMENT:{aid}")
        for s, e, k, fp, sid in ref_rows:
            consensus_units[sid] = (aid, s, e, k, fp)
            if k == "AMBIGUOUS":
                errors.append(f"OPEN_SPECIFICATION_HOLE:{sid}")

    req_by_id: dict[str, Mapping[str, Any]] = {}
    unit_to_requirements: dict[str, set[str]] = {sid: set() for sid in consensus_units}
    for req in requirements:
        rid = req.get("id") if isinstance(req, Mapping) else None
        if not isinstance(rid, str) or not rid.strip():
            errors.append("REQUIREMENT_ID_MISSING")
            continue
        if rid in req_by_id:
            errors.append(f"REQUIREMENT_ID_DUPLICATE:{rid}")
            continue
        req_by_id[rid] = req
        refs = req.get("source_semantic_unit_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"REQUIREMENT_WITHOUT_SEMANTIC_UNITS:{rid}")
            continue
        for sid in refs:
            if sid not in consensus_units:
                errors.append(f"REQUIREMENT_UNKNOWN_SEMANTIC_UNIT:{rid}:{sid}")
            else:
                unit_to_requirements[sid].add(rid)

    for sid, (_, _, _, kind, _) in consensus_units.items():
        if kind in {"BEHAVIOR", "ENVIRONMENT", "RESOURCE", "SOURCE_BOUNDARY", "EVALUATION"}:
            if not unit_to_requirements.get(sid):
                errors.append(f"OPERATIVE_SEMANTIC_UNIT_WITHOUT_REQUIREMENT:{sid}")

    return sorted(set(errors))
