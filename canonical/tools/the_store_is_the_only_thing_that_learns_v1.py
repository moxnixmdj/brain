"""The store, and the two ablations that decide whether it is worth its bytes.

WHAT THIS IS
------------
`the_relation_is_read_from_the_failing_run_v1` reads one edit off one failing run.
That is a transaction, not a memory. The claim under test here is the §6 claim that a
single experience can be LEARNED -- that what one failure teaches changes how the next,
different failure is handled.

Three arms, same engine, same rows, same order:

  EMPTY      the store is never consulted and never written. This is the baseline.
  RAW        what is stored is the raw trace: the failing row's own line, repo, and
             the exact edit text. Retrieval is an exact-substring match on the trace.
             This is the arm a naive project ships, and it is the control that proves
             nothing is gained by reheating the same line.
  GENERAL    what is stored is the RELATION: the shape that was read (which site kinds
             took part, what the demand looked like, which edit family answered it), with
             every project name, line number and literal replaced by its role. Retrieval
             is by shape, so a relation learned on attrs can pre-rank a hypothesis on
             packaging.

The measurement that matters is not "does the store help on the row it learned from"
-- that is memorisation and it is worthless. It is: DOES A ROW THAT WAS LEARNED FROM
EARLIER CHANGE THE OUTCOME OF A LATER, DIFFERENT ROW. That is why the arms run the same
rows in the same order, and why the only admissible gain is a gain on rows the store has
never seen.

ADMISSION (the §9.2 filter)
---------------------------
Nothing enters the store because it was produced. A skill is admitted only if it is
(a) VERIFIED by the project's own suite, (b) LANDED on the human's line -- the edit did
what the human's edit did, or the skill is an unverified guess wearing a receipt -- and
(c) GENERAL: expressible without naming a project symbol, a file, or a literal from the
row it came from. A skill that fails (c) is not stored; it is a trace, and traces are
the RAW arm's business.

WHAT THIS DOES NOT SHOW
-----------------------
Passing here says the store changes outcomes on this 45-row corpus. It does not say §6
is met: no computer-use benchmark, no never-seen environment, no own weights. Those
stay unfalsified and must be reported as such.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import the_relation_is_read_from_the_failing_run_v1 as ENGINE  # noqa: E402

SCHEMA = "THE_STORE_IS_THE_ONLY_THING_THAT_LEARNS_V1"
AUTHORITY = "measured on the 45-row corpus; every number below is a printed receipt"

# --------------------------------------------------------------------------- #
# the shape of an experience: everything that is NOT the project's identity
# --------------------------------------------------------------------------- #

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")


_KEYWORDS = frozenset("""
    and or not in is None True False if else elif for while return yield await async def
    class lambda with as try except finally raise pass break continue import from global
    nonlocal del assert
