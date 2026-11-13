#!/usr/bin/env python3
"""A real repair is a whole file. A lesson is one statement. This finds the statement.

THE DEFECT, MEASURED ON REAL THIRD-PARTY CODE
---------------------------------------------
`canonical/tests/fixtures/historical_repair_projects_v1` pins four real historical repairs from
boltons and more-itertools by sha256 and git blob sha, each with its exact unchanged upstream test
body. Teaching the production path the way its own curriculum worker teaches it --
`crystallize_code_fix(before_snippet=target.read_text(), after_snippet=<whole after.py>)` -- gives,
for the real boltons `bytes2human` boundary fix:

    holes=13   pattern_tokens=99   replacement_tokens=99
    derive_operator_swap -> None      derive_swap_family -> []
    error_class GENERIC               state ACTIVE
    candidates proposed on 8 real sources -> 0, 0, 0, 0, 0, 0, 0, 0

The rule is stored, marked ACTIVE, and fires nowhere. `derive_operator_swap` is right to refuse: it
returns a swap only when the two token streams are identical except at exactly ONE operator
position, and two 1317-line files that differ in a docstring and an operator differ in more than one
place. `error_class` is not the cause -- GENERIC and BOUNDARY produce identical tokens.

So one real experience, taught the way the tree teaches it, currently buys a permanent no-op. That
is the measured answer to "give it the smartest actions once and it learns them permanently".

WHAT LOCALIZATION BUYS, MEASURED
--------------------------------
Localizing the same real repair to the smallest statement that covers the change yields

    if abs_bytes <= next_size:  ->  if abs_bytes < next_size:
    swap {'from': '<=', 'to': '<'}   family [('<=','<'), ('>=','>'), ('>','>=')]

and that lesson, applied to a DIFFERENT real module, contains that module's real upstream fix at
rank 2 of 4 candidates and the fix passes its own 3 upstream tests. See
`canonical/tools/real_repair_localization_probe_v1.py`, which executes all of it.

On the two more-itertools cases -- real bugs whose fix ADDS a zero-guard rather than changing an
operator -- localization returns NO_OPERATOR_LESSON. That is the correct answer and the reason this
module refuses rather than approximates: a missing guard is a different lesson, and emitting an
operator rule for it would be a rule that fires 32 times and repairs nothing.

WHAT THIS DOES NOT DO
---------------------
It does not repair, teach, store or accept anything. It returns a snippet pair and a swap, or a
named refusal. It does not modify `crystallize_code_fix`: teaching a localized pair while verifying
a whole file would break that function's downstream reproduction checks
(`verify_rule_on_mutated_twin`, `iter_crystallized_code_rule_candidates`), which assume the rule
reproduces `after_snippet` from `before_snippet`. Making those region-relative is the named next
step, not something to half-apply here.
It does not claim the localized lesson is the RIGHT lesson. It claims the change is a single
operator difference at a located statement, which `derive_operator_swap` checks token by token.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_LESSON_LOCALIZATION_V1"

LOCALIZED = "LOCALIZED__ONE_OPERATOR_LESSON"
SEVERAL = "SEVERAL_OPERATOR_LESSONS__NOT_ONE_LESSON"
NO_LESSON = "NO_OPERATOR_LESSON__NO_REGION_IS_A_SINGLE_OPERATOR_DIFFERENCE"
NO_CHANGE = "NO_CHANGED_REGION__THE_TWO_SOURCES_ARE_IDENTICAL"
UNPARSEABLE = "UNPARSEABLE__A_SOURCE_DID_NOT_PARSE"
NO_LANGUAGE = "NO_LOCALIZER_FOR_LANGUAGE"

#: The most regions of one file pair this will examine. A real repair is local; a pair that differs
#: in a hundred places is a rewrite, and calling one of its hunks "the lesson" would be a guess.
MAX_REGIONS = 40


class LessonLocalizationError(RuntimeError):
    """A named refusal. Never approximate a lesson."""


@dataclass(frozen=True)
class LocalizedLesson:
    """One candidate lesson: the smallest statement pair whose only difference is one operator."""
    before_statement: str
    after_statement: str
    swap: Mapping[str, str]
    family: Sequence[Mapping[str, str]]
    before_lines: tuple[int, int]
    after_lines: tuple[int, int]
    rule: Mapping[str, Any] = field(default=None, repr=False)  # type: ignore[assignment]


@dataclass(frozen=True)
class Localization:
    schema: str
    status: str
    reason: str
    regions_examined: int
    regions_with_a_statement_pair: int
    lessons: tuple[LocalizedLesson, ...]
    chosen: LocalizedLesson | None
    language: str

    @property
    def localized(self) -> bool:
        return self.status == LOCALIZED and self.chosen is not None


# --------------------------------------------------------------------------- the pieces
def changed_regions(before: str, after: str) -> list[tuple[str, int, int, int, int]]:
    """Line-level diff regions that are not `equal`, as (tag, i1, i2, j1, j2)."""
    matcher = difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False)
    return [op for op in matcher.get_opcodes() if op[0] != "equal"]


def enclosing_statement(source: str, lines: Sequence[int]) -> tuple[str, int, int] | None:
    """The smallest AST statement covering every line in `lines`, as (text, first, last).

    A statement, not a function: the real boltons fix sits in a function whose docstring ALSO
    changed, so the enclosing function carries two differences and `derive_operator_swap` refuses it.
    Statement granularity is what makes one real repair into one lesson.
    """
    wanted = set(int(x) for x in lines)
    if not wanted:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best: tuple[int, int, ast.stmt] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        lo = node.lineno
        hi = getattr(node, "end_lineno", node.lineno)
        if wanted and all(lo <= ln <= hi for ln in wanted):
            if best is None or (hi - lo) < (best[1] - best[0]):
                best = (lo, hi, node)
    if best is None:
        return None
    text = ast.get_source_segment(source, best[2])
    if text is None:
        return None
    return text, best[0], best[1]


def localize_operator_lesson(before: str, after: str, *, language: str = "python",
                             error_class: str = "BOUNDARY",
                             max_regions: int = MAX_REGIONS) -> Localization:
    """Find the one statement whose only change is one operator, or refuse by name."""
    if language.lower() != "python":
        # The localizer is an AST walker. Guessing at another language's statement boundaries would
        # produce a lesson located nowhere, which is worse than refusing.
        return Localization(SCHEMA, NO_LANGUAGE, f"{NO_LANGUAGE}:{language}", 0, 0, (), None, language)
    try:
        ast.parse(before)
        ast.parse(after)
    except SyntaxError as exc:
        return Localization(SCHEMA, UNPARSEABLE, f"{UNPARSEABLE}:{exc.msg}", 0, 0, (), None, language)

    regions = changed_regions(before, after)
    if not regions:
        return Localization(SCHEMA, NO_CHANGE, NO_CHANGE, 0, 0, (), None, language)
    regions = regions[:max(0, int(max_regions))]

    from canonical.swe_kernel import operator_generalization_v1 as gen
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule

    lessons: list[LocalizedLesson] = []
    with_pair = 0
    for _tag, i1, i2, j1, j2 in regions:
        b_lines = range(i1 + 1, max(i2, i1 + 1) + 1)
        a_lines = range(j1 + 1, max(j2, j1 + 1) + 1)
        sb = enclosing_statement(before, b_lines)
        sa = enclosing_statement(after, a_lines)
        if sb is None or sa is None or sb[0] == sa[0]:
            continue
        with_pair += 1
        rule = anti_unify_code_rule(sb[0], sa[0], language=language, error_class=error_class)
        if rule is None:
            continue
        swap = gen.derive_operator_swap(rule)
        if not swap:
            continue
        lessons.append(LocalizedLesson(before_statement=sb[0], after_statement=sa[0], swap=swap,
                                       family=tuple(gen.derive_swap_family(rule)),
                                       before_lines=(sb[1], sb[2]), after_lines=(sa[1], sa[2]),
                                       rule=rule))

    if not lessons:
        reason = NO_LESSON if with_pair else f"{NO_LESSON}__NO_REGION_HAD_A_STATEMENT_PAIR_IN_BOTH"
        return Localization(SCHEMA, NO_LESSON, reason, len(regions), with_pair, (), None, language)
    if len(lessons) > 1:
        # Several regions each look like an operator lesson. Picking one would be a guess about which
        # change the repair was about, and a wrong guess becomes a rule that fires everywhere.
        return Localization(SCHEMA, SEVERAL, SEVERAL, len(regions), with_pair, tuple(lessons), None,
                            language)
    return Localization(SCHEMA, LOCALIZED, LOCALIZED, len(regions), with_pair, tuple(lessons),
                        lessons[0], language)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", required=True, help="path to the pre-repair source")
    ap.add_argument("--after", required=True, help="path to the post-repair source")
    ap.add_argument("--language", default="python")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    before = pathlib.Path(args.before).read_text(encoding="utf-8", errors="replace")
    after = pathlib.Path(args.after).read_text(encoding="utf-8", errors="replace")
    out = localize_operator_lesson(before, after, language=args.language)
    if args.json:
        print(json.dumps({
            "schema": out.schema, "status": out.status, "reason": out.reason,
            "language": out.language, "regions_examined": out.regions_examined,
            "regions_with_a_statement_pair": out.regions_with_a_statement_pair,
            "lessons": [{"before_statement": l.before_statement, "after_statement": l.after_statement,
                         "swap": dict(l.swap), "family": [dict(s) for s in l.family],
                         "before_lines": list(l.before_lines), "after_lines": list(l.after_lines)}
                        for l in out.lessons],
        }, indent=1, sort_keys=True))
        return 0
    print(f"lesson localization: {args.before} -> {args.after}\n")
    print(f"  status                     {out.status}")
    print(f"  regions examined           {out.regions_examined}")
    print(f"  regions with a stmt pair   {out.regions_with_a_statement_pair}")
    print(f"  operator lessons found     {len(out.lessons)}")
    for les in out.lessons:
        print(f"    {les.swap}  lines {les.before_lines} -> {les.after_lines}")
        print(f"      before: {les.before_statement.strip().splitlines()[0]}")
        print(f"      after : {les.after_statement.strip().splitlines()[0]}")
        print(f"      family: {[(s['from'], s['to']) for s in les.family]}")
    return 0 if out.localized else 1


if __name__ == "__main__":
    raise SystemExit(main())
