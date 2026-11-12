#!/usr/bin/env python3
"""A rule that has been taught is not a rule that has been shown to hold.

THE DEFECT THIS CLOSES
----------------------
`record_permanence_witnesses` stores how many inputs and outputs were varied:

    {"distinct_inputs": 3, "distinct_outputs": 3, "nonconstant_amplified": true}

That is a count of the demonstration. It is history: it cannot fail. A rule can carry
`nonconstant_amplified: true` while being the wrong rule, because the count says the
demonstrations differed, not that the rule still works.

`domain_of_verification_v1` already names this ("a hypothesis is a property of the
observations plus an unstated assumption") and has zero importers. This module is the
smaller, executable version of it for skills.

WHAT THIS DOES
--------------
`recheck(rule, sources)` re-RUNS the stored rule against the sources it was taught on and
returns a verdict that can be FAIL:

    PASS     every taught source, re-applied now, still produces the stored rewrite
    FAIL     a taught source no longer produces it -- the rule has gone stale, or the
             world moved under it
    ABSENT   the rule carries no teachable source, so it can never be re-checked

ABSENT is the interesting one. Five of five stored rules are ABSENT: the store records the
rule, not the text it came from, so nothing about them can be re-executed. That is exactly
the `0 of 5 carry a verification field` line in the auditability report, and this is the
mechanism that would move it.

THE SECOND MECHANISM: SELF-WITNESS
----------------------------------
Keeping the taught text (2026-11-12) fixed every lesson taught from now on, and left the
five rules the repository SHIPS untouched: their demonstrations are gone and cannot be
reconstructed honestly. Attaching a source they were never taught on would be fabricating
provenance, which is worse than the gap.

But a token rule is not only a record of a demonstration -- it is a *denotation*. Its
`pattern_tokens` name a text and its `replacement_tokens` name another, so the smallest text
the pattern denotes can be rendered, fed to the production applier, and compared with the
text the replacement denotes. `self_witness(rule)` does that, two-sided:

    PASS     the applier rewrites the rendered pattern into exactly the rendered replacement,
             AND leaves a near-miss text (one concrete token altered) alone
    FAIL     it does not rewrite it, rewrites it into something else, raises, rewrites the
             near-miss too, or names a hole in the replacement the pattern never bound
    ABSENT   no witness can be built: no pattern tokens, an unrenderable hole kind, a refuted
             rule (correctly inert, not broken), or no concrete token to anchor a negative

A self-witness PASS is WEAKER than a taught-source PASS and is never reported as one: it
shows the rule still means what it says to the engine that applies it, not that it still
fixes the bug it was learned from. What it buys is the property that was missing -- the
shipped memory can now be shown wrong, on any machine, without the demonstration.

Usage:
    python3 -m canonical.swe_kernel.skill_recheck_v1 [--db PATH] [--bundle PATH]

Authority: NONE. A PASS here means "the stored rule still reproduces the stored rewrite on
the stored source", which is transport, not correctness. It is not independent verification
and it does not raise any capability.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys

SCHEMA = "PROJECT_BRAIN_SKILL_RECHECK_V1"

PASS = "PASS"
FAIL = "FAIL"
ABSENT = "ABSENT"


def _rule_sources(rule: dict) -> list[dict]:
    """The taught (before, after) pairs a rule must still reproduce.

    Accepted shapes, in order of preference: `taught_sources` (what this module expects to
    be written), then `training_example` (a single pair). Anything else is ABSENT -- the
    safe direction, because an unrecognised source must never count as evidence.
    """
    # `crystallize_code_fix` writes them under `provenance`; accept the top level too so a
    # rule copied out of the store stays checkable wherever it is pasted.
    for holder in (rule, rule.get("provenance")):
        if not isinstance(holder, dict):
            continue
        sources = holder.get("taught_sources")
        if isinstance(sources, list) and sources:
            return [s for s in sources if isinstance(s, dict) and "before" in s]
        one = holder.get("training_example")
        if isinstance(one, dict) and "before" in one:
            return [one]
    return []


def recheck(rule: dict, *, apply=None) -> dict:
    """Re-run `rule` on its own taught sources. Can return FAIL, which is the point."""
    if apply is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            apply_crystallized_code_rule as apply,
        )
    sources = _rule_sources(rule)
    if not sources:
        return {"verdict": ABSENT, "reason": "NO_TAUGHT_SOURCE",
                "detail": "the rule stores no source text, so it cannot be re-executed"}

    checked = 0
    for index, source in enumerate(sources):
        before = str(source.get("before") or "")
        expected = source.get("after")
        try:
            produced = apply(before, rule)
        except Exception as exc:                     # a rule that raises has failed
            return {"verdict": FAIL, "reason": f"APPLY_RAISED:{type(exc).__name__}",
                    "source_index": index}
        checked += 1
        if produced is None:
            return {"verdict": FAIL, "reason": "RULE_NO_LONGER_APPLIES",
                    "source_index": index,
                    "detail": "the pattern no longer matches the text it was taught on"}
        if expected is not None and produced != str(expected):
            return {"verdict": FAIL, "reason": "REWRITE_DIFFERS_FROM_TAUGHT",
                    "source_index": index,
                    "expected_len": len(str(expected)), "produced_len": len(produced)}

    return {"verdict": PASS, "reason": None, "sources_checked": checked}


# ---------------------------------------------------------------------------
# self-witness: a rule whose demonstration is gone still denotes a rewrite
# ---------------------------------------------------------------------------

#: What a hole is filled with when the smallest text the pattern denotes is rendered.
#: One entry per hole kind the engine emits; an unknown kind is ABSENT, never guessed,
#: because a witness built from an invented filler would prove the invention, not the rule.
WITNESS_HOLE_FILL = {
    "hole_id": "w{n}",
    "hole_num": "{n}",
    "hole_str": '"s{n}"',
}

#: Substitutes used to build the near-miss text, by the kind of token being altered. Each one
#: is chosen to tokenize as a DIFFERENT kind or a different value than the pattern expects, so
#: a rule that still fires on the near-miss is over-applying.
WITNESS_NEGATIVE_SUBSTITUTE = {
    "op": ("%", "&", "|", "^", "~"),
    "kw": ("zzqwitness",),
    "ident": ("zzqwitness",),
    "num": ("9999", "8888"),
    "str": ('"zzq"', '"zzr"'),
}


def _render_tokens(tokens: list, names: dict) -> str | None:
    """Concatenate token values, filling each hole from `names` (adding fillers as needed)."""
    out: list[str] = []
    for token in tokens:
        if not isinstance(token, (list, tuple)) or len(token) != 2:
            return None
        kind, value = token
        if str(kind).startswith("hole_"):
            hole = str(value)
            if hole not in names:
                filler = WITNESS_HOLE_FILL.get(str(kind))
                if filler is None:
                    return None
                names[hole] = filler.format(n=len(names))
            out.append(names[hole])
        else:
            out.append(str(value))
    return "".join(out)


def render_witness(rule: dict) -> dict:
    """The smallest text this rule's own pattern denotes, plus a near-miss that must NOT match.

    Returns `{"ok": False, "reason": ...}` when no witness can be built. Nothing here consults
    the demonstration; a rule that lost its source is still a statement about texts, and this
    renders that statement.
    """
    pattern = rule.get("pattern_tokens")
    replacement = rule.get("replacement_tokens")
    if not isinstance(pattern, list) or not isinstance(replacement, list):
        return {"ok": False, "reason": "NO_PATTERN_TOKENS"}
    concrete = [(k, v) for k, v in pattern
                if isinstance(k, str) and not k.startswith("hole_") and k != "ws"]
    if not concrete:
        # No concrete token means no negative: any text of the right shape would match, so a
        # PASS here could not be contradicted. Refusing is the safe direction.
        return {"ok": False, "reason": "NO_CONCRETE_ANCHOR"}

    names: dict[str, str] = {}
    before = _render_tokens([tuple(t) for t in pattern], names)
    if before is None:
        kinds = sorted({str(t[0]) for t in pattern
                        if isinstance(t, (list, tuple)) and len(t) == 2
                        and str(t[0]).startswith("hole_")
                        and str(t[0]) not in WITNESS_HOLE_FILL})
        return {"ok": False, "reason": "UNRENDERABLE_HOLE_KIND:" + (kinds[0] if kinds else "?")}
    after = _render_tokens([tuple(t) for t in replacement], dict(names))
    if after is None:
        return {"ok": False, "reason": "UNRENDERABLE_HOLE_KIND_IN_REPLACEMENT"}

    unbound = [str(t[1]) for t in replacement
               if isinstance(t, (list, tuple)) and len(t) == 2
               and str(t[0]).startswith("hole_") and str(t[1]) not in names]
    if unbound:
        # A replacement hole the pattern never bound has no value: whatever the applier emits
        # for it was not specified by the lesson.
        return {"ok": False, "reason": "UNBOUND_HOLE_IN_REPLACEMENT", "hole": unbound[0]}

    # The near-miss: the same witness with one concrete token altered, so the pattern cannot
    # match it. Holes keep their fillers -- only the anchor moves.
    anchor_kind, anchor_value = concrete[0]
    taken = {str(v) for k, v in pattern if not str(k).startswith("hole_")}
    taken |= set(names.values())
    substitute = next((s for s in WITNESS_NEGATIVE_SUBSTITUTE.get(str(anchor_kind), ("zzqwitness",))
                       if s not in taken), None)
    if substitute is None:
        return {"ok": False, "reason": "NO_NEGATIVE_SUBSTITUTE"}
    negative_tokens = []
    replaced = False
    for token in pattern:
        kind, value = token
        if not replaced and kind == anchor_kind and value == anchor_value:
            negative_tokens.append((kind, substitute))
            replaced = True
        else:
            negative_tokens.append((kind, value))
    negative = _render_tokens(negative_tokens, dict(names))
    if negative is None:
        return {"ok": False, "reason": "NEGATIVE_UNRENDERABLE"}

    return {"ok": True, "before": before, "after": after, "negative": negative,
            "hole_bindings": dict(names), "anchor_altered": [str(anchor_kind), str(anchor_value),
                                                             substitute]}


def self_witness(rule: dict, *, apply=None) -> dict:
    """Re-execute a rule against the text its own pattern denotes. Can return FAIL.

    Two-sided on purpose: a check that only asks "does it fire?" is passed by an applier that
    rewrites everything, which is the exact shape of the always-pass grader this repository
    keeps finding. The near-miss arm is what makes the positive arm mean something.
    """
    if apply is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            apply_crystallized_code_rule as apply,
        )
    witness = render_witness(rule)
    if not witness.get("ok"):
        reason = witness.get("reason", "NO_WITNESS")
        if reason == "UNBOUND_HOLE_IN_REPLACEMENT":
            # Not a missing measurement: a replacement that names a hole the pattern never
            # bound declares a rewrite no text can satisfy. That is a contradiction, and a
            # contradiction is a FAIL. Every other reason really is "no witness could be built".
            return {"verdict": FAIL, "basis": "SELF_WITNESS", "reason": reason,
                    "hole": witness.get("hole")}
        return {"verdict": ABSENT, "basis": "SELF_WITNESS", "reason": reason}
    if not _rule_is_applicable(rule):
        # A refuted rule is inert BY DESIGN: the applier returns None for it. Scoring that as
        # FAIL would punish invalidation, and scoring it PASS would credit a dead lesson.
        return {"verdict": ABSENT, "basis": "SELF_WITNESS", "reason": "REFUTED_RULE_IS_INERT"}

    try:
        produced = apply(witness["before"], rule)
    except Exception as exc:                          # a rule that raises has failed
        return {"verdict": FAIL, "basis": "SELF_WITNESS",
                "reason": f"APPLY_RAISED:{type(exc).__name__}", "witness": witness["before"]}
    if produced is None:
        return {"verdict": FAIL, "basis": "SELF_WITNESS", "reason": "WITNESS_NOT_REWRITTEN",
                "witness": witness["before"], "expected": witness["after"]}
    if produced != witness["after"]:
        return {"verdict": FAIL, "basis": "SELF_WITNESS", "reason": "REWRITE_DIFFERS_FROM_DECLARED",
                "witness": witness["before"], "expected": witness["after"], "produced": produced}
    try:
        over = apply(witness["negative"], rule)
    except Exception as exc:
        return {"verdict": FAIL, "basis": "SELF_WITNESS",
                "reason": f"NEGATIVE_APPLY_RAISED:{type(exc).__name__}",
                "negative": witness["negative"]}
    if over is not None:
        return {"verdict": FAIL, "basis": "SELF_WITNESS", "reason": "OVER_APPLIES_TO_NEAR_MISS",
                "negative": witness["negative"], "produced": over}

    return {"verdict": PASS, "basis": "SELF_WITNESS", "reason": None,
            "witness": witness["before"], "produced": produced,
            "negative": witness["negative"], "hole_bindings": witness["hole_bindings"]}


def _rule_is_applicable(rule: dict) -> bool:
    """The store's own answer to 'may this rule act?', with a local fallback for stray rules."""
    try:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import rule_is_applicable
        return bool(rule_is_applicable(rule))
    except Exception:                                 # pragma: no cover - import cycle guard
        return rule.get("state") in (None, "ACTIVE")