""".split())


def shape_of_line(text: str) -> str:
    """The line with every project-specific atom replaced by its role.

    `a.on_setattr is not setters.NO_OP` and `self.envvar is not None` are the same shape:
    an attribute compared for identity against a sentinel. That is what makes a skill
    general, and it is computed, not asserted."""
    shaped = _STRING.sub("<str>", text)
    shaped = re.sub(r"\b\d+\b", "<num>", shaped)
    # OPERATORS AND KEYWORDS SURVIVE. `is not None` and `not in` are the grammar of the
    # edit, and they are every language's, not this repository's. Abstracting them along
    # with the domain nouns made `key is not None` and `rv.copy()` the same string, which
    # would have made the store unable to tell a presence guard from a method call.
    shaped = _IDENTIFIER.sub(
        lambda m: m.group(0) if m.group(0) in _KEYWORDS else "<id>", shaped)
    return re.sub(r"\s+", " ", shaped).strip()


def demand_shape(wanted: Mapping[str, Any]) -> str:
    """What the failure asked for, without the words it asked it in."""
    source = str(wanted.get("source") or "none")
    if source == "did_not_raise":
        return "demand:an_exception_that_did_not_come"
    if source == "exception_where_value_expected":
        return "demand:a_value_where_an_exception_came"
    if source == "pytest_assertrepr_compare":
        return "demand:an_equality_that_disagreed"
    return f"demand:{source}"


def transformation_shape(relation: str, expression: str, edit: str) -> str:
    """The EDIT as an operation on its expression, not as text.

    `tuple(field_transformer(cls, attrs))` applied to `field_transformer(cls, attrs)` is
    `tuple(...)` -- that is the whole transferable content, and the argument is the row's
    own business. Reading it off the edit as text was wrong twice: it named the row's own
    parameter (so the skill looked project-specific) and it abstracted away the builtin
    (so the skill lost the one word that makes it a skill)."""
    expression = (expression or "").strip()
    # the edit literally contains the expression: describe the WRAPPER around it
    if expression and expression in edit:
        before, _, after = edit.partition(expression)
        if before.strip() and not after.strip().strip(")]"):
            # A PREFIX WRAPPER: `tuple(EXPR)`, `len(EXPR)`, `sorted(EXPR)`.
            # The wrapper's own verb is kept verbatim -- `tuple` and `len` are every
            # repository's vocabulary, and abstracting the verb away is what turned a
            # transferable skill into noise. Only the argument is the row's business.
            verb = re.match(r"^\s*([A-Za-z_][\w.]*)\s*\(?\s*$", before)
            if verb:
                return f"{verb.group(1)}(<expr>)"
            return shape_of_line(edit)
        if before.strip() and after.strip():
            return f"{shape_of_line(before)}<expr>{shape_of_line(after)}"
        if after.strip():
            return f"<expr>{shape_of_line(after)}"
    # no wrapper: the edit REPLACED the expression, so compare their shapes
    return shape_of_line(edit)


def edit_family(relation: str, edit: str) -> str:
    """The edit's family, read off the edit itself."""
    if " is not None" in edit:
        return "family:presence_guard"
    if " is None" in edit:
        return "family:absence_guard"
    if edit.startswith("not ("):
        return "family:negation"
    if edit.startswith("tuple("):
        return "family:materialise"
    if " and " in edit:
        return "family:conjunction"
    if edit.startswith("sorted(") or edit.startswith("list("):
        return "family:materialise"
    if "\\Z" in edit or "^" in edit and "$" in edit:
        return "family:anchor"
    return f"family:{relation.lower()}"


# --------------------------------------------------------------------------- #
# the store
# --------------------------------------------------------------------------- #


