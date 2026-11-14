#!/usr/bin/env python3
"""Which changes can the check actually see? A measured licence, per site, before a lesson is kept.

WHY THIS EXISTS
---------------
Every round of this line of work has ended at the same sentence, in slightly different words:

    one demonstration is a point; a check is a quantifier; permanence multiplies whatever the
    evidence was worth.

That is the right shape, and it has been acted on twice already. `lesson_admission_gate_v1` refuses
to persist a lesson unless it repairs a held-out program and leaves a correct one alone (13 Nov
2026). `test_entry_point_finder_v1` then corrected the measurement underneath it: the previous
round's "no check exists" was a finder bug, and the honest figure is 18 of 54 non-test files have a
reachable check. It also measured the thing that matters and did not build on it: **3 of 5 mutants
survived** on two real projects. A test that imports a module, names its classes and never notices
that its behaviour is gone is not a check. It is a check-shaped object.

So the quantity the whole loop depends on is still missing, and it is not "is there a test":

    for THIS behaviour, in THIS project, does the check notice when the behaviour is wrong?

`expect_discrimination_v1` measured that for the registry's own declared `expect` fields (it found
29 of 74 assigning a literal). Nobody measured it for a project's test suite at the granularity a
lesson lives at — the changed site. Without that number the loop has no way to know whether a
refusal means "the lesson was wrong" or "the check was blind", and those two demand opposite
responses.

WHAT THIS MEASURES, AND WHY IT IS A LICENCE AND NOT A SCORE
----------------------------------------------------------
A check licenses a change-behaviour when perturbing that site changes what the check reports. The
mechanism is mutation: generate one small, AST-verified perturbation of the source at a site, write
it in a scratch copy, run the check, restore the bytes, run the check again.

    caught    the check failed with the mutant and passed on the original  -> this behaviour is visible
    survived  the check passed with the mutant                            -> this behaviour is BLIND
    uncaught-by-baseline  the check was already red without the mutant    -> says nothing, refuse
    flaky     the original fails on a second run                          -> says nothing, refuse

The licence is per SITE and all-or-nothing: a site is licensed only when every perturbation
generated there was caught. A site where one perturbation survives is refused, and the survivor is
named, because a lesson about that site can be wrong in a way the check will bless.

WHAT THIS DOES NOT SAY -- READ BEFORE QUOTING A NUMBER
------------------------------------------------------
* It is **empirical, not a proof**. Mutation adequacy is evidence, not theorem. A licensed site is
  one where the perturbations generated here were caught; it is not a claim that no wrong change
  there could pass. The report carries `bounded_by` naming the operators used and the mutants run.
* **A refused site is not a bug in the project's tests.** It is a statement about what those tests
  were written to observe. The correct response is to run fewer lessons there, not to demand 100%.
* **A licence is not a licence to teach anything.** It says the check can SEE a change at that site.
  Whether the change is the right one is still decided by the check, on the target's own inputs.
* **Equivalent mutants are real.** `x <= 0` -> `x < 0` is behaviour-identical on inputs the function
  never sees, and some perturbations are equivalent on every input. Survivors are named as
  candidates; `NO_DISTINGUISHING_INPUT` here is bounded, never a proof of equivalence.
* Docstrings, comments and formatting survive this by construction: mutations are byte splices
  verified to change the parsed AST, never a re-printed tree.
* **A kill can be a coincidence.** A perturbation that makes the code raise is caught by any test
  that runs it, and a timeout is counted as caught because the check did register it. Both are
  recorded per mutant (`killed_by`) so a reader can weight them.

Authority: NONE. Producer-run sandbox measurement. No capability registered, no family flipped,
`truth.achieved` is untouched, no model is called, `$0`.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_ORACLE_LICENCE_V1"
AUTHORITY = "NONE"

# Verdicts of one measurement of one site.
CAUGHT = "CAUGHT"
SURVIVED = "SURVIVED"

# Licence verdicts over a set of sites.
ALL_LICENSED = "ALL_LICENSED"
PARTIAL = "PARTIAL"
NONE_LICENSED = "NONE_LICENSED"

# Refusals: the measurement could not be made, so no licence is granted for anything it covers.
REFUSED_NO_MUTANTS = "REFUSED_NO_MUTANTS"
REFUSED_FILE_NOT_LOADED = "REFUSED_CHECK_DOES_NOT_LOAD_THE_FILE"
REFUSED_BASELINE_RED = "REFUSED_BASELINE_RED"
REFUSED_FLAKY_BASELINE = "REFUSED_FLAKY_BASELINE"
REFUSED_SOURCE_MOVED = "REFUSED_SOURCE_MOVED"

# How a mutant was caught, so a reader can tell a behaviour change from a crash or a hang.
BY_FAILURE = "TEST_FAILED"
BY_ERROR = "TEST_ERRORED"
BY_TIMEOUT = "TIMED_OUT"

# --------------------------------------------------------------------------------------- operators
#
# Five families, chosen because each is a change a person reviewing the diff would have to think
# about, and because none of them can loop forever on its own:
#   ROR  relational/boundary  -- the `<=` family every one-shot lesson in this tree is about
#   AOR  arithmetic
#   LCR  boolean connective
#   RVR  scalar return replaced by None
# Bool-literal flipping (BCR) is deliberately NOT here: `while True` -> `while False` hangs, and a
# timeout costs a full budget to learn one bit.

ROR = "ROR"
AOR = "AOR"
LCR = "LCR"
RVR = "RVR"
OPERATORS: tuple[str, ...] = (ROR, AOR, LCR, RVR)

_ROR_SWAPS: dict[str, tuple[str, ...]] = {
    "<": ("<=", ">="),
    "<=": ("<", ">"),
    ">": (">=", "<="),
    ">=": (">", "<"),
    "==": ("!=",),
    "!=": ("==",),
    "in": ("not in",),
    "not in": ("in",),
    "is": ("is not",),
    "is not": ("is",),
}

_CMP_TOKENS = {(ast.Lt,): "<", (ast.LtE,): "<=", (ast.Gt,): ">", (ast.GtE,): ">=",
               (ast.Eq,): "==", (ast.NotEq,): "!=", (ast.In,): "in", (ast.NotIn,): "not in",
               (ast.Is,): "is", (ast.IsNot,): "is not"}

_ARITH_TOKENS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//"}
_ARITH_SWAPS: dict[type, tuple[str, ...]] = {
    ast.Add: ("-",),
    ast.Sub: ("+",),
    ast.Mult: ("//",),
    ast.FloorDiv: ("*",),
}

_LOGICAL_SWAPS = {"and": ("or",), "or": ("and",)}
_BINOP_TOKENS = {(ast.And,): "and", (ast.Or,): "or"}


@dataclass(frozen=True)
class Mutant:
    """One perturbation as a byte splice, plus everything needed to audit or repeat it."""

    site_id: str
    rel_path: str
    lineno: int
    operator: str
    original: str
    replacement: str
    start: int          # absolute byte offset into the file
    end: int            # absolute byte offset, exclusive
    code: str           # the whole mutated file, so a run needs no second splice
    sha256: str         # of `code`

    def row(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "rel_path": self.rel_path,
            "lineno": self.lineno,
            "operator": self.operator,
            "original": self.original,
            "replacement": self.replacement,
            "sha256": self.sha256,
        }


@dataclass
class Site:
    """A place in the source, and the perturbations available there."""

    site_id: str
    rel_path: str
    lineno: int
    column: int
    node_kind: str
    mutants: list[Mutant] = field(default_factory=list)


# ------------------------------------------------------------------------------- byte arithmetic

def _line_start_bytes(raw: bytes) -> list[int]:
    """Absolute byte offset of the start of every line, 1-based by index."""
    starts = [0, 0]
    for i, byte in enumerate(raw):
        if byte == 0x0A and i + 1 < len(raw):
            starts.append(i + 1)
    return starts


def _offset(starts: Sequence[int], lineno: int, col: int) -> int:
    """(line, utf-8 byte column) -> absolute byte offset. AST columns are byte offsets."""
    if lineno < 1 or lineno >= len(starts):
        raise IndexError(f"line {lineno} outside source")
    return starts[lineno] + col


def _span_text(raw: bytes, start: int, end: int) -> str:
    return raw[start:end].decode("utf-8", "replace")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------------ mutant generation

def _gap_token(raw: bytes, starts: Sequence[int], left_end: tuple[int, int],
               right_start: tuple[int, int]) -> tuple[int, int, str] | None:
    """The operator bytes strictly between two nodes, with surrounding whitespace trimmed off.

    Returning the trimmed span matters: splicing over the whitespace would rewrite formatting, and
    rewriting formatting is how a mutation tool produces a large diff nobody asked for. If the gap
    is not a single short token (parentheses, a call, a line break) this returns None and the site
    is not mutated at all -- silence, not a guess.
    """
    if left_end[0] != right_start[0]:
        return None
    start = _offset(starts, left_end[0], left_end[1])
    end = _offset(starts, right_start[0], right_start[1])
    if end <= start:
        return None
    segment = raw[start:end]
    left_trimmed = segment.lstrip()
    lead = len(segment) - len(left_trimmed)
    token_bytes = left_trimmed.rstrip()
    if not token_bytes or len(token_bytes) > 10:
        return None
    return start + lead, start + lead + len(token_bytes), token_bytes.decode("ascii", "replace")


def _splice_safe(raw: bytes, start: int, end: int, replacement: str) -> bytes:
    return raw[:start] + replacement.encode("utf-8") + raw[end:]


def _ast_fingerprint(tree: ast.AST) -> str:
    return hashlib.sha256(ast.dump(tree).encode("utf-8")).hexdigest()


def generate_mutants(
    source: str,
    *,
    rel_path: str = "<source>",
    operators: Sequence[str] = OPERATORS,
) -> list[Site]:
    """Every single-line, AST-verified perturbation of `source`, grouped by site.

    A candidate splice is kept only when the mutated text still parses AND its AST differs from the
    original's. That is the cheap half of the equivalence problem done exactly: a splice that does
    not change the parsed program is not a perturbation, and running it would only ever "survive"
    and manufacture a blind spot that does not exist.
    """
    raw = source.encode("utf-8")
    tree = ast.parse(source)
    starts = _line_start_bytes(raw)
    original_fp = _ast_fingerprint(tree)
    sites: dict[str, Site] = {}
    seen: set[tuple[int, int, str]] = set()

    def add(kind: str, node: ast.AST, start: int, end: int, replacement: str,
            operator: str) -> None:
        if (start, end, replacement) in seen:
            return
        mutated = _splice_safe(raw, start, end, replacement)
        try:
            mutated_tree = ast.parse(mutated.decode("utf-8"))
        except SyntaxError:
            return
        if _ast_fingerprint(mutated_tree) == original_fp:
            return                      # not a perturbation: equivalent by construction
        seen.add((start, end, replacement))
        lineno = int(getattr(node, "lineno", 0) or 0)
        column = int(getattr(node, "col_offset", 0) or 0)
        site_id = f"{rel_path}:{lineno}:{column}:{kind}"
        site = sites.setdefault(site_id, Site(site_id=site_id, rel_path=rel_path, lineno=lineno,
                                              column=column, node_kind=kind))
        code = mutated.decode("utf-8")
        site.mutants.append(Mutant(
            site_id=site_id, rel_path=rel_path, lineno=lineno, operator=operator,
            original=_span_text(raw, start, end), replacement=replacement,
            start=start, end=end, code=code, sha256=_sha(code),
        ))

    want = set(operators)
    for node in ast.walk(tree):
        if ROR in want and isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and len(node.comparators) == 1:
            token = _CMP_TOKENS.get((type(node.ops[0]),))
            if token is None or getattr(node, "end_lineno", None) is None:
                continue
            gap = _gap_token(raw, starts,
                             (int(node.left.end_lineno or 0), int(node.left.end_col_offset or 0)),
                             (int(node.comparators[0].lineno), int(node.comparators[0].col_offset)))
            if gap is None:
                continue
            start, end, found = gap
            if found != token:
                continue                # the bytes do not say what the AST says: do not guess
            for replacement in _ROR_SWAPS[token]:
                add("comparison", node, start, end, replacement, ROR)

        elif AOR in want and isinstance(node, ast.BinOp) and type(node.op) in _ARITH_SWAPS \
                and getattr(node, "end_lineno", None) is not None \
                and node.left.end_lineno == node.right.lineno:
            token = _ARITH_TOKENS[type(node.op)]
            gap = _gap_token(raw, starts,
                             (int(node.left.end_lineno or 0), int(node.left.end_col_offset or 0)),
                             (int(node.right.lineno), int(node.right.col_offset)))
            if gap is None:
                continue
            start, end, found = gap
            if found != token:
                continue
            for replacement in _ARITH_SWAPS[type(node.op)]:
                add("arithmetic", node, start, end, replacement, AOR)

        elif LCR in want and isinstance(node, ast.BoolOp) and len(node.values) >= 2 \
                and node.values[0].end_lineno == node.values[1].lineno:
            token = _BINOP_TOKENS.get((type(node.op),))
            if token is None:
                continue
            gap = _gap_token(raw, starts,
                             (int(node.values[0].end_lineno or 0),
                              int(node.values[0].end_col_offset or 0)),
                             (int(node.values[1].lineno), int(node.values[1].col_offset)))
            if gap is None:
                continue
            start, end, found = gap
            if found != token:
                continue
            for replacement in _LOGICAL_SWAPS[token]:
                add("logical", node, start, end, replacement, LCR)

        elif RVR in want and isinstance(node, ast.Return) and node.value is not None \
                and not (isinstance(node.value, ast.Constant) and node.value.value is None) \
                and node.end_lineno == node.lineno:
            start = _offset(starts, node.lineno, node.col_offset)
            end = _offset(starts, int(node.end_lineno or node.lineno),
                          int(node.end_col_offset or node.col_offset))
            if end <= start:
                continue
            add("return", node, start, end, "return None", RVR)

    return [sites[k] for k in sorted(sites, key=lambda s: (sites[s].lineno, sites[s].column, s))]


def mutants_of(sites: Iterable[Site]) -> list[Mutant]:
    return [m for site in sites for m in site.mutants]


def _expected_after(site: Site) -> str:
    return "all mutant" + ("s" if len(site.mutants) != 1 else "") + " caught"


# --------------------------------------------------------------------------------- the experiment

# A runner answers one question: with the check given `mutant.code` written in place of the file, did
# the check fail? True means caught. It must restore the original bytes itself, and it must not
# mutate the caller's tree.
Runner = Callable[[Mutant], bool | Mapping[str, Any]]


def _normalise_outcome(raw: bool | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(raw, bool):
        return {"caught": raw, "killed_by": BY_FAILURE if raw else None, "detail": None}
    caught = bool(raw.get("caught"))
    return {
        "caught": caught,
        "killed_by": (raw.get("killed_by") or (BY_FAILURE if caught else None)) if caught else None,
        "detail": raw.get("detail"),
    }


def measure(
    source: str,
    *,
    rel_path: str,
    run: Runner,
    operators: Sequence[str] = OPERATORS,
    sites_wanted: Sequence[str] | None = None,
    max_mutants_per_site: int | None = None,
    max_sites: int | None = None,
    max_mutants: int | None = None,
    baseline_ok: bool | None = True,
) -> dict[str, Any]:
    """Measure, per site, whether the check notices this source being perturbed.

    `run` is called once per mutant with the mutated file already described in the record; it is
    the caller's job to write the bytes, run the check and restore. `baseline_ok` is the caller's
    answer to "does the check pass on the source as it stands" — when it is not True the check
    cannot be read as evidence either way, and the report refuses rather than scoring zeros.
    """
    sites = generate_mutants(source, rel_path=rel_path, operators=operators)
    if sites_wanted is not None:
        wanted = set(sites_wanted)
        sites = [s for s in sites if s.site_id in wanted]
    offered = len(sites)
    if max_sites is not None and len(sites) > max_sites:
        # Deterministic, not random: the first sites in line order. A sampled licence that changes
        # between runs cannot be compared with itself, and comparing a licence over time is most of
        # its use. Callers that care about particular sites pass `sites_wanted`.
        sites = sites[:max_sites]
    rows: list[dict[str, Any]] = []
    spent = 0
    for site in sites:
        chosen = site.mutants if max_mutants_per_site is None else site.mutants[:max_mutants_per_site]
        if max_mutants is not None:
            chosen = chosen[: max(0, max_mutants - spent)]
        if not chosen:
            continue
        spent += len(chosen)
        site_rows = []
        for mutant in chosen:
            outcome = _normalise_outcome(run(mutant))
            site_rows.append({**mutant.row(), **outcome})
        licensed = all(r["caught"] for r in site_rows)
        rows.append({
            "site_id": site.site_id,
            "rel_path": site.rel_path,
            "lineno": site.lineno,
            "node_kind": site.node_kind,
            "mutants": site_rows,
            "mutants_run": len(site_rows),
            "mutants_caught": sum(1 for r in site_rows if r["caught"]),
            "licensed": licensed,
            "survivors": [r["replacement"] for r in site_rows if not r["caught"]],
        })
    report = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "rel_path": rel_path,
        "source_sha256": _sha(source),
        "operators": list(operators),
        "sites": rows,
        "sites_available": offered,
        "sites_measured": len(rows),
        "mutants_run": spent,
        "baseline_ok": baseline_ok,
        "bounded_by": {
            "mutants_per_site": max_mutants_per_site,
            "operators": list(operators),
            "note": "empirical: licensed sites are where THESE mutants were caught, not a proof",
        },
    }
    return report


def _site_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    """Accept either stored rows or bare site ids, so a hand-built report cannot silently mislead."""
    out: list[dict[str, Any]] = []
    for row in rows or ():
        out.append({"site_id": row} if isinstance(row, str) else dict(row or {}))
    return out


def _refusal(rel_path: str, source: str, verdict: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "rel_path": rel_path,
        "source_sha256": _sha(source), "verdict": verdict, "reason": reason,
        "licensed_sites": [], "refused_sites": [], "fraction_licensed": None,
    }


def licence(report: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a measurement into a licence: what may be taught here, and what must not be.

    Refusals come first and they are not zeros. A suite that was already red, a source that moved,
    or a source with no generatable perturbation at all produce no evidence, and "no evidence" must
    never read as "fully licensed".
    """
    base = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "rel_path": report.get("rel_path"),
        "source_sha256": report.get("source_sha256"),
    }
    if report.get("baseline_ok") is not True:
        return {**base, "verdict": REFUSED_BASELINE_RED,
                "reason": "THE_CHECK_DOES_NOT_PASS_WITHOUT_A_MUTANT_SO_IT_CANNOT_BE_READ",
                "licensed_sites": [], "refused_sites": [], "fraction_licensed": None}
    if report.get("baseline_stable") is False:
        return {**base, "verdict": REFUSED_FLAKY_BASELINE,
                "reason": "THE_CHECK_FAILS_ON_A_RERUN_OF_UNCHANGED_SOURCE",
                "licensed_sites": [], "refused_sites": [], "fraction_licensed": None}
    sites = list(report.get("sites") or [])
    if not sites:
        return {**base, "verdict": REFUSED_NO_MUTANTS,
                "reason": "NO_PERTURBATION_COULD_BE_GENERATED_SO_NOTHING_WAS_MEASURED",
                "licensed_sites": [], "refused_sites": [], "fraction_licensed": None}
    licensed = [s for s in sites if s.get("licensed")]
    refused = [s for s in sites if not s.get("licensed")]
    fraction = round(len(licensed) / len(sites), 6)
    if not refused:
        verdict = ALL_LICENSED
    elif not licensed:
        verdict = NONE_LICENSED
    else:
        verdict = PARTIAL
    return {
        **base,
        "verdict": verdict,
        "licensed_sites": [{"site_id": s["site_id"], "lineno": s["lineno"],
                            "node_kind": s["node_kind"]} for s in licensed],
        "refused_sites": [{"site_id": s["site_id"], "lineno": s["lineno"],
                           "node_kind": s["node_kind"], "survivors": s.get("survivors")}
                          for s in refused],
        "sites_measured": len(sites),
        "sites_licensed": len(licensed),
        "sites_refused": len(refused),
        "mutants_run": sum(int(s.get("mutants_run") or 0) for s in sites),
        "mutants_caught": sum(int(s.get("mutants_caught") or 0) for s in sites),
        "fraction_licensed": fraction,
        "teaching_rule": (
            "A lesson may be persisted about a LICENSED site only. A refused site is where the "
            "check is blind, so a lesson there can be wrong and still be blessed -- which is the "
            "one failure mode permanence makes unrecoverable."
        ),
        "does_not_say": [
            "that a licensed site is correct, only that the check can see a change there",
            "that a refused site is a defect in the project's tests",
            "that no wrong change could pass at a licensed site (empirical, not a proof)",
        ],
    }