def recheck_bundle(bundle_path: pathlib.Path | str) -> dict:
    """Measure the SHIPPED bundle, which is what a machine that never learned anything gets.

    The SQLite store is gitignored generated state; the bundle is the memory that travels. A
    lesson that can only be re-checked in the store it was written to is not re-checkable on
    the next computer, so the shipped file is measured on its own.
    """
    bundle_path = pathlib.Path(bundle_path)
    if not bundle_path.is_file():
        return {"schema": SCHEMA, "authority": "NONE", "bundle": str(bundle_path),
                "error": "BUNDLE_ABSENT", "rules": [], "counts": {}}
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"schema": SCHEMA, "authority": "NONE", "bundle": str(bundle_path),
                "error": f"BUNDLE_UNREADABLE:{type(exc).__name__}"[:160], "rules": [],
                "counts": {}}

    counts = {PASS: 0, FAIL: 0, ABSENT: 0}
    taught_counts = {PASS: 0, FAIL: 0, ABSENT: 0}
    rules_out: list[dict] = []
    entries = payload.get("rules") if isinstance(payload, dict) else None
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        rule = entry.get("rule")
        if not isinstance(rule, dict):
            counts[FAIL] += 1
            rules_out.append({"skill_id": entry.get("skill_id"), "verdict": FAIL,
                              "basis": "SELF_WITNESS", "reason": "NO_RULE_PAYLOAD"})
            continue
        outcome = self_witness(rule)
        counts[outcome["verdict"]] += 1
        taught_counts[recheck(rule)["verdict"]] += 1
        rules_out.append({"skill_id": entry.get("skill_id"),
                          "language": rule.get("language"), **outcome})

    return {"schema": SCHEMA, "authority": "NONE", "bundle": str(bundle_path),
            "rules": rules_out, "counts": counts, "taught_source_counts": taught_counts,
            "recheckable": counts[PASS] + counts[FAIL], "total": len(rules_out)}