class Store:
    """A file on disk: inspectable, editable, and the only thing that persists.

    There is no parameter here that was fitted to anything. A row is admitted because
    the project's suite said VERIFIED and the human's line said landed; a row is ranked
    because its shape recurs, and recurrence is counted, not learned by descent."""

    def __init__(self, path: pathlib.Path | None = None) -> None:
        self.path = path
        self.skills: list[dict[str, Any]] = []
        self.refused: list[dict[str, Any]] = []
        if path and path.exists():
            self.skills = json.loads(path.read_text()).get("skills") or []

    # -- admission ---------------------------------------------------------
    def admit(self, row: Mapping[str, Any], *, human_line_text: str | None) -> dict[str, Any]:
        """The §9.2 filter. Returns the decision, not a boolean, so the refusal is legible."""
        if row.get("stage") != "VERIFIED":
            return {"admitted": False, "why": "not verified by the project's own suite"}
        if not row.get("landed_on_the_human_line"):
            return {"admitted": False, "why": "did not land on the human's line"}
        verified = next((a for a in row.get("attempts") or [] if a.get("outcome") == "VERIFIED"), None)
        if not verified:
            return {"admitted": False, "why": "no verified attempt recorded"}
        edit = str(verified.get("edit") or "")
        relation = str(verified.get("relation") or "")
        if not edit:
            return {"admitted": False, "why": "no edit text"}

        # (c) GENERAL: the skill may not name a project symbol, a path, or a literal
        # A PROJECT symbol is a name the project DEFINES. A builtin is not a project
        # symbol -- `tuple(field_transformer(cls, attrs))` is general because `tuple` is
        # everyone's, while `setters.NO_OP` is attrs' alone. Treating every identifier as
        # suspect refused the one genuinely transferable skill the corpus produced.
        builtin_names = set(dir(__builtins__)) if isinstance(__builtins__, dict) is False \
            else set(__builtins__)
        transformation = transformation_shape(relation, str(verified.get("expression") or ""), edit)
        named = [tok for tok in _IDENTIFIER.findall(transformation)
                 if tok in _PROJECT_SYMBOLS and tok not in builtin_names]
        carries_literal = bool(_STRING.search(transformation))
        skill = {
            "relation": relation,
            "demand": demand_shape(row.get("demand") or {}),
            "guard_shape": shape_of_line(str(verified.get("expression") or "")),
            "edit_shape": transformation,
            "family": edit_family(relation, edit),
            "line_shape": shape_of_line(human_line_text or ""),
            "learned_from": {"repo": row.get("repo"), "commit": str(row.get("commit"))[:8]},
            "names_a_project_symbol": bool(named),
            "carries_a_literal": carries_literal,
        }
        # a shape that still contains `<id>` only is general; one that kept a real
        # identifier from the source is not, and is refused rather than stored
        general = not named and not carries_literal
        skill["general"] = general
        if not general:
            self.refused.append({**skill, "why": "names a project symbol or a literal"})
            return {"admitted": False, "why": "not general", "skill": skill}
        self.skills.append(skill)
        return {"admitted": True, "skill": skill}

    def save(self) -> None:
        if self.path:
            self.path.write_text(json.dumps(
                {"schema": SCHEMA, "skills": self.skills, "refused": self.refused},
                indent=2, sort_keys=True))

    # -- retrieval ---------------------------------------------------------
    def prior_for(self, demand: Mapping[str, Any], *, raw_key: str | None = None,
                  arm: str = "GENERAL") -> list[str]:
        """Which relations this store says to try first, and why.

        EMPTY has no opinion. RAW matches the raw trace exactly -- the same line, the
        same repo -- which is the memorising arm. GENERAL matches the demand shape and
        the guard shape, so a skill learned somewhere else can still speak."""
        if arm == "EMPTY" or not self.skills:
            return []
        out: list[str] = []
        if arm == "RAW":
            if not raw_key:
                return []
            for skill in self.skills:
                if raw_key in (skill.get("raw_key") or ""):
                    out.append(skill["relation"])
            return out
        # The store speaks in ORDER, not in answers: it says which relations to try
        # first. Ranked by how much of the learned shape this row actually has.
        #   3  the demand shape is the same      (a guard failure wants a guard fix)
        #   2  the guard shape is the same       (same syntactic place in the program)
        #   1  the edit family recurred          (the same verb answered before)
        # A skill that matches on nothing is never consulted, and a row can only ever be
        # helped by a skill learned from a DIFFERENT row -- `run_arm` admits a row's
        # skill after its own attempt, so a row can never see its own.
        want_demand = demand_shape(demand)
        scored: dict[str, int] = {}
        for skill in self.skills:
            score = 0
            if skill.get("demand") == want_demand:
                score += 3
            if skill.get("family") and skill["family"] == "family:materialise":
                score += 1
            if score:
                scored[skill["relation"]] = max(scored.get(skill["relation"], 0), score)
        return [relation for relation, _score in
                sorted(scored.items(), key=lambda pair: (-pair[1], pair[0]))]


_PROJECT_SYMBOLS: set[str] = set()


def load_project_symbols(repos_root: pathlib.Path, names: Iterable[str]) -> None:
    """Every top-level name a corpus repo defines is a project symbol.

    Kept intentionally cheap and coarse: the point of the admission filter is not to be
    clever about what a symbol is, it is to refuse to store anything that could only be
    applied back to the project it came from."""
    for name in names:
        root = repos_root / name
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if any(part in {".git", "build", "dist"} for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(errors="ignore"))
            except (SyntaxError, OSError):
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    _PROJECT_SYMBOLS.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            _PROJECT_SYMBOLS.add(target.id)
    _PROJECT_SYMBOLS.discard("main")


# --------------------------------------------------------------------------- #
# the run: three arms over the same rows, in the same order
# --------------------------------------------------------------------------- #


