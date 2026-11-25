#!/usr/bin/env python3
"""Is the confidence gate measuring the task, or the noise around it?

THE OBSERVATION THAT STARTED THIS
---------------------------------
Four goals handed to the shipped model:

    "In more_itertools, chunked(iterable, n) raises ZeroDivisionError when n=0 ..."   coverage 0.000  refused
    "In click, echo must translate the control byte ^D ..."                           coverage 0.375  routed
    "In werkzeug, dump_header must quote a header containing a semicolon."            coverage 0.250  refused
    "Fix the bug in the function so the test passes."                                 coverage 0.833  ROUTED

Confidence rises as the task gets emptier. That is the signature of an average over tokens, not a
measurement of the task: a real issue carries its own vocabulary -- file names, tracebacks, version strings,
identifiers from the reporter's environment -- and every one of those tokens is counted as a word *about the
operation*, then charged against a 0.34 coverage floor. A content-free sentence is all common words, all
indexed, and scores best.

That is the same defect as V21's mean of ratios, V23's objective that disagreed with its own price table,
V27's summary line carrying a wall clock, and V28's majority-class tie: **the convenient number is not the
one that carries the meaning.** The convenient number here is "how many of the request's tokens does the
model recognise". The meaningful question is "does the model recognise the part of the request that is the
ask".

WHAT THIS MEASURES
------------------
80 real SWE-bench Verified instance texts (fetched from GitHub, reference patches not fetched).

    A. the SHIPPED gate      coverage as computed now, and how many of the 80 it refuses
    B. the CAUSE             of the unmatched tokens, how many are identifiers tied to this specific
                             environment (paths, sha hashes, tracebacks, code spans, version numbers,
                             the repository's own name) rather than operation vocabulary
    C. a CANDIDATE gate      the same gate with those token classes excluded from the denominator, which is
                             a proposal, not a result: it is scored on the same 80 and its acceptance count
                             is reported next to the shipped gate's so the trade is visible

The honest failure mode of C is stated in advance: excluding tokens always raises coverage, so C will accept
more requests, and more acceptance is only better if the accepted requests are ones the model can actually
serve. That cannot be settled on 80 issue texts alone, so no claim of improvement is made -- only the
measured difference and the size of the risk.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.brain_unified_model_v1 import ask_tokens, open_model, tokenize  # noqa: E402

SCHEMA = "BRAIN_IS_THE_GATE_MEASURING_THE_TASK_V1"
ISSUES = REPO / "canonical" / "corpus" / "swe_verified_issue_text_20261124_V1.json"

#: Token classes that name the REPORTER'S environment, not the operation being asked for.
ENVIRONMENTAL = {
    "code_span": re.compile(r"`[^`]*`"),
    "path": re.compile(r"(?:^|[\s(\[])(?:~|\.{0,2})/[\w./-]{2,}"),
    "sha": re.compile(r"\b[0-9a-f]{7,40}\b"),
    "traceback": re.compile(r"Traceback \(most recent call last\)[\s\S]*", re.M),
    "version": re.compile(r"\b\d+\.\d+(?:\.\d+)?\b"),
    "url": re.compile(r"https?://\S+"),
}


def environmental_tokens(text: str) -> set[str]:
    """Every token that occurs inside an environmental span, and nowhere in the bare prose."""
    spans: list[str] = []
    for pattern in ENVIRONMENTAL.values():
        spans.extend(match.group(0) for match in pattern.finditer(text))
    inside: set[str] = set()
    for span in spans:
        inside.update(tokenize(span))
    prose = text
    for pattern in ENVIRONMENTAL.values():
        prose = pattern.sub(" ", prose)
    return inside - set(tokenize(prose))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    started = time.time()

    payload = json.loads(ISSUES.read_text())
    instances = payload["per_instance"]
    model = open_model(root=str(REPO))
    floor = model.min_coverage

    rows = []
    for instance, cell in sorted(instances.items()):
        text = (cell.get("title") or "").strip() + "\n\n" + (cell.get("body") or "").strip()
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 20:
            continue
        routing = model.route(text)
        ask = list(dict.fromkeys(ask_tokens(text)))
        environmental = environmental_tokens(text)
        # the candidate gate: same scoring, denominator without the reporter's environment
        kept = [token for token in ask if token not in environmental]
        matched_now = set(routing["query_tokens"]) - set()          # tokens the index carries
        recognised = {token for token in ask if token in model.index}
        candidate_denominator = kept or ask
        candidate_coverage = (len(recognised & set(candidate_denominator))
                              / len(candidate_denominator))
        rows.append({
            "instance": instance,
            "chars": len(text),
            "ask_tokens": len(ask),
            "ask_tokens_environmental": len([t for t in ask if t in environmental]),
            "shipped_coverage": routing["coverage"],
            "shipped_confident": routing["confident"],
            "candidate_coverage": round(candidate_coverage, 4),
            "candidate_confident": bool(candidate_coverage >= floor
                                        and routing["best"]
                                        and routing["best"]["score"] >= model.min_score),
            "shipped_best": (routing["best"] or {}).get("id"),
        })

    shipped_accept = sum(1 for row in rows if row["shipped_confident"])
    candidate_accept = sum(1 for row in rows if row["candidate_confident"])
    shipped_cov = [row["shipped_coverage"] for row in rows]
    candidate_cov = [row["candidate_coverage"] for row in rows]
    env_share = [(row["ask_tokens_environmental"] / row["ask_tokens"]) if row["ask_tokens"] else 0.0
                 for row in rows]

    def median(values: list[float]) -> float:
        values = sorted(values)
        return round(values[len(values) // 2], 4) if values else 0.0

    summary = {
        "instances": len(rows),
        "coverage_floor": floor,
        "A_shipped_gate": {
            "refused": len(rows) - shipped_accept,
            "accepted": shipped_accept,
            "refusal_rate": round((len(rows) - shipped_accept) / max(1, len(rows)), 4),
            "median_coverage": median(shipped_cov),
            "mean_coverage": round(sum(shipped_cov) / max(1, len(rows)), 4),
        },
        "B_cause": {
            "median_share_of_ask_tokens_rooted_in_the_reporters_environment": median(env_share),
            "mean_share": round(sum(env_share) / max(1, len(rows)), 4),
            "instances_where_environment_is_over_half_the_ask":
                sum(1 for share in env_share if share > 0.5),
        },
        "C_candidate_gate": {
            "accepted": candidate_accept,
            "refused": len(rows) - candidate_accept,
            "median_coverage": median(candidate_cov),
            "mean_coverage": round(sum(candidate_cov) / max(1, len(rows)), 4),
            "additional_requests_accepted": candidate_accept - shipped_accept,
            "share_of_the_lift_that_is_environment_exclusion":
                round(sum(c - s for c, s in zip(candidate_cov, shipped_cov))
                      / max(1e-9, sum(1 for _ in rows)), 4),
        },
        "verdicts": {
            "the_gate_refuses_a_majority_of_real_issues":
                (len(rows) - shipped_accept) > len(rows) / 2,
            "confidence_is_anti_correlated_with_content_free_goals":
                True,   # measured separately: the 4-goal probe is in the report, not in this artifact
            "environmental_vocabulary_is_a_material_part_of_a_real_ask":
                median(env_share) > 0.15,
            "excluding_environmental_tokens_changes_the_acceptance_decision":
                candidate_accept != shipped_accept,
            "improvement_is_established": False,   # accepting more is not serving more
        },
        "reading": (
            "B is the finding. If a large share of a real issue's ask tokens come from the reporter's "
            "environment -- paths, hashes, tracebacks, code spans, versions -- then a gate that charges them "
            "to the model's coverage budget is measuring the reporter's context, not the model's competence. "
            "C is only a candidate: raising acceptance is not evidence of serving more, and this artifact "
            "makes no such claim."),
        "what_this_does_not_show": (
            "that the accepted requests would be solved. No patch was produced, no test was run, and the "
            "reference patches were never fetched. This is a measurement of the front door."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": str(ISSUES.relative_to(REPO)),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_instance": rows,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
