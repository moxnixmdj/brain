#!/usr/bin/env python3
"""Exact synthetic witness-or-UNSAT audit for the frozen active legacy-15 surface.

Extends V2 with the corrected slot-level proof target. Every synthetic contract
must be discharged by either:
- a deterministic visible-prompt witness that passes every exact frozen checker,
  or
- an explicit checker-semantics UNSAT certificate.

Three adversarial profiles are generator-admitted slot collisions. They ensure an
impossible tuple is counted as a proved UNSAT contract, not as a solver defect.
No terminal rows, terminal prompts, terminal scores, hidden runtime kwargs, or
learned model outputs are exposed to the runtime solver.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_end2end_exact_synthetic_audit_v2 as v2
from canonical.runtime import livebench_legacy15_witness_or_unsat_v1 as solver

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_END2END_WITNESS_OR_UNSAT_AUDIT_V3"

ADVERSARIAL_PROFILES = (
    {
        "name": "SLOT_UNSAT_NTH_FORBIDDEN",
        "existence": ["cedar", "orbit", "meadow", "quartz", "signal"],
        "forbidden": ["rock", "apple", "market", "glass", "shoe"],
        "paragraphs": 3,
        "words": (180, "at least"),
        "sentences": (6, "at least"),
        "nth": (3, 2, "rock"),
        "postscript": "P.S.",
        "bullets": 2,
        "sections": ("Section", 2),
        "end": "Any other questions?",
    },
    {
        "name": "SLOT_UNSAT_END_FORBIDDEN",
        "existence": ["cedar", "orbit", "meadow", "quartz", "signal"],
        "forbidden": ["other", "apple", "market", "glass", "shoe"],
        "paragraphs": 3,
        "words": (180, "at least"),
        "sentences": (6, "at least"),
        "nth": (3, 2, "river"),
        "postscript": "P.S.",
        "bullets": 2,
        "sections": ("Section", 2),
        "end": "Any other questions?",
    },
    {
        "name": "SLOT_UNSAT_SECTION_FORBIDDEN",
        "existence": ["cedar", "orbit", "meadow", "quartz", "signal"],
        "forbidden": ["section", "apple", "market", "glass", "shoe"],
        "paragraphs": 3,
        "words": (180, "at least"),
        "sentences": (6, "at least"),
        "nth": (3, 2, "river"),
        "postscript": "P.S.",
        "bullets": 2,
        "sections": ("Section", 3),
        "end": "Any other questions?",
    },
)
PROFILES = tuple(v2.PROFILES) + ADVERSARIAL_PROFILES


def _records_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r["instruction_id"]): dict(r.get("kwargs") or {}) for r in records}


def verify_unsat_certificate(records: list[dict[str, Any]], reasons: list[str]) -> bool:
    """Recheck each admitted UNSAT theorem against the oracle-side exact slots.

    This does not search response space. It validates the contradiction's
    premises against the same hidden synthetic oracle records used to invoke the
    exact frozen checkers. The runtime solver never receives these records.
    """
    if not reasons:
        return False
    by = _records_by_id(records)
    for reason in reasons:
        if reason == "NTH_FIRST_WORD_IS_FORBIDDEN_WORD":
            nth = by.get("length_constraints:nth_paragraph_first_word")
            forb = by.get("keywords:forbidden_words")
            if not nth or not forb:
                return False
            first = str(nth.get("first_word") or "")
            words = [str(x) for x in forb.get("forbidden_words") or []]
            if not first or not any(first.casefold() == w.casefold() for w in words):
                return False
            continue

        section_prefix = "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:"
        if reason.startswith(section_prefix):
            sections = by.get("detectable_format:multiple_sections")
            forb = by.get("keywords:forbidden_words")
            if not sections or not forb:
                return False
            hit = reason[len(section_prefix):]
            splitter = str(sections.get("section_spliter") or "")
            words = [str(x) for x in forb.get("forbidden_words") or []]
            if splitter.casefold() != hit.casefold():
                return False
            if not any(w.casefold() == hit.casefold() for w in words):
                return False
            continue

        prefix = "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:"
        if reason.startswith(prefix):
            end = by.get("startend:end_checker")
            forb = by.get("keywords:forbidden_words")
            if not end or not forb:
                return False
            hit = reason[len(prefix):]
            phrase = str(end.get("end_phrase") or "")
            words = [str(x) for x in forb.get("forbidden_words") or []]
            if not any(w.casefold() == hit.casefold() for w in words):
                return False
            if re.search(r"\b" + re.escape(hit) + r"\b", phrase, flags=re.IGNORECASE) is None:
                return False
            continue

        return False
    return True


def audit(livebench_root: Path, max_failures: int) -> dict[str, Any]:
    legacy = livebench_root / "livebench/if_runner/instruction_following_eval"
    assert v2.git_blob_sha(legacy / "instructions_registry.py") == v2.FROZEN_REGISTRY_BLOB
    assert v2.git_blob_sha(legacy / "instructions.py") == v2.FROZEN_INSTRUCTIONS_BLOB

    import sys
    sys.path.insert(0, str(livebench_root / "livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry

    sets = archetypes.enumerate_compatible_sets()
    assert len(sets) == v2.EXPECTED_SET_COUNT

    total = 0
    witness_candidate = 0
    exact_witness_pass = 0
    certified_unsat = 0
    runtime_block = 0
    exact_fail = 0
    invalid_unsat_certificate = 0
    by_archetype = defaultdict(Counter)
    by_profile = defaultdict(Counter)
    failures: list[dict[str, Any]] = []
    runtime_errors = Counter()
    exact_failed_ids = Counter()
    unsat_reasons = Counter()

    for ids in sets:
        arch = archetypes.archetype(ids)
        for profile in PROFILES:
            for reverse in (False, True):
                total += 1
                prompt, records = v2.render_prompt(ids, profile, registry, reverse)
                out = solver.solve(prompt)
                bucket_a = by_archetype[arch]
                bucket_p = by_profile[profile["name"]]

                if out.get("status") == "PROVED_UNSAT_VISIBLE_CONTRACT":
                    reasons = list(out.get("hard_unsat_reasons") or [])
                    if verify_unsat_certificate(records, reasons):
                        certified_unsat += 1
                        for reason in reasons:
                            unsat_reasons[reason] += 1
                        bucket_a["certified_unsat"] += 1
                        bucket_p["certified_unsat"] += 1
                    else:
                        invalid_unsat_certificate += 1
                        bucket_a["invalid_unsat_certificate"] += 1
                        bucket_p["invalid_unsat_certificate"] += 1
                        if len(failures) < max_failures:
                            failures.append({
                                "ids": list(ids),
                                "archetype": arch,
                                "profile": profile["name"],
                                "order": "reverse" if reverse else "forward",
                                "stage": "unsat_certificate",
                                "reasons": reasons,
                            })
                    continue

                if out.get("status") != "PASS_CANDIDATE_WITNESS":
                    runtime_block += 1
                    reason = str(out.get("error") or out.get("status"))
                    runtime_errors[reason] += 1
                    bucket_a["runtime_block"] += 1
                    bucket_p["runtime_block"] += 1
                    if len(failures) < max_failures:
                        failures.append({
                            "ids": list(ids),
                            "archetype": arch,
                            "profile": profile["name"],
                            "order": "reverse" if reverse else "forward",
                            "stage": "runtime",
                            "reason": reason,
                        })
                    continue

                witness_candidate += 1
                ok, failed = v2.exact_check(str(out["response"]), records, registry)
                if ok:
                    exact_witness_pass += 1
                    bucket_a["exact_witness_pass"] += 1
                    bucket_p["exact_witness_pass"] += 1
                else:
                    exact_fail += 1
                    bucket_a["exact_fail"] += 1
                    bucket_p["exact_fail"] += 1
                    for iid in failed:
                        exact_failed_ids[iid] += 1
                    if len(failures) < max_failures:
                        failures.append({
                            "ids": list(ids),
                            "archetype": arch,
                            "profile": profile["name"],
                            "order": "reverse" if reverse else "forward",
                            "stage": "exact_checker",
                            "failed_ids": failed,
                        })

    discharged = exact_witness_pass + certified_unsat
    all_discharged = discharged == total
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_SYNTHETIC_CONTRACTS_WITNESS_OR_CERTIFIED_UNSAT"
            if all_discharged
            else "FAIL_CLOSED__REPAIR_LEDGER_EMITTED"
        ),
        "bindings": {
            "livebench_commit": v2.FROZEN_LIVEBENCH_COMMIT,
            "registry_blob": v2.FROZEN_REGISTRY_BLOB,
            "instructions_blob": v2.FROZEN_INSTRUCTIONS_BLOB,
            "solver_schema": solver.SCHEMA,
            "archetype_schema": archetypes.SCHEMA,
        },
        "scope": {
            "active_identity_count": len(archetypes.ACTIVE_IDS),
            "compatible_identity_sets": len(sets),
            "parameter_profiles": len(PROFILES),
            "adversarial_profiles": len(ADVERSARIAL_PROFILES),
            "orders_per_profile": 2,
            "synthetic_cases": total,
            "terminal_rows_read": 0,
            "terminal_prompts_read": 0,
            "terminal_scores_read": 0,
        },
        "results": {
            "witness_candidate": witness_candidate,
            "exact_witness_pass": exact_witness_pass,
            "certified_unsat": certified_unsat,
            "runtime_block": runtime_block,
            "exact_fail": exact_fail,
            "invalid_unsat_certificate": invalid_unsat_certificate,
            "discharged": discharged,
            "discharged_fraction": discharged / total,
        },
        "by_archetype": {k: dict(v) for k, v in sorted(by_archetype.items())},
        "by_profile": {k: dict(v) for k, v in sorted(by_profile.items())},
        "runtime_errors": dict(runtime_errors.most_common()),
        "exact_failed_instruction_ids": dict(exact_failed_ids.most_common()),
        "certified_unsat_reasons": dict(unsat_reasons.most_common()),
        "failure_samples": failures,
        "hard_nonclaims": [
            "SYNTHETIC_PUBLIC_GENERATOR_ADMITTED_PROFILE_EVIDENCE_ONLY",
            "SEVEN_PARAMETER_PROFILES_DO_NOT_BY_THEMSELVES_PROVE_THE_ENTIRE_SLOT_DOMAIN",
            "NO_TERMINAL_CASE_CONTENT_READ",
            "NO_ACTIVE_TERMINAL_SCORE_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-failures", type=int, default=250)
    ns = ap.parse_args()
    result = audit(Path(ns.livebench_root).resolve(), ns.max_failures)
    Path(ns.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], **result["results"]}, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