# ------------------------------------------------------------------------ the learning connection

def teaching_permission(licence_report: Mapping[str, Any], *, site_id: str) -> dict[str, Any]:
    """The one question a learn path should ask before it persists a lesson.

    Named for what it is. It is a permission to teach, bounded by the measurement, and it never
    returns True on a refusal.
    """
    verdict = licence_report.get("verdict")
    if verdict not in (ALL_LICENSED, PARTIAL):
        return {"permitted": False, "reason": str(verdict),
                "why": "the check was not measured for this environment, so nothing here is licensed"}
    for site in _site_rows(licence_report.get("licensed_sites")):
        if site.get("site_id") == site_id:
            return {"permitted": True, "reason": "SITE_LICENSED",
                    "why": "every perturbation generated at this site was caught by the check"}
    for site in _site_rows(licence_report.get("refused_sites")):
        if site.get("site_id") == site_id:
            return {"permitted": False, "reason": "SITE_REFUSED_CHECK_IS_BLIND",
                    "survivors": site.get("survivors"),
                    "why": "a change here can be wrong and the check will still pass it"}
    return {"permitted": False, "reason": "SITE_NOT_MEASURED",
            "why": "no measurement exists for this site, so no licence can be granted"}


def record(report: Mapping[str, Any], licence_report: Mapping[str, Any]) -> dict[str, Any]:
    """A compact, hash-linked row fit to keep beside a persisted lesson."""
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "rel_path": licence_report.get("rel_path"),
        "source_sha256": licence_report.get("source_sha256"),
        "verdict": licence_report.get("verdict"),
        "sites_measured": licence_report.get("sites_measured"),
        "sites_licensed": licence_report.get("sites_licensed"),
        "fraction_licensed": licence_report.get("fraction_licensed"),
        "mutants_run": licence_report.get("mutants_run"),
        "measurement_sha256": _sha(
            __import__("json").dumps(report, sort_keys=True, separators=(",", ":"))
        ),
        "whole_task_correctness_proved": False,
    }


