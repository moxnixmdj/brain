#!/usr/bin/env python3
"""A skill that stops paying for itself must stop being offered.

Why this exists
---------------
`VerifiedSkillStore.invalidate()` works and is tested, and `rule_expiry_v1` ages a rule out when
the *world* moves underneath it. Neither answers the other half of the question. Measured
2026-11-25 on this tree: **nothing retires a skill for poor contribution.** `invalidate()` has to
be called by someone who already decided to call it; expiry only fires when the interpreter, the
platform or a watched tool changed. A skill can be wrong about the task while the world sits
perfectly still -- and one that keeps being *offered* and keeps not helping is not neutral. It
crowds recall, it costs a verification, and it returns a confident answer built on a lesson that
never paid.

The 2026 literature reached the same place from the other side and called it *library drift*:
unbounded growth without outcome-driven retirement drifts an agent below its no-skill baseline.
The repair is a ledger plus two finite numbers -- a retirement threshold and a bounded active cap.

What this refuses to do
-----------------------
Retire on its own judgement. `Library Drift`'s own bound, ``E[p] >= p0 - (tau + eps) - C*delta``,
is only worth the arithmetic when the outcome signal is trustworthy. `The Blind Curator` measured
that a biased judge does not merely add noise: it **silently switches retirement off**, and the
failure shows up in no aggregate metric. Their conclusion is the one this module enforces: the
mechanism survives only for *near-zero-false-pass, verifier-like graders*.

So retirement is not permitted because we would like it to be. It is permitted when a grader's
false-pass rate has been **measured** and is below `RETIREMENT_NEEDS_FALSE_PASS_BELOW`:

    retirement is permitted  <=>  measured false_pass_rate < 0.02     (and n >= 50)

An unmeasured grader -- no false-pass rate, or too few trials to say -- is refused, not assumed
good. This repository can afford that rule because its graders are verification programs, and a
verification program's error rate is a computable property of the observation
(`computer_use_check_density_v1` measures exactly the false-accept side of it). A system graded by
an LLM judge cannot state this number, which is why such a system cannot safely retire at all.

Retirement is not deletion. The row and its evidence stay addressable; `state` moves to
INVALIDATED through the store's own `invalidate()`, which every recall path already refuses. A
retired skill can be reinstated by new evidence. Its history is never rewritten.

What it will not claim
----------------------
The +0.328 pass@1 that `Ratchet` reports is somebody else's benchmark on a frozen LLM. This module
ships the mechanism and a test that the mechanism is load-bearing; it makes no claim that the
numbers transfer until they are measured here.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_SKILL_CONTRIBUTION_LEDGER_V1"

ACTIVE = "ACTIVE"
RETIRED = "RETIRED"
REINSTATED = "REINSTATED"

#: Outcomes, as the caller reports them. Anything else is a caller bug, refused rather than
#: silently bucketed -- an unknown outcome must not be able to look like a success.
REUSED_AND_HELPED = "REUSED_AND_HELPED"
REUSED_AND_FAILED = "REUSED_AND_FAILED"
OFFERED_NOT_USED = "OFFERED_NOT_USED"

_OUTCOMES = frozenset({REUSED_AND_HELPED, REUSED_AND_FAILED, OFFERED_NOT_USED})

#: A skill must be attempted this many times before silence about it can mean anything.
DEFAULT_MIN_TRIALS = 3

#: Retire when the measured success rate is at or below this. Not zero: a skill that helps once in
#: ten is still mostly noise in the shortlist, and `Ratchet`'s own default threshold is 0.10.
DEFAULT_THRESHOLD = 0.10

#: A bounded active cap is what turns unbounded growth into a bounded problem. `Ratchet` uses 50
#: for skills; this store's rows are finer-grained (one per crystallized pattern), so 200.
DEFAULT_ACTIVE_CAP = 200

#: The false-pass rate a grader must be shown to be below before its verdicts may retire anything.
RETIREMENT_NEEDS_FALSE_PASS_BELOW = 0.02

#: One-sided confidence the bound is stated at.
CONFIDENCE = 0.95


class CuratorError(RuntimeError):
    """A named failure. The curator never fails quietly and never retires on a guess."""


# --------------------------------------------------------------------------- grader admissibility
def _betainc(a: float, b: float, x: float, _depth: int = 0) -> float:
    """Regularized incomplete beta I_x(a,b), stdlib only.

    A dependency would be one more part to install and one more way for the gate to be absent on a
    machine that needs it. This is the standard continued fraction (Lentz), which converges in
    tens of iterations for the shapes used here.
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    # The swap is used at most once: exactly on the boundary (a+1)/(a+b+2) the two forms
    # are equal and would exchange forever, so a second level always continues the fraction.
    if _depth > 0 or x < (a + 1.0) / (a + b + 2.0):
        # continued fraction for I_x directly
        c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        result = d
        for m in range(1, 500):
            m2 = 2 * m
            num = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
            d = 1.0 + num * d
            d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
            c = 1.0 + num / c if abs(c) > 1e-300 else 1.0 + num / 1e-300
            result *= d * c
            num = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
            d = 1.0 + num * d
            d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
            c = 1.0 + num / c if abs(c) > 1e-300 else 1.0 + num / 1e-300
            delta = d * c
            result *= delta
            if abs(delta - 1.0) < 1e-14:
                break
        return result * front / a
    return 1.0 - _betainc(b, a, 1.0 - x, _depth + 1)


