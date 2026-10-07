from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from canonical.runtime import m0a_raw_source_brain_candidate_v2 as candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as suite

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_M0A_RAW_SOURCE_GENERATOR_IMAGE_UNIVERSAL_VERIFIER_V1"
EXPECTED = {
    "canonical/runtime/m0a_raw_source_terminal_suite_v2.py": "63b5daacfa5623c38228d41f6a84e548890d252d",
    "canonical/runtime/m0a_raw_source_brain_candidate_v2.py": "0aac96d27068bdad379703c1b0b8a7a32cacb2e2",
    "canonical/verification/M0A_RAW_SOURCE_POST_REPAIR_PUBLIC_RUNNER_20261002_V1.json": "0eef12725a992a5f3377340ee4dcacb65e74b0cc",
    "canonical/reasoning/2026-10-02_M0A_SEMANTIC_IDENTIFIABILITY_BOUNDARY_V1.json": "a8b3ca5230e8c1e73fdc0dbe0a4c5ae2a0710a6a",
}

def blob(path: str) -> str:
    b = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def verify() -> dict:
    errors: list[str] = []
    for path, want in EXPECTED.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("MISSING:" + path)
        else:
            got = blob(path)
            if got != want:
                errors.append("DRIFT:" + path + ":" + got)

    domains = tuple(suite.DOMAINS)
    classes = tuple(suite.CASE_CLASSES)
    if len(domains) != 11 or len(set(domains)) != 11:
        errors.append("DOMAIN_IMAGE_NOT_11_UNIQUE")
    if len(classes) != 8 or len(set(classes)) != 8:
        errors.append("CLASS_IMAGE_NOT_8_UNIQUE")

    generator_src = inspect.getsource(suite.generate_case)
    required_generator_fragments = (
        "domain, subject, verb, obj, kind = DOMAINS[r.randrange(len(DOMAINS))]",
        "cls = CASE_CLASSES[ordinal % len(CASE_CLASSES)]",
        'case_id": f"M0A-{seed}-{ordinal}"',
    )
    for fragment in required_generator_fragments:
        if fragment not in generator_src:
            errors.append("GENERATOR_FORM_DRIFT:" + fragment)

    solve_src = inspect.getsource(candidate.solve)
    for forbidden in ("case_id", "ordinal", "_oracle"):
        if forbidden in solve_src:
            errors.append("CANDIDATE_DEPENDS_ON_NONPUBLIC_SELECTOR:" + forbidden)

    # For each of the eight case classes, find one real generate_case witness
    # for each of the eleven fixed domain tuples. Because the exact pinned
    # generator's semantic payload depends only on (domain tuple, case class),
    # these 88 witnesses exhaust its semantic image.
    rows = []
    if not errors:
        domain_names = {d[0] for d in domains}
        for class_index, class_name in enumerate(classes):
            found = {}
            seed = 0
            while len(found) < len(domains) and seed < 200000:
                case = suite.generate_case(seed, class_index)
                if case["case_class"] != class_name:
                    errors.append("CLASS_SELECTOR_DRIFT:" + class_name)
                    break
                if case["domain"] in domain_names and case["domain"] not in found:
                    found[case["domain"]] = case
                seed += 1
            if set(found) != domain_names:
                errors.append("DOMAIN_PAIR_NOT_REACHABLE:" + class_name)
                continue
            for domain_name in sorted(found):
                case = found[domain_name]
                public = suite.public_task(case)
                got = candidate.solve(public)
                verdict = suite.score_case(case, got)
                rows.append({
                    "domain": domain_name,
                    "class": class_name,
                    "pass": bool(verdict.get("pass")),
                    "reason": verdict.get("reason"),
                })
                if verdict.get("pass") is not True:
                    errors.append("PAIR_FAIL:" + domain_name + ":" + class_name + ":" + str(verdict.get("reason")))

    pair_keys = {(r["domain"], r["class"]) for r in rows}
    if not errors and len(rows) != 88:
        errors.append("PAIR_COUNT:" + str(len(rows)))
    if not errors and len(pair_keys) != 88:
        errors.append("PAIR_UNIQUENESS:" + str(len(pair_keys)))

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_88_PAIR_GENERATOR_IMAGE_EXHAUSTED__SELECTED_CELL_UNIVERSAL__ZERO_GLOBAL_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "domain_count": len(domains),
        "case_class_count": len(classes),
        "generator_image_pair_count": len(pair_keys),
        "pair_pass_count": sum(1 for r in rows if r["pass"]),
        "selected_cell_scope_complete": not errors and len(pair_keys) == 88,
        "whole_open_ended_semantic_scope_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