# ------------------------------------------------------------------------------- running a check
#
# Everything above is pure: text in, records out. This section is the one part that touches a
# machine, and it is deliberately the smallest possible version of that: copy the project once, run
# the caller's check, write one mutant at a time, put the bytes back, prove they came back.

import os
import shutil
import subprocess
import tempfile


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    returncode: int
    timed_out: bool
    seconds: float
    tail: str

    def row(self) -> dict[str, Any]:
        return {"passed": self.passed, "returncode": self.returncode,
                "timed_out": self.timed_out, "seconds": round(self.seconds, 3),
                "tail": self.tail}


class ScratchRunner:
    """Runs one check command against a throwaway copy, one mutant at a time.

    The caller's tree is never written. The mutant is written to the scratch copy, the check runs
    with the scratch copy as cwd, and the original bytes are restored in a `finally` and verified by
    hash before the next mutant. If the restore cannot be proved, this raises: a runner that leaves
    a mutant behind turns every later measurement into a fiction.

    `timeout` is not optional and not generous by default. A perturbation can turn a `while` into a
    loop that never ends. A timeout counts as CAUGHT (`TIMED_OUT`): the check did register something,
    and pretending it did not would understate the check. It is recorded separately so a reader can
    discount coincidences.
    """

    def __init__(self, project: str | os.PathLike[str], argv: Sequence[str], *,
                 timeout: float = 120.0, env: Mapping[str, str] | None = None,
                 keep: bool = False, extra_paths: Sequence[str] = ()) -> None:
        self.project = os.fspath(project)
        self.argv = [str(a) for a in argv]
        self.timeout = float(timeout)
        self.env = dict(env or {})
        self.keep = keep
        # src-layout projects import their package from `src/`, not from the repository root. Without
        # this, `import packaging` resolves to whatever is installed in site-packages and the mutant
        # is written into a file the check never opens -- which reads as "the tests are blind" when
        # the truth is "the harness measured somebody else's code". That happened on the first real
        # run of this tool, on `pypa/packaging`.
        self.extra_paths = [str(p) for p in extra_paths]
        self._tmp: str | None = None
        self._root: str | None = None

    def __enter__(self) -> "ScratchRunner":
        self._tmp = tempfile.mkdtemp(prefix="brain_oracle_licence_")
        self._root = os.path.join(self._tmp, os.path.basename(os.path.abspath(self.project)) or "proj")
        shutil.copytree(self.project, self._root,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".tox",
                                                      ".venv", "venv", "node_modules", ".pytest_cache"))
        return self

    def __exit__(self, *exc: object) -> None:
        if self._tmp and not self.keep:
            shutil.rmtree(self._tmp, ignore_errors=True)

    # -- the check itself ----------------------------------------------------------------
    def check(self) -> CheckResult:
        if not self._root:
            raise RuntimeError("SCRATCH_RUNNER_NOT_ENTERED")
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        roots = [self._root] + [os.path.join(self._root, p) for p in self.extra_paths]
        if env.get("PYTHONPATH"):
            roots.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(roots)
        env.update(self.env)
        started = __import__("time").monotonic()
        try:
            proc = subprocess.run(self.argv, cwd=self._root, capture_output=True, text=True,
                                  timeout=self.timeout, env=env)
        except subprocess.TimeoutExpired as expired:
            return CheckResult(passed=False, returncode=-1, timed_out=True,
                               seconds=__import__("time").monotonic() - started,
                               tail=((expired.stdout or "") if isinstance(expired.stdout, str) else ""))
        text = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
        return CheckResult(passed=proc.returncode == 0, returncode=proc.returncode,
                           timed_out=False, seconds=__import__("time").monotonic() - started,
                           tail="\n".join(text[-6:]))

    # -- one mutant ----------------------------------------------------------------------
    def _path(self, rel: str) -> str:
        if not self._root:
            raise RuntimeError("SCRATCH_RUNNER_NOT_ENTERED")
        target = os.path.normpath(os.path.join(self._root, rel))
        if os.path.commonpath([os.path.abspath(target), os.path.abspath(self._root)]) != os.path.abspath(self._root):
            raise RuntimeError(f"MUTANT_PATH_ESCAPES_SCRATCH:{rel}")
        return target

    def run_mutant(self, mutant: Mutant) -> dict[str, Any]:
        """Write the mutant, run the check, restore, and verify the restore. Never leaves it behind."""
        path = self._path(mutant.rel_path)
        with open(path, "rb") as handle:
            original = handle.read()
        try:
            with open(path, "wb") as handle:
                handle.write(mutant.code.encode("utf-8"))
            result = self.check()
        finally:
            with open(path, "wb") as handle:
                handle.write(original)
            with open(path, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != hashlib.sha256(original).hexdigest():
                    raise RuntimeError(f"MUTANT_NOT_RESTORED:{mutant.rel_path}")
        if result.timed_out:
            return {"caught": True, "killed_by": BY_TIMEOUT, "detail": result.row()}
        if result.passed:
            return {"caught": False, "killed_by": None, "detail": result.row()}
        lower = f"{result.tail}".lower()
        killed_by = BY_ERROR if ("error" in lower or "traceback" in lower) else BY_FAILURE
        return {"caught": True, "killed_by": killed_by, "detail": result.row()}

    # -- does the check even open this file? ----------------------------------------------
    def load_probe(self, rel_path: str) -> dict[str, Any]:
        """Prove the check reads the file we are about to mutate.

        Write a file that cannot be parsed, run the check, put the bytes back. A check that passes
        on an unparseable version of the file does not import it, and every mutant written there
        will "survive" for a reason that has nothing to do with the tests. This is the difference
        between `the check is blind to this behaviour` and `the check is blind to this file`, and
        only the first one is a licence question.

        It is sound in one direction: a check that FAILS on the broken file has shown it touches the
        file. It is not a proof that any particular behaviour is observed -- that is what the
        mutants are for.
        """
        path = self._path(rel_path)
        with open(path, "rb") as handle:
            original = handle.read()
        try:
            with open(path, "wb") as handle:
                handle.write(original + b"\ndef __oracle_licence_load_probe__( -> None:\n")
            result = self.check()
        finally:
            with open(path, "wb") as handle:
                handle.write(original)
            with open(path, "rb") as handle:
                if handle.read() != original:
                    raise RuntimeError(f"LOAD_PROBE_NOT_RESTORED:{rel_path}")
        return {"loaded": not result.passed, "check": result.row()}

    def load_probe_tests(self, rel_path: str) -> dict[str, Any]:
        """Per-test form: the broken file must make at least one previously-passing test stop passing."""
        path = self._path(rel_path)
        with open(path, "rb") as handle:
            original = handle.read()
        try:
            with open(path, "wb") as handle:
                handle.write(original + b"\ndef __oracle_licence_load_probe__( -> None:\n")
            result = self.check_tests()
        finally:
            with open(path, "wb") as handle:
                handle.write(original)
            with open(path, "rb") as handle:
                if handle.read() != original:
                    raise RuntimeError(f"LOAD_PROBE_NOT_RESTORED:{rel_path}")
        return {"result": result}

    # -- the baseline --------------------------------------------------------------------
    def baseline(self, *, twice: bool = True) -> dict[str, Any]:
        """Does the check pass on the untouched source, and does it still pass when run again?"""
        first = self.check()
        second = self.check() if twice else None
        stable = None if second is None else (second.passed == first.passed)
        return {"ok": first.passed, "stable": stable,
                "first": first.row(), "second": None if second is None else second.row()}


def measure_project(
    project: str | os.PathLike[str],
    rel_path: str,
    argv: Sequence[str],
    *,
    timeout: float = 120.0,
    operators: Sequence[str] = OPERATORS,
    max_mutants_per_site: int | None = None,
    sites_wanted: Sequence[str] | None = None,
    max_sites: int | None = None,
    max_mutants: int | None = None,
    extra_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Measure one file of one project against the project's own check, start to finish.

    COST, WHICH IS THE WHOLE DESIGN CONSTRAINT: one measurement costs
    `mutants x (seconds of the caller's check)`. A 700-line module can offer hundreds of sites at
    ~5 s per run, which is hours -- so `max_sites` and `max_mutants` exist and a caller that wants
    a licence it can afford must pass them. Nothing here is random: sites are taken in line order,
    so two runs over an unchanged file measure the same sites.
    """
    path = os.path.join(os.fspath(project), rel_path)
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    with ScratchRunner(project, argv, timeout=timeout, extra_paths=extra_paths) as runner:
        probe = runner.load_probe(rel_path)
        if not probe["loaded"]:
            return {"schema": SCHEMA, "authority": AUTHORITY, "rel_path": rel_path,
                    "source_sha256": _sha(source), "check_argv": list(argv),
                    "load_probe": probe,
                    "licence": _refusal(
                        rel_path, source, REFUSED_FILE_NOT_LOADED,
                        "THE_CHECK_PASSES_ON_A_FILE_THAT_CANNOT_BE_IMPORTED_SO_IT_NEVER_READ_IT")}
        base = runner.baseline()
        report = measure(source, rel_path=rel_path, run=runner.run_mutant, operators=operators,
                         sites_wanted=sites_wanted, max_mutants_per_site=max_mutants_per_site,
                         max_sites=max_sites, max_mutants=max_mutants,
                         baseline_ok=base["ok"])
        report["baseline"] = base
        report["baseline_stable"] = base["stable"]
        report["check_argv"] = list(argv)
        report["check_timeout_seconds"] = timeout
        report["load_probe"] = probe
    report["licence"] = licence(report)
    return report


# --------------------------------------------------------------- per-test accounting (the real rule)
#
# The boolean runner above has one honest weakness: if the project's check is already red on one
# test, the whole measurement refuses, and a repository with two pre-existing failures -- which is
# most repositories -- can never be measured. That is not a property of the project; it is a
# property of asking a boolean question.
#
# The question a check actually answers is per test. So the mutant is caught when a test that
# PASSED on the unmutated source FAILS on the mutant. That is exactly SWE-bench's fail-to-pass /
# pass-to-pass rule applied at the level of one perturbation, and it has three consequences worth
# stating, because they are the difference between a measurement and a score:
#
#   * a test broken BEFORE the mutant cannot make anything look caught, so pre-existing red is
#     harmless and does not have to be "fixed" or excluded by hand;
#   * a mutant that breaks a test nobody was looking at still counts -- the check saw it, and a
#     lesson that breaks it will be refused by the same check;
#   * a mutant that makes a test ERROR counts, and is labelled, because the check did register it.

import xml.etree.ElementTree as _ET


def parse_junit(path: str | os.PathLike[str]) -> dict[str, str]:
    """{test id: PASSED | FAILED | ERROR | SKIPPED} from a junit xml file. Empty when unreadable."""
    try:
        root = _ET.parse(os.fspath(path)).getroot()
    except Exception:
        return {}
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        name = f"{case.get('classname') or ''}::{case.get('name') or ''}"
        status = "PASSED"
        for child in case:
            tag = (child.tag or "").lower()
            if tag == "failure":
                status = "FAILED"
            elif tag == "error":
                status = "ERROR"
            elif tag == "skipped":
                status = "SKIPPED"
        if outcomes.get(name) in ("ERROR", "FAILED"):
            continue
        outcomes[name] = status
    return outcomes


class JunitScratchRunner(ScratchRunner):
    """A ScratchRunner that reads the check per test instead of as one boolean.

    `argv` must write a junit xml file. Pass `junit_arg` naming how to tell the check where to put
    it, e.g. `"--junitxml={path}"` for pytest. Everything else is inherited, including the restore
    proof and the timeout accounting.
    """

    def __init__(self, project: str | os.PathLike[str], argv: Sequence[str], *,
                 junit_arg: str = "--junitxml={path}", **kwargs: Any) -> None:
        super().__init__(project, argv, **kwargs)
        self.junit_arg = junit_arg
        self._junit_dir: str | None = None

    def __enter__(self) -> "JunitScratchRunner":
        super().__enter__()
        self._junit_dir = tempfile.mkdtemp(prefix="brain_oracle_junit_")
        return self

    def __exit__(self, *exc: object) -> None:
        super().__exit__(*exc)
        if self._junit_dir:
            shutil.rmtree(self._junit_dir, ignore_errors=True)

    def check_tests(self) -> dict[str, Any]:
        """Run the check once; return its per-test outcomes and whether it registered failure."""
        import time
        if not self._root or not self._junit_dir:
            raise RuntimeError("SCRATCH_RUNNER_NOT_ENTERED")
        out = os.path.join(self._junit_dir, f"junit_{time.monotonic_ns()}.xml")
        argv = [a.replace("{path}", out) for a in self.argv]
        if not any("{path}" in a for a in self.argv):
            argv = argv + [self.junit_arg.replace("{path}", out)]
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        roots = [self._root] + [os.path.join(self._root, p) for p in self.extra_paths]
        if env.get("PYTHONPATH"):
            roots.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(roots)
        env.update(self.env)
        started = time.monotonic()
        timed_out = False
        returncode = -1
        try:
            proc = subprocess.run(argv, cwd=self._root, capture_output=True, text=True,
                                  timeout=self.timeout, env=env)
            returncode = proc.returncode
            tail = "\n".join(((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-6:])
        except subprocess.TimeoutExpired as expired:
            timed_out = True
            tail = str(getattr(expired, "stdout", "") or "")[-400:]
        tests = parse_junit(out)
        return {"tests": tests, "timed_out": timed_out, "returncode": returncode,
                "seconds": round(time.monotonic() - started, 3), "tail": tail}

    def run_mutant_tests(self, mutant: Mutant) -> dict[str, Any]:  # type: ignore[override]
        path = self._path(mutant.rel_path)
        with open(path, "rb") as handle:
            original = handle.read()
        try:
            with open(path, "wb") as handle:
                handle.write(mutant.code.encode("utf-8"))
            result = self.check_tests()
        finally:
            with open(path, "wb") as handle:
                handle.write(original)
            with open(path, "rb") as handle:
                if handle.read() != original:
                    raise RuntimeError(f"MUTANT_NOT_RESTORED:{mutant.rel_path}")
        return result


def compare_per_test(baseline: Mapping[str, str], after: Mapping[str, str]) -> dict[str, Any]:
    """Was the mutant seen? A mutant is caught when a baseline-passing test no longer passes.

    Tests that errored or disappeared also count: the check registered something, and which kind is
    recorded so a reader can tell a behavioural failure from a crash.
    """
    newly_failing = sorted(
        name for name, status in baseline.items()
        if status == "PASSED" and after.get(name, "MISSING") != "PASSED"
    )
    kinds: dict[str, int] = {}
    for name in newly_failing:
        kinds[after.get(name, "MISSING")] = kinds.get(after.get(name, "MISSING"), 0) + 1
    return {
        "caught": bool(newly_failing),
        "newly_failing": newly_failing[:8],
        "newly_failing_count": len(newly_failing),
        "kinds": kinds,
        "killed_by": ("TEST_ERRORED" if kinds.get("ERROR") else
                      "TEST_FAILED" if newly_failing else None),
    }


def measure_project_per_test(
    project: str | os.PathLike[str],
    rel_path: str,
    argv: Sequence[str],
    *,
    timeout: float = 120.0,
    operators: Sequence[str] = OPERATORS,
    max_mutants_per_site: int | None = None,
    sites_wanted: Sequence[str] | None = None,
    junit_arg: str = "--junitxml={path}",
    max_sites: int | None = None,
    max_mutants: int | None = None,
    extra_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Measure one file against a per-test reading of the project's check.

    `max_sites` / `max_mutants` are the budget, in the same units as `measure_project`.
    """
    path = os.path.join(os.fspath(project), rel_path)
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    with JunitScratchRunner(project, argv, junit_arg=junit_arg, timeout=timeout,
                            extra_paths=extra_paths) as runner:
        first = runner.check_tests()
        broken = runner.load_probe_tests(rel_path)
        touched = compare_per_test(first["tests"], broken["result"]["tests"])
        if not touched["caught"] and not broken["result"]["timed_out"]:
            return {"schema": SCHEMA, "authority": AUTHORITY, "rel_path": rel_path,
                    "source_sha256": _sha(source), "check_argv": list(argv),
                    "load_probe": {"loaded": False,
                                   "note": "an unparseable version of this file changed no "
                                           "passing test, so the check never imports it",
                                   "check": {k: broken["result"][k] for k in
                                             ("timed_out", "returncode", "seconds")}},
                    "licence": _refusal(
                        rel_path, source, REFUSED_FILE_NOT_LOADED,
                        "THE_CHECK_PASSES_ON_A_FILE_THAT_CANNOT_BE_IMPORTED_SO_IT_NEVER_READ_IT")}
        second = runner.check_tests()
        stable = {k: v for k, v in second["tests"].items() if v == "PASSED"} == \
                 {k: v for k, v in first["tests"].items() if v == "PASSED"}
        baseline = first["tests"]
        passing = sum(1 for v in baseline.values() if v == "PASSED")

        def run(mutant: Mutant) -> dict[str, Any]:
            after = runner.run_mutant_tests(mutant)
            if after["timed_out"]:
                return {"caught": True, "killed_by": BY_TIMEOUT,
                        "detail": {"timed_out": True, "seconds": after["seconds"]},
                        "newly_failing_count": None}
            judged = compare_per_test(baseline, after["tests"])
            if not after["tests"] and not after["returncode"] == 0:
                return {"caught": True, "killed_by": BY_ERROR,
                        "detail": {"returncode": after["returncode"], "tail": after["tail"]},
                        "newly_failing_count": None,
                        "note": "the check produced no readable per-test report and did not pass"}
            return {**judged, "detail": {"returncode": after["returncode"]}}

        report = measure(source, rel_path=rel_path, run=run, operators=operators,
                         sites_wanted=sites_wanted, max_mutants_per_site=max_mutants_per_site,
                         max_sites=max_sites, max_mutants=max_mutants,
                         baseline_ok=passing > 0)
        report["baseline"] = {
            "tests_total": len(baseline),
            "tests_passing": passing,
            "tests_not_passing": sorted(n for n, s in baseline.items() if s != "PASSED")[:8],
            "stable_across_reruns": stable,
            "first_run": {k: first[k] for k in ("timed_out", "returncode", "seconds")},
        }
        report["baseline_stable"] = stable
        report["check_argv"] = list(argv)
        report["check_timeout_seconds"] = timeout
        report["quantifier"] = f"{passing} passing tests"
        report["load_probe"] = {"loaded": True,
                                "broken_version_broke": touched["newly_failing_count"],
                                "kinds": touched["kinds"]}
    report["licence"] = licence(report)
    return report


# --------------------------------------------------------------------------------------- the cache
#
# A licence costs one check run per mutant -- minutes on a real project. Paying that every time a
# lesson is considered would make the honest thing the expensive thing, and the expensive thing is
# the one that gets skipped. So the licence is content-addressed and kept: the same bytes, the same
# check and the same budget produce the same answer, and a file that changes gets measured again.
#
# What is deliberately NOT cached: nothing about correctness. The cache holds a measurement, and a
# measurement whose inputs are hashed can be replayed without being trusted.

import json


def cache_key(*, project: str, rel_path: str, source_sha256: str, argv: Sequence[str],
              operators: Sequence[str], max_sites: int | None, max_mutants: int | None,
              extra_paths: Sequence[str] = ()) -> str:
    material = {
        "project": os.path.abspath(os.fspath(project)),
        "rel_path": rel_path,
        "source_sha256": source_sha256,
        "argv": [str(a) for a in argv],
        "operators": list(operators),
        "max_sites": max_sites,
        "max_mutants": max_mutants,
        "extra_paths": list(extra_paths),
        "schema": SCHEMA,
    }
    return _sha(json.dumps(material, sort_keys=True, separators=(",", ":")))


class LicenceCache:
    """A content-addressed store of licences. One JSON file per key; unreadable entries are misses."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = os.fspath(root)

    def _path(self, key: str) -> str:
        return os.path.join(self.root, key[:2], f"{key}.json")

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            with open(self._path(key), "r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except Exception:
            return None
        if stored.get("schema") != SCHEMA or stored.get("key") != key:
            return None
        return stored

    def put(self, key: str, licence_report: Mapping[str, Any],
            measurement: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = {"schema": SCHEMA, "key": key, "cached_licence": dict(licence_report),
                   "measurement": _slim(measurement) if measurement else None, "from_cache": False}
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, indent=1)
        os.replace(tmp, path)
        return payload


def _slim(measurement: Mapping[str, Any]) -> dict[str, Any]:
    """The measurement without the blocks that made it, so a cache stays a record and not a dump.

    Mutant source is never kept: it is reconstructible from the source hash and the site, and a
    cache full of mutated files is a liability. The check's output tails are trimmed to one line.
    """
    slim = dict(measurement)
    slim.pop("sites_source", None)
    sites = []
    for site in measurement.get("sites") or []:
        row = dict(site)
        mutants = []
        for mutant in site.get("mutants") or []:
            entry = {k: v for k, v in mutant.items() if k != "detail"}
            detail = mutant.get("detail")
            if isinstance(detail, Mapping):
                entry["result"] = {k: detail.get(k) for k in ("passed", "returncode", "timed_out")
                                   if k in detail}
            mutants.append(entry)
        row["mutants"] = mutants
        sites.append(row)
    slim["sites"] = sites
    return slim


def licence_for_project(
    project: str | os.PathLike[str],
    rel_path: str,
    argv: Sequence[str],
    *,
    cache: LicenceCache | None = None,
    per_test: bool = True,
    timeout: float = 120.0,
    operators: Sequence[str] = OPERATORS,
    max_sites: int | None = None,
    max_mutants: int | None = None,
    extra_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """The licence for one file, from the cache when the inputs are unchanged, measured otherwise."""
    path = os.path.join(os.fspath(project), rel_path)
    with open(path, "rb") as handle:
        source_sha = hashlib.sha256(handle.read()).hexdigest()
    key = cache_key(project=project, rel_path=rel_path, source_sha256=source_sha, argv=argv,
                    operators=operators, max_sites=max_sites, max_mutants=max_mutants,
                    extra_paths=extra_paths)
    if cache is not None:
        hit = cache.get(key)
        if hit is not None:
            return {**hit["cached_licence"], "measurement": hit.get("measurement"),
                    "from_cache": True, "cache_key": key,
                    "text": render_licence(hit["cached_licence"], from_cache=True)}
    measure_fn = measure_project_per_test if per_test else measure_project
    report = measure_fn(project, rel_path, argv, timeout=timeout, operators=operators,
                        max_sites=max_sites, max_mutants=max_mutants, extra_paths=extra_paths)
    licence_report = report["licence"]
    if cache is not None:
        cache.put(key, licence_report, report)
    return {**licence_report, "measurement": report, "from_cache": False,
            "cache_key": key, "text": render_licence(licence_report)}


# ------------------------------------------------------------------------------------ the writing

def render_licence(licence_report: Mapping[str, Any], *, from_cache: bool = False) -> str:
    """The licence as a sentence a person can act on, not a scoreboard."""
    verdict = licence_report.get("verdict")
    rel = licence_report.get("rel_path")
    if verdict == REFUSED_FILE_NOT_LOADED:
        return (f"{rel}: REFUSED — the check passes on a file that cannot be imported, so it never "
                f"reads this file. No measurement is possible and nothing here is licensed.")
    if verdict == REFUSED_BASELINE_RED:
        return (f"{rel}: REFUSED — the check does not pass without a mutant, so a failure cannot be "
                f"attributed to one.")
    if verdict == REFUSED_FLAKY_BASELINE:
        return (f"{rel}: REFUSED — the check fails when rerun on unchanged source; it cannot be read.")
    if verdict == REFUSED_NO_MUTANTS:
        return (f"{rel}: REFUSED — no perturbation could be generated, so nothing was measured.")
    licensed = int(licence_report.get("sites_licensed") or 0)
    measured = int(licence_report.get("sites_measured") or 0)
    fraction = licence_report.get("fraction_licensed")
    head = (f"{rel}: {licensed} of {measured} sites licensed "
            f"({fraction:.0%}){', from cache' if from_cache else ''}. "
            f"{licence_report.get('mutants_caught')} of {licence_report.get('mutants_run')} "
            f"perturbations seen by the check.")
    if verdict == ALL_LICENSED:
        tail = " Every behaviour tried here is visible to the check."
    elif verdict == NONE_LICENSED:
        tail = (" No behaviour tried here is visible to the check. A lesson here can be wrong and "
                "the check will bless it.")
    else:
        refused = licence_report.get("refused_sites") or []
        names = ", ".join(f"line {s['lineno']} ({s['node_kind']})" for s in refused[:4])
        tail = f" Blind at: {names}{' ...' if len(refused) > 4 else ''}."
    return head + tail


# ------------------------------------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure which changes a project's own check can see, and issue a licence.")
    parser.add_argument("--project", required=True, help="project root (read-only; copied)")
    parser.add_argument("--file", required=True, action="append",
                        help="path inside the project; repeat for several files")
    parser.add_argument("--check", required=True, nargs=argparse.REMAINDER,
                        help="the check command, run in the project copy, e.g. -- "
                             "python -m pytest -q tests/test_x.py")
    parser.add_argument("--extra-path", action="append", default=[],
                        help="directory inside the project to put on PYTHONPATH (src-layout)")
    parser.add_argument("--max-sites", type=int, default=10)
    parser.add_argument("--max-mutants", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--operators", default=",".join(OPERATORS))
    parser.add_argument("--boolean-runner", action="store_true",
                        help="read the check as pass/fail instead of per test")
    parser.add_argument("--cache", default=None, help="directory for the licence cache")
    parser.add_argument("--out", default=None, help="write the full report here as JSON")
    args = parser.parse_args(argv)

    check = [a for a in (args.check or []) if a != "--"]
    if not check:
        parser.error("--check needs a command after `--`")
    operators = [o.strip().upper() for o in args.operators.split(",") if o.strip()]
    cache = LicenceCache(args.cache) if args.cache else None

    reports = []
    for rel in args.file:
        result = licence_for_project(
            args.project, rel, check, cache=cache, per_test=not args.boolean_runner,
            timeout=args.timeout, operators=operators,
            max_sites=args.max_sites, max_mutants=args.max_mutants,
            extra_paths=tuple(args.extra_path))
        reports.append(result)
        print(result["text"])
    payload = {"schema": SCHEMA, "authority": AUTHORITY, "project": args.project,
               "check": check, "licences": reports}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, indent=1)
        print(f"wrote {args.out}")
    refused = [r for r in reports if not str(r.get("verdict", "")).endswith("LICENSED")
               or r.get("verdict") == NONE_LICENSED]
    return 0 if not refused else 1


if __name__ == "__main__":
    raise SystemExit(main())


# ------------------------------------------------------------------------ a licence for a project
#
# One file's licence answers "can the check see behaviour in this file". A learn path needs one step
# further back: "in this project, can the check see behaviour AT ALL, and where". That is what this
# is. It is deliberately not a codebase-wide mutation score -- that would cost hours and answer a
# question nobody asked. It measures a bounded, deterministic sample of files and reports the
# distribution, so a lesson path can say "teach here" or "do not teach here" with a number behind it.

PROJECT_LICENSED = "PROJECT_LICENSED_HERE"
PROJECT_PARTIAL = "PROJECT_LICENSED_AT_SOME_SITES"
PROJECT_BLIND = "PROJECT_CHECK_IS_BLIND_TO_EVERY_SITE_TRIED"
PROJECT_REFUSED = "PROJECT_UNMEASURED"


def licence_for_codebase(
    project: str | os.PathLike[str],
    files: Sequence[str],
    argv: Sequence[str],
    *,
    cache: LicenceCache | None = None,
    per_test: bool = True,
    timeout: float = 120.0,
    operators: Sequence[str] = OPERATORS,
    max_sites: int | None = 8,
    max_mutants: int | None = 16,
    extra_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Measure several files and say whether this project's check can gate a lesson at all.

    `files` is the caller's list, in the caller's order, and the whole list is measured -- there is no
    hidden sampling, because a licence that silently skipped a file would be a licence to teach in a
    place nobody looked.
    """
    per_file: list[dict[str, Any]] = []
    for rel in files:
        result = licence_for_project(project, rel, argv, cache=cache, per_test=per_test,
                                     timeout=timeout, operators=operators, max_sites=max_sites,
                                     max_mutants=max_mutants, extra_paths=extra_paths)
        per_file.append({
            "rel_path": rel, "verdict": result.get("verdict"),
            "sites_measured": result.get("sites_measured"),
            "sites_licensed": result.get("sites_licensed"),
            "mutants_run": result.get("mutants_run"),
            "mutants_caught": result.get("mutants_caught"),
            "fraction_licensed": result.get("fraction_licensed"),
            "from_cache": result.get("from_cache"),
            "licensed_sites": [s["site_id"] for s in (result.get("licensed_sites") or [])],
            "refused_sites": [s["site_id"] for s in (result.get("refused_sites") or [])],
            # The reason a site is refused, kept per site, so a project-scoped answer can say WHY a
            # particular site may not be taught instead of only that some other site may.
            "refused_site_rows": list(result.get("refused_sites") or []),
        })
    measured = [f for f in per_file if f.get("sites_measured")]
    licensed_sites = sum(int(f.get("sites_licensed") or 0) for f in measured)
    measured_sites = sum(int(f.get("sites_measured") or 0) for f in measured)
    if not measured or measured_sites == 0:
        verdict = PROJECT_REFUSED
    elif licensed_sites == measured_sites:
        verdict = PROJECT_LICENSED
    elif licensed_sites == 0:
        verdict = PROJECT_BLIND
    else:
        verdict = PROJECT_PARTIAL
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "scope": "PROJECT",
        "project": os.path.abspath(os.fspath(project)),
        "check_argv": [str(a) for a in argv],
        "verdict": verdict,
        "files": per_file,
        "sites_measured": measured_sites,
        "sites_licensed": licensed_sites,
        "fraction_licensed": (round(licensed_sites / measured_sites, 6)
                              if measured_sites else None),
        "teaching_rule": (
            "A lesson is persisted only for a site id licensed by a MEASURED file. Not measuring is "
            "not permission: PROJECT_UNMEASURED grants nothing."
        ),
        "text": (f"{len(measured)} of {len(files)} files measured; {licensed_sites} of "
                 f"{measured_sites} sites licensed. {verdict}."),
    }


def site_file(site_id: str | None) -> str:
    """The file a site id belongs to. A site id is `rel_path:line:col:kind`, so the file is a prefix.

    Deriving it instead of passing it separately is not tidiness: the first version of
    `project_permission` took both, and a caller that omitted `rel_path` got an empty string that
    matched no measured file, so every project-scoped licence refused everything. One identity, one
    place to get it wrong, and a test now pins it.
    """
    if not site_id:
        return ""
    head, sep, _tail = str(site_id).rpartition(":")
    head, sep2, _col = head.rpartition(":")
    head, sep3, _line = head.rpartition(":")
    return head if (sep and sep2 and sep3) else ""


def project_permission(
    project_report: Mapping[str, Any], *, rel_path: str = "", site_id: str | None = None,
) -> dict[str, Any]:
    """The project-scoped question a learn path asks: may a lesson be persisted about this place?

    `rel_path` may be omitted when `site_id` is given; the file is then read off the site id. If both
    are given and disagree, the site id wins and the disagreement is reported rather than resolved
    silently.
    """
    derived = site_file(site_id)
    if derived and rel_path and derived != rel_path:
        return {"permitted": False, "reason": "SITE_AND_FILE_DISAGREE",
                "why": f"the site id says {derived!r} and the caller said {rel_path!r}"}
    rel_path = derived or rel_path
    verdict = project_report.get("verdict")
    if verdict in (PROJECT_REFUSED, PROJECT_BLIND, None):
        return {"permitted": False, "reason": str(verdict or "PROJECT_UNMEASURED"),
                "why": "the project's check was not shown to see any change here"}
    for entry in project_report.get("files") or []:
        if entry.get("rel_path") != rel_path:
            continue
        if site_id is not None:
            # The same question, the same code as a file-scoped licence. A project scope must not
            # answer a site question with a file-level "somewhere in here is fine".
            answer = teaching_permission(
                {"verdict": ALL_LICENSED if entry.get("licensed_sites") else NONE_LICENSED,
                 "licensed_sites": [{"site_id": s} for s in (entry.get("licensed_sites") or [])],
                 "refused_sites": (entry.get("refused_site_rows")
                                   or entry.get("refused_sites") or [])},
                site_id=site_id)
            return answer
        licensed = entry.get("licensed_sites") or []
        return {"permitted": bool(licensed),
                "reason": "FILE_HAS_LICENSED_SITES" if licensed else "FILE_HAS_NO_LICENSED_SITE",
                "licensed_sites": licensed,
                "why": ("this file has licensed sites; teach at those and nowhere else" if licensed
                        else "the check was blind to every perturbation tried in this file")}
    return {"permitted": False, "reason": "FILE_NOT_MEASURED",
            "why": "this file is not in the measured set, so nothing about it is licensed"}