def _beta_ppf(q: float, a: float, b: float) -> float:
    """Inverse of `_betainc` in x, by bisection. Deterministic, bounded, ~50 evaluations."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if _betainc(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _binomial_upper_bound(failures: int, trials: int, confidence: float = CONFIDENCE) -> float:
    """Clopper-Pearson upper bound on a rate.

    A naive ``failures / trials < 0.02`` check is not a measurement, it is a mood. Zero failures in
    34 trials is entirely consistent with an 8.5% false-pass rate; zero in 149 is consistent with
    under 2%. Retirement decisions get the bound, not the point estimate.

    Exact form: the upper bound is the ``1-alpha`` quantile of ``Beta(failures+1, trials-failures)``.
    """
    if trials <= 0:
        return 1.0
    if failures >= trials:
        return 1.0
    alpha = 1.0 - float(confidence)
    return _beta_ppf(1.0 - alpha, failures + 1.0, trials - failures)


def trials_needed(failures: int = 0, confidence: float = CONFIDENCE,
                  threshold: float = RETIREMENT_NEEDS_FALSE_PASS_BELOW) -> int:
    """How many clean trials it takes to certify a grader at `threshold`. Reported, not guessed."""
    trials = max(int(failures), 1)
    while trials < 100000:
        if _binomial_upper_bound(failures, trials, confidence) < threshold:
            return trials
        trials += 1
    raise CuratorError("TRIALS_NEEDED_UNREACHABLE")


def grader_may_retire(report: Mapping[str, Any] | None) -> tuple[bool, str]:
    """May this grader's verdicts move a skill out of recall?

    Returns ``(permitted, reason)``. The reason is always populated: a refusal that cannot say why
    is indistinguishable from a bug, and this gate refuses more often than it permits.
    """
    if not isinstance(report, Mapping):
        return False, "NO_GRADER_REPORT"
    rate = report.get("false_pass_rate")
    n = report.get("trials")
    if rate is None:
        return False, "FALSE_PASS_RATE_UNMEASURED"
    if not isinstance(rate, (int, float)) or isinstance(rate, bool):
        return False, "FALSE_PASS_RATE_NOT_A_NUMBER"
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        return False, f"TOO_FEW_TRIALS:{n}"

    failures = report.get("false_passes")
    if not isinstance(failures, int) or isinstance(failures, bool):
        failures = int(round(float(rate) * n))

    bound = _binomial_upper_bound(failures, n)
    if bound >= RETIREMENT_NEEDS_FALSE_PASS_BELOW:
        return False, (
            f"GRADER_NOT_PROVEN_TIGHT:upper_bound={bound:.4f}>="
            f"{RETIREMENT_NEEDS_FALSE_PASS_BELOW:.2f}_from_{failures}/{n}"
            f"_needs_{trials_needed(failures)}_trials"
        )
    return True, f"GRADER_PROVEN_TIGHT:upper_bound={bound:.4f}"


def grader_from_check_density(
    density_report: Mapping[str, Any] | None = None,
    *,
    observation_model: str = "full",
) -> dict[str, Any]:
    """Adapt `computer_use_check_density_v1`'s output into a grader report.

    That module answers the false-accept question directly: of the wrong actions whose observable was
    *identical* to the recorded consequence, how many would a differential accept? Those are false
    passes, and `INDISTINGUISHABLE` is the category that names them.

    The real report is keyed ``density_by_observation[model]`` and counts 34 mutants, so on today's
    corpus every observation model is refused -- `full` at 0/34 has an upper bound of 8.4%, nowhere
    near the 2% the gate demands. That is the correct answer, and the refusal states the number of
    clean trials that would change it.
    """
    if density_report is None:
        from canonical.swe_kernel import computer_use_check_density_v1 as _density
        density_report = _density.measure()
    if not isinstance(density_report, Mapping):
        raise CuratorError("CHECK_DENSITY_REPORT_REQUIRED")

    by_observation = density_report.get("density_by_observation") or {}
    block = by_observation.get(observation_model) or {}
    if not block:
        return {"false_pass_rate": None, "trials": 0,
                "source": f"CHECK_DENSITY:{observation_model}", "refusal": "NO_SUCH_OBSERVATION_MODEL"}

    trials = int(density_report.get("mutants") or 0)
    false_passes = int(block.get("INDISTINGUISHABLE") or 0)
    return {
        "false_pass_rate": (false_passes / trials) if trials else None,
        "false_passes": false_passes,
        "trials": trials,
        "source": f"CHECK_DENSITY:{observation_model}",
        "checked_density": block.get("density"),
    }


# --------------------------------------------------------------------------- storage
_LEDGER = "skill_contribution_ledger_v1"
_EVENTS = "skill_contribution_events_v1"


def _connect(db_path: Path) -> sqlite3.Connection:
    """Create the ledger tables beside the store, in the store's own file.

    Same file on purpose: a ledger in a different file can be lost, copied or restored separately
    from the skills it is about, and then the store's history and its evidence disagree.
    """
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_LEDGER} ("
        "  skill_id TEXT PRIMARY KEY,"
        "  trials INTEGER NOT NULL DEFAULT 0,"
        "  helped INTEGER NOT NULL DEFAULT 0,"
        "  failed INTEGER NOT NULL DEFAULT 0,"
        "  offered_not_used INTEGER NOT NULL DEFAULT 0,"
        "  state TEXT NOT NULL DEFAULT 'ACTIVE',"
        "  retired_ts REAL,"
        "  retired_reason TEXT,"
        "  first_ts REAL NOT NULL,"
        "  last_ts REAL NOT NULL"
        ")"
    )
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_EVENTS} ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  skill_id TEXT NOT NULL,"
        "  outcome TEXT NOT NULL,"
        "  ts REAL NOT NULL,"
        "  note TEXT"
        ")"
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_contrib_state ON {_LEDGER}(state)")
    conn.commit()
    return conn


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    trials = int(out.get("trials") or 0)
    out["success_rate"] = (int(out.get("helped") or 0) / trials) if trials else None
    return out


# --------------------------------------------------------------------------- the ledger
class ContributionLedger:
    """Append-only evidence, current state. The evidence is never rewritten; only `state` moves."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        _connect(self.db_path).close()

    # -- recording -----------------------------------------------------------------
    def record(self, skill_id: str, outcome: str, *, note: str = "") -> dict[str, Any]:
        if not str(skill_id).strip():
            raise CuratorError("SKILL_ID_REQUIRED")
        if outcome not in _OUTCOMES:
            raise CuratorError(f"UNKNOWN_OUTCOME:{outcome}")
        now = time.time()
        conn = _connect(self.db_path)
        try:
            with conn:
                # Seed at zero: the counter below is the only thing that counts a trial, so
                # seeding at 1 would make the first record count twice.
                conn.execute(
                    f"INSERT INTO {_LEDGER} (skill_id, trials, helped, failed, offered_not_used,"
                    " state, first_ts, last_ts) VALUES (?,0,0,0,0,'ACTIVE',?,?)"
                    " ON CONFLICT(skill_id) DO NOTHING",
                    (skill_id, now, now),
                )
                column = {
                    REUSED_AND_HELPED: "helped",
                    REUSED_AND_FAILED: "failed",
                    OFFERED_NOT_USED: "offered_not_used",
                }[outcome]
                conn.execute(
                    f"UPDATE {_LEDGER} SET trials=trials+1, {column}={column}+1, last_ts=?"
                    " WHERE skill_id=?",
                    (now, skill_id),
                )
                conn.execute(
                    f"INSERT INTO {_EVENTS} (skill_id, outcome, ts, note) VALUES (?,?,?,?)",
                    (skill_id, outcome, now, note[:2000]),
                )
        finally:
            conn.close()
        return self.status(skill_id)

    # -- reading -------------------------------------------------------------------
    def status(self, skill_id: str) -> dict[str, Any]:
        conn = _connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT * FROM {_LEDGER} WHERE skill_id=?", (skill_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return {"skill_id": skill_id, "trials": 0, "success_rate": None,
                    "state": None, "known": False}
        out = _row_to_dict(row)
        out["known"] = True
        return out

    def history(self, skill_id: str) -> list[dict[str, Any]]:
        conn = _connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT outcome, ts, note FROM {_EVENTS} WHERE skill_id=? ORDER BY id", (skill_id,)
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def active_count(self) -> int:
        conn = _connect(self.db_path)
        try:
            (n,) = conn.execute(
                f"SELECT COUNT(*) FROM {_LEDGER} WHERE state='{ACTIVE}'"
            ).fetchone()
        finally:
            conn.close()
        return int(n)

    def census(self) -> dict[str, Any]:
        conn = _connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = [_row_to_dict(r) for r in conn.execute(f"SELECT * FROM {_LEDGER}").fetchall()]
        finally:
            conn.close()
        by_state: dict[str, int] = {}
        for row in rows:
            by_state[row["state"]] = by_state.get(row["state"], 0) + 1
        return {
            "schema": SCHEMA,
            "skills_tracked": len(rows),
            "by_state": by_state,
            "active": by_state.get(ACTIVE, 0),
            "retired": by_state.get(RETIRED, 0),
            "helped": sum(int(r.get("helped") or 0) for r in rows),
            "failed": sum(int(r.get("failed") or 0) for r in rows),
        }

    # -- decisions -----------------------------------------------------------------
    def overdue(self, *, min_trials: int = DEFAULT_MIN_TRIALS,
                threshold: float = DEFAULT_THRESHOLD) -> list[dict[str, Any]]:
        """Active skills whose measured success rate has fallen to the threshold.

        `min_trials` is the evidence floor. Without it a single failure retires anything, which is
        the over-retirement ablation `Ratchet` measured as actively harmful.
        """
        conn = _connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = [_row_to_dict(r) for r in conn.execute(
                f"SELECT * FROM {_LEDGER} WHERE state='{ACTIVE}' AND trials>=?",
                (int(min_trials),),
            ).fetchall()]
        finally:
            conn.close()
        return [r for r in rows if r["success_rate"] is not None
                and r["success_rate"] <= float(threshold)]