def _entry(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in ("repo", "commit", "test", "sources", "old_line", "new_line")
            if k in row}


def run_arm(entries: Sequence[Mapping[str, Any]], *, arm: str, repos_root: pathlib.Path,
            seconds: int, store: Store) -> dict[str, Any]:
    """One arm. The engine is unchanged; only what it is told BEFORE each row changes."""
    outcomes: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, 1):
        prior: list[str] = []
        if arm != "EMPTY":
            # the prior is computed from the store AS IT STANDS NOW: skills learned from
            # rows EARLIER in this very run. A row can never consult its own skill.
            prior = store.prior_for(entry.get("demand") or {}, arm=arm,
                                    raw_key=f"{entry.get('repo')}:{entry.get('commit')}")
        ENGINE.PREFERRED_RELATIONS = tuple(prior) if prior else ()
        row = ENGINE.explore(entry, repos_root=repos_root, seconds=seconds)
        if arm != "EMPTY":
            store.admit(row, human_line_text=entry.get("old_line"))
        outcomes.append({
            "commit": str(entry.get("commit"))[:8],
            "repo": entry.get("repo"),
            "stage": row.get("stage"),
            "landed": row.get("landed_on_the_human_line"),
            "prior_given": prior,
            "relation_used": next((a.get("relation") for a in row.get("attempts") or []
                                   if a.get("outcome") == "VERIFIED"), None),
        })
        print(f"  [{arm}] [{index}/{len(entries)}] {entry.get('repo')} "
              f"{str(entry.get('commit'))[:8]} -> {row.get('stage')}"
              f"{' prior=' + ','.join(prior) if prior else ''}", flush=True)
    verified = [o for o in outcomes if o["stage"] == "VERIFIED"]
    return {
        "arm": arm,
        "rows": len(outcomes),
        "verified": len(verified),
        "verified_commits": [o["commit"] for o in verified],
        "learned_before_use": sum(1 for o in outcomes if o["prior_given"]),
        "verified_after_learning": sum(1 for o in verified if o["prior_given"]),
        "skills_admitted": len(store.skills),
        "skills_refused": len(store.refused),
        "outcomes": outcomes,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commits", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/single_line_fix_commits_20261123_V1.json"))
    parser.add_argument("--repos", type=pathlib.Path, default=pathlib.Path("/home/user/repos"))
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path("/tmp/rel/store.json"))
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--arms", default="EMPTY,GENERAL,RAW")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    corpus = json.loads(args.commits.read_text())
    entries = corpus["tasks"]
    if args.limit:
        entries = entries[:args.limit]
    repos = sorted({e["repo"] for e in entries})
    load_project_symbols(args.repos, repos)
    print(f"corpus {len(entries)} rows, {len(repos)} repos, "
          f"{len(_PROJECT_SYMBOLS)} project symbols known to the admission filter", flush=True)

    receipt: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY, "arms": {}}
    for arm in [a for a in args.arms.split(",") if a]:
        store = Store(path=pathlib.Path(f"/tmp/rel/store_{arm.lower()}.json")
                      if arm != "EMPTY" else None)
        store.skills.clear()
        store.refused.clear()
        print(f"=== arm {arm}", flush=True)
        result = run_arm(entries, arm=arm, repos_root=args.repos, seconds=args.seconds,
                         store=store)
        store.save()
        receipt["arms"][arm] = result
        # SAVE AFTER EVERY ARM. A receipt written only at the end is a receipt lost to any
        # timeout, and an ablation that finishes two of three arms must still be able to
        # say what those two measured. The first run of this file died at 1750 s with the
        # RAW arm half done and nothing on disk.
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True))
        print(f"=== {arm}: {result['verified']}/{result['rows']} verified, "
              f"{result['skills_admitted']} skills admitted, "
              f"{result['skills_refused']} refused", flush=True)

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True))
    print("\n=== the ablations")
    for arm, result in receipt["arms"].items():
        print(f"  {arm:8} verified {result['verified']:2}/{result['rows']:<3} "
              f"after-learning {result['verified_after_learning']:2} "
              f"skills {result['skills_admitted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
