"""Refuse a plan before it is implemented, on the grounds that it cannot be measured.

Why this exists
---------------
This repository has run ~6,850 pull requests and carries 264 top-level documents, and the binding
constraint on its stated goal has not moved. The cause is not effort. It is that its plans were
admitted on the strength of what they would *produce* — causal models, concepts, skills, lessons,
operators, documents, tests — rather than on the strength of what they would *decide*.

An artefact count is the most expensive kind of metric, because it always goes up. A plan whose
success criterion is a count cannot fail, and a plan that cannot fail cannot teach the person
paying for it anything.

So a plan is admitted only if it names, before any work:

  * a capability metric with a ratio/rate/score unit, not an artefact count;
  * a held-out distribution that development never touched;
  * a cache-only arm AND a random/default arm (both are mandatory; a cache can pass any test that
    does not include one);
  * a stopping rule;
  * a falsifier — a sentence that could come back TRUE and would prove the phase wrong.

This is the same discipline `learning_claim_adjudicator_v1.py` applies to *results*, applied one
step earlier, to *intentions*. It is cheaper there.

What this is not
----------------
Not a judge of ambition, novelty, or taste. A plan can pass this gate and still be worthless. The
gate has exactly one job: stop the plans that are guaranteed to be uninformative.

Authority: NONE. Offline. No model, no network, no writes.
Run: python3 canonical/tools/plan_admission_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "canonical" / "research_sources" / "PROPOSED_PLAN_20261113_V1.json"

SCHEMA = "proposed_plan_v1"

# An artefact count. Each of these nouns denominates a thing the system *made*, not a thing the
# system can *do*. Counting them is how twelve false positives were born in this tree.
ARTEFACT_NOUNS = (
    "causal model", "causal models",
    "concept", "concepts",
    "skill", "skills",
    "lesson", "lessons",
    "capability registered", "capabilities registered",
    "operator", "operators",
    "document", "documents",
    "pull request", "pull requests",
    "test count", "tests pass", "tests passed",
    "organ", "organs",
)

# A capability metric has a denominator. These markers are the mechanical form of that.
RATIO_MARKERS = ("%", "rate", "coverage", "precision", "recall", "score", "ratio", "per ", "fraction")

# A task family is not an action. These words name an activity a person does over hours.
FAMILY_WORDS = (
    "debugging", "refactor", "refactoring", "profiling", "architecture design",
    "test generation", "security analysis", "api integration", "interaction",
    "administration", "analysis", "creative",
)

CODES = {
    "ACTIVITY_METRIC": "the success criterion counts artefacts the system produced, not capability",
    "NO_RATIO": "the success criterion has no ratio/rate/score unit, so it cannot be compared to a control",
    "NO_HELD_OUT": "no held-out distribution is named, so every number would be a fit",
    "NO_CACHE_CONTROL": "no cache-only arm, so learning cannot be separated from recall",
    "NO_RANDOM_CONTROL": "no random/default arm, so any number can be beaten by chance",
    "NO_STOPPING_RULE": "no stopping rule, so the phase has no end",
    "NO_FALSIFIER": "no falsifier, so the phase cannot return NO",
    "ACTION_IS_A_TASK_FAMILY": "a named 'action' is a task family, not an action",
    "DOMAIN_SEQUENCING": "phases are ordered by substrate, not by verifier availability",
}

HARD = frozenset({
    "ACTIVITY_METRIC", "NO_RATIO", "NO_HELD_OUT", "NO_CACHE_CONTROL",
    "NO_RANDOM_CONTROL", "NO_STOPPING_RULE", "NO_FALSIFIER", "ACTION_IS_A_TASK_FAMILY",
})


@dataclass
class Finding:
    code: str
    phase: str
    detail: str

    def render(self) -> str:
        return f"[{self.code}] {self.phase}: {self.detail}"


@dataclass
class Verdict:
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.code in HARD]

    @property
    def admitted(self) -> bool:
        return not self.blocking

    def render(self) -> str:
        if not self.findings:
            return "ADMITTED (no findings)"
        lines = [f"REJECTED ({len(self.blocking)} blocking)" if not self.admitted else "ADMITTED with notes"]
        for f in self.findings:
            lines.append("  " + f.render())
        return "\n".join(lines)


_COUNT_RE = re.compile(
    r"\b\d[\d,]*\s+(?:[a-z_]+[\s]+){0,2}(?:" + "|".join(re.escape(n) for n in sorted(ARTEFACT_NOUNS, key=len, reverse=True)) + r")\b"
)


def counted_artefacts(criterion: str) -> list[str]:
    """Artefact nouns bound to a number, e.g. '40 causal models' but not 'the operators we wrote'."""
    return [m.group(0) for m in _COUNT_RE.finditer(criterion)]


def _low(text: Any) -> str:
    return str(text or "").lower()


def check_phase(phase: dict[str, Any]) -> list[Finding]:
    name = str(phase.get("name") or "unnamed phase")
    out: list[Finding] = []

    criterion = _low(phase.get("success_criterion"))
    has_ratio = any(m in criterion for m in RATIO_MARKERS)
    hit = [n for n in ARTEFACT_NOUNS if n in criterion]
    # Mentioning an artefact is not counting it: "coverage on repos never used to design the
    # operators" is a capability metric that happens to name the thing built. A count is a digit
    # bound to the noun, or a criterion that is nothing but artifacts and has no denominator.
    counted = counted_artefacts(criterion)
    if hit and (counted or not has_ratio):
        what = sorted(set(counted)) if counted else sorted(set(hit))
        out.append(Finding(
            "ACTIVITY_METRIC", name,
            f"counts {what} — an artefact count rises whether or not capability does",
        ))
    if criterion and not has_ratio:
        out.append(Finding(
            "NO_RATIO", name,
            "no rate/score/coverage unit, so there is nothing to compare against a control arm",
        ))

    if not str(phase.get("held_out") or "").strip():
        out.append(Finding("NO_HELD_OUT", name, "empty"))

    controls = [str(c).lower() for c in (phase.get("controls") or [])]
    joined = " | ".join(controls)
    if not any("cache" in c for c in controls):
        out.append(Finding("NO_CACHE_CONTROL", name, "no arm that answers from a store of seen cases"))
    if not any(("random" in c) or ("default" in c) or ("coin" in c) for c in controls):
        out.append(Finding("NO_RANDOM_CONTROL", name, "no arm that answers without learning"))
    assert isinstance(joined, str)

    if not str(phase.get("stopping_rule") or "").strip():
        out.append(Finding("NO_STOPPING_RULE", name, "empty"))
    if not str(phase.get("falsifier") or "").strip():
        out.append(Finding("NO_FALSIFIER", name, "empty"))

    for action in phase.get("actions") or []:
        a = _low(action)
        # A task family is an activity described by a gerund or a compound; an action is a verb on
        # an object that resolves in one step (edit_file, run_tests).
        if any(w in a for w in FAMILY_WORDS):
            out.append(Finding(
                "ACTION_IS_A_TASK_FAMILY", name,
                f"{action!r} is an activity measured in hours, not an action that resolves in one step",
            ))
    return out


def check_plan(plan: dict[str, Any]) -> Verdict:
    verdict = Verdict()
    if plan.get("schema") != SCHEMA:
        verdict.findings.append(Finding(
            "NO_FALSIFIER", "plan", f"schema is not {SCHEMA}, so the plan is not in an admissible form",
        ))
        return verdict

    phases = plan.get("phases") or []
    if not phases:
        verdict.findings.append(Finding("NO_FALSIFIER", "plan", "no phases"))
        return verdict

    for phase in phases:
        verdict.findings.extend(check_phase(phase))

    # Sequencing by substrate instead of by verifier availability. A warning, not a refusal: a
    # domain-ordered plan can still be admissible if each phase carries its own controls.
    stems = [_low(p.get("name")) for p in phases]
    verifier_words = ("verifier", "oracle", "test", "checked", "graded")
    if stems and not any(any(w in s for w in verifier_words) for s in stems):
        verdict.findings.append(Finding(
            "DOMAIN_SEQUENCING", "plan",
            "no phase is ordered or justified by how cheaply an independent verifier is available; "
            "the phases advance by substrate (code -> code edits -> adjacent -> GUI), which is not "
            "the axis that decides tractability",
        ))
    return verdict


def load(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else DEFAULT_PLAN
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", type=Path, default=None)
    args = ap.parse_args(argv)

    plan = load(args.plan)
    verdict = check_plan(plan)
    print(f"plan : {plan.get('goal', '')[:88]}")
    print(verdict.render())
    if not verdict.admitted:
        seen = []
        for f in verdict.blocking:
            if f.code not in seen:
                seen.append(f.code)
        print()
        print("what it would have to add:")
        for code in seen:
            print(f"  {code}: {CODES[code]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