# --------------------------------------------------------------------------- the curator
def curate(
    store: Any,
    ledger: ContributionLedger,
    *,
    grader_report: Mapping[str, Any] | None,
    min_trials: int = DEFAULT_MIN_TRIALS,
    threshold: float = DEFAULT_THRESHOLD,
    active_cap: int = DEFAULT_ACTIVE_CAP,
) -> dict[str, Any]:
    """Retire what stopped paying and evict past the cap -- but only on a measured grader.

    Returns a report, never a bare boolean. Every refusal names itself.
    """
    permitted, why = grader_may_retire(grader_report)
    if not permitted:
        return {
            "schema": SCHEMA,
            "action": "REFUSED",
            "refusal": why,
            "grader": dict(grader_report or {}),
            "retired": [],
            "evicted": [],
            "reason": (
                "retirement is a claim about the world; an unmeasured grader cannot make it"
            ),
        }

    retired: list[dict[str, Any]] = []
    for row in ledger.overdue(min_trials=min_trials, threshold=threshold):
        sid = str(row["skill_id"])
        ok = store.invalidate(
            sid,
            f"CONTRIBUTION_BELOW_THRESHOLD:{row['success_rate']:.4f}<={float(threshold):.4f}"
            f"_after_{row['trials']}_trials",
        )
        if ok:
            _mark(ledger, sid, RETIRED, f"threshold {float(threshold):.4f}",
                  f"{row['helped']}/{row['trials']} helped")
            retired.append({"skill_id": sid, "success_rate": row["success_rate"],
                            "trials": row["trials"]})

    evicted: list[dict[str, Any]] = []
    active = ledger.active_count()
    if active > int(active_cap):
        excess = active - int(active_cap)
        conn = _connect(ledger.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = [_row_to_dict(r) for r in conn.execute(
                f"SELECT * FROM {_LEDGER} WHERE state='{ACTIVE}'").fetchall()]
        finally:
            conn.close()
        # Lowest measured contribution goes first; ties break on fewest trials, because the skill
        # we know least about is the one whose shortlist slot is worth least.
        rows.sort(key=lambda r: (r["success_rate"] if r["success_rate"] is not None else 1.0,
                                 r["trials"]))
        for row in rows[:excess]:
            sid = str(row["skill_id"])
            if store.invalidate(sid, f"ACTIVE_CAP_EVICTION:{active}>{int(active_cap)}"):
                _mark(ledger, sid, RETIRED, "active cap", "lowest measured contribution")
                evicted.append({"skill_id": sid, "success_rate": row["success_rate"],
                                "trials": row["trials"]})

    return {
        "schema": SCHEMA,
        "action": "CURATED",
        "grader": dict(grader_report or {}),
        "retired": retired,
        "evicted": evicted,
        "active_after": ledger.active_count(),
        "active_cap": int(active_cap),
        "threshold": float(threshold),
        "min_trials": int(min_trials),
    }


def _mark(ledger: ContributionLedger, skill_id: str, state: str, reason: str, note: str) -> None:
    now = time.time()
    conn = _connect(ledger.db_path)
    try:
        with conn:
            conn.execute(
                f"UPDATE {_LEDGER} SET state=?, retired_ts=?, retired_reason=? WHERE skill_id=?",
                (state, now, f"{reason} | {note}", skill_id),
            )
            conn.execute(
                f"INSERT INTO {_EVENTS} (skill_id, outcome, ts, note) VALUES (?,?,?,?)",
                (skill_id, f"STATE_{state}", now, f"{reason} | {note}"[:2000]),
            )
    finally:
        conn.close()


def reinstate(store: Any, ledger: ContributionLedger, skill_id: str, *,
              grader_report: Mapping[str, Any] | None, note: str = "") -> dict[str, Any]:
    """New evidence may put a retired skill back. Retirement is a state, not a deletion."""
    permitted, why = grader_may_retire(grader_report)
    if not permitted:
        return {"schema": SCHEMA, "action": "REFUSED", "refusal": why}
    conn = _connect(ledger.db_path)
    try:
        with conn:
            row = conn.execute(
                f"SELECT state FROM {_LEDGER} WHERE skill_id=?", (skill_id,)
            ).fetchone()
            if row is None or row[0] != RETIRED:
                return {"schema": SCHEMA, "action": "REFUSED",
                        "refusal": "NOT_RETIRED" if row is None else f"STATE_IS_{row[0]}"}
            conn.execute(
                f"UPDATE {_LEDGER} SET state=?, retired_ts=NULL, retired_reason=NULL,"
                " trials=0, helped=0, failed=0, offered_not_used=0 WHERE skill_id=?",
                (REINSTATED, skill_id),
            )
            conn.execute(
                f"INSERT INTO {_EVENTS} (skill_id, outcome, ts, note) VALUES (?,?,?,?)",
                (skill_id, "STATE_REINSTATED", time.time(), note[:2000]),
            )
    finally:
        conn.close()
    store_row = _set_store_state(ledger, store, skill_id, "ACTIVE")
    return {"schema": SCHEMA, "action": "REINSTATED", "store_updated": store_row}


def _set_store_state(ledger: ContributionLedger, store: Any, skill_id: str, state: str) -> bool:
    """Flip the store's own `state` back without inventing a second write path."""
    db = getattr(store, "db_path", None)
    if db is None:
        return False
    conn = _connect(Path(db))
    try:
        with conn:
            row = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE skill_id=?", (skill_id,)
            ).fetchone()
            if row is None:
                return False
            rule = json.loads(row[0])
            rule["state"] = state
            conn.execute("UPDATE crystallized_skills SET pattern_json=? WHERE skill_id=?",
                         (json.dumps(rule), skill_id))
    finally:
        conn.close()
    return True