def recheck_store(db_path: pathlib.Path | str) -> dict:
    """Every stored rule, re-checked. Reports counts, and never turns ABSENT into a pass."""
    db_path = pathlib.Path(db_path)
    if not db_path.is_file():
        return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
                "error": "DB_ABSENT", "rules": [], "counts": {}}

    rules_out: list[dict] = []
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = list(conn.execute(
                "SELECT skill_id, language, error_class, pattern_json "
                "FROM crystallized_skills ORDER BY skill_id"))
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
                "error": f"SQLITE:{exc}"[:160], "rules": [], "counts": {}}

    counts = {PASS: 0, FAIL: 0, ABSENT: 0}
    witness_counts = {PASS: 0, FAIL: 0, ABSENT: 0}
    recheckable_any = 0
    for skill_id, language, error_class, pattern_json in rows:
        try:
            rule = json.loads(pattern_json)
        except (TypeError, ValueError):
            counts[FAIL] += 1
            witness_counts[ABSENT] += 1
            rules_out.append({"skill_id": skill_id, "verdict": FAIL,
                              "reason": "PATTERN_JSON_INVALID",
                              "self_witness": {"verdict": ABSENT, "basis": "SELF_WITNESS",
                                               "reason": "PATTERN_JSON_INVALID"}})
            recheckable_any += 1
            continue
        outcome = recheck(rule)
        counts[outcome["verdict"]] += 1
        # Two mechanisms, counted separately and never merged into one number: a taught source
        # re-runs the demonstration, a self-witness re-runs the rule's own denotation. A rule
        # checkable by both is ONE checkable rule, so `recheckable` (taught only, the pinned
        # contract) and `recheckable_any` (either) stay distinguishable.
        witness = self_witness(rule)
        witness_counts[witness["verdict"]] += 1
        if outcome["verdict"] in (PASS, FAIL) or witness["verdict"] in (PASS, FAIL):
            recheckable_any += 1
        rules_out.append({"skill_id": skill_id, "language": language,
                          "error_class": error_class, **outcome, "self_witness": witness})

    return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
            "rules": rules_out, "counts": counts,
            "recheckable": counts[PASS] + counts[FAIL],
            "self_witness_counts": witness_counts,
            "self_witness_recheckable": witness_counts[PASS] + witness_counts[FAIL],
            "self_witness_only": sum(
                1 for r in rules_out
                if r.get("verdict") == ABSENT
                and (r.get("self_witness") or {}).get("verdict") in (PASS, FAIL)),
            "recheckable_any": recheckable_any,
            "total": len(rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None,
                        help="sqlite store; defaults to the live store's path")
    parser.add_argument("--bundle", default=None,
                        help="measure the SHIPPED bundle instead of the local store: the "
                             "bundle is what a machine that never learned anything receives")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.bundle is not None:
        report = recheck_bundle(args.bundle)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        elif report.get("error"):
            print(f"cannot measure: {report['error']}")
        else:
            print("self-witness: can a shipped rule be shown to still mean what it says?\n")
            print(f"  {report['total']} shipped rules  ({report['bundle']})")
            for verdict in (PASS, FAIL, ABSENT):
                print(f"    {verdict:7} {report['counts'][verdict]}")
            print(f"\n  re-checkable by self-witness: {report['recheckable']}/{report['total']}")
            print(f"  re-checkable by taught source: "
                  f"{report['taught_source_counts'][PASS] + report['taught_source_counts'][FAIL]}"
                  f"/{report['total']}")
            for rule in report["rules"]:
                if rule["verdict"] != PASS:
                    print(f"    {rule['verdict']:7} {str(rule.get('skill_id'))[:22]:24} "
                          f"{rule.get('reason')}")
        if report.get("error"):
            return 2
        return 1 if report.get("counts", {}).get(FAIL) else 0

    db = args.db
    if db is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import _default_db_path
        db = _default_db_path()

    report = recheck_store(db)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if report.get("error"):
            print(f"cannot measure: {report['error']}")
            return 2
        print("recheck: can a stored rule be shown to still hold?\n")
        print(f"  {report['total']} stored rules")
        for verdict in (PASS, FAIL, ABSENT):
            print(f"    {verdict:7} {report['counts'][verdict]}")
        print(f"\n  recheckable: {report['recheckable']}/{report['total']}")
        witness = report.get("self_witness_counts") or {}
        if witness:
            print(f"\n  self-witness (the rule's own denotation, weaker than a taught source)")
            for verdict in (PASS, FAIL, ABSENT):
                print(f"    {verdict:7} {witness.get(verdict, 0)}")
            print(f"    re-checkable by either: {report.get('recheckable_any')}/{report['total']}"
                  f"   (by self-witness alone: {report.get('self_witness_only')})")
        for rule in report["rules"]:
            if rule["verdict"] != PASS:
                why = rule.get("reason")
                witness_verdict = (rule.get("self_witness") or {}).get("verdict")
                if rule["verdict"] == ABSENT and witness_verdict in (PASS, FAIL):
                    why = f"{why} (self-witness {witness_verdict})"
                print(f"    {rule['verdict']:7} {str(rule.get('skill_id'))[:22]:24} {why}")
    # Red only on a genuine FAIL, from either mechanism. ABSENT is a missing measurement, not a
    # contradiction -- and a self-witness FAIL is a contradiction, so it must be able to gate.
    return 1 if (report.get("counts", {}).get(FAIL)
                 or (report.get("self_witness_counts") or {}).get(FAIL)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
