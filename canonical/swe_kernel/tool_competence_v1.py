"""Which of my own tools work, on kind of failure? A competence model that is measured, not authored.

WHAT WAS WRONG
--------------
`failure_kind_v1._FAMILY_FOR` is a hand-written table saying which repair family should run first for
each kind of failure. Measured on 2026-11-05, it is wrong in 3 of 4 cases:

    failure kind   prior says first    what actually produced candidates
    VALUE          operator_family     operator_family      <- correct
    BINDING        stun_guard          nothing at all
    SIGNATURE      guided              signature_repair
    SYNTAX         guided              operator_family (5) and syntax_repair (1)

And `family_order()` is called from nowhere in the system. The prior had never been exercised, let
alone validated, while four commit messages described the failure-kind channel as load-bearing.

That is the deepest static thing in this codebase and it is not a missing mechanism: it is a BELIEF
about its own competence that nothing was ever allowed to correct. Twenty-one passes tuned the tools
and never asked the creature what it was good at.

WHAT THIS IS
------------
For each (failure kind, producer) pair, keep the outcome of the probes the loop already pays for:

    seen:      how often this producer was consulted on this kind
    produced:  how often it returned at least one candidate
    won:       how often its candidate was the one that passed the screen

From those, a per-kind ordering over producers that is *earned*. Ordering is the only thing this
decides -- every candidate is still screened by execution and the acceptance gate -- so a wrong ranking
costs probes, never correctness. That is exactly the property the authored prior claimed and never had.

WHAT IS LEARNED, WHAT REMAINS MINE
----------------------------------
The *set* of producers is still my list; this cannot invent a tool. The *classification* of a failure
into a kind is still `failure_kind_v1`'s authored patterns. What changes is the mapping from kind to
tool, which moves from my guess to the creature's measurement.

A producer with no history is ranked by optimism, not last, so the ordering explores rather than
locking onto whichever tool happened to work first.

Authority NONE, spend $0, `truth.achieved` false.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_TOOL_COMPETENCE_V1"

# Every producer the awake loop consults, by the name the loop knows it by. This list is the one thing
# here I authored, and it is unavoidable: the creature cannot name a tool it does not have.
TOOLS = (
    "interpretive",
    "synth_grammar",
    "habits",
    "operator_family",
    "binding",
    "signature",
    "syntax",
    "stun_guard",
    "guided",
    "deterministic_ast",
)


class ToolCompetence:
    """Per-(kind, tool) counts of consulted / produced / won, and an earned ordering per kind."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        # kind -> tool -> {"seen": n, "produced": m, "won": w}
        self.table: dict[str, dict[str, dict[str, float]]] = {}
        self.load()

    # -- persistence ---------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "table": self.table, "tools": list(TOOLS)}

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d.get("schema") == SCHEMA and isinstance(d.get("table"), dict):
                self.table = d["table"]
        except (ValueError, OSError, TypeError):
            return

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return

    # -- observation ---------------------------------------------------------------------------
    def note_produced(self, kind: str, produced: Mapping[str, int]) -> None:
        """Record, for one failure, how many candidates each producer offered."""
        row = self.table.setdefault(str(kind or "UNKNOWN"), {})
        for tool, n in produced.items():
            slot = row.setdefault(str(tool), {"seen": 0.0, "produced": 0.0, "won": 0.0})
            slot["seen"] += 1
            if int(n) > 0:
                slot["produced"] += 1
        self.save()

    def note_win(self, kind: str, tool: str) -> None:
        """Record which producer's candidate the screen accepted."""
        row = self.table.setdefault(str(kind or "UNKNOWN"), {})
        slot = row.setdefault(str(tool), {"seen": 0.0, "produced": 0.0, "won": 0.0})
        slot["won"] += 1
        self.save()

    # -- ranking -------------------------------------------------------------------------------
    def rank(self, kind: str) -> list[str]:
        """Tools ordered for this kind by measured promise; unexplored tools by optimism.

        A tool that has never been consulted gets a mid-range prior rather than last place: locking a
        tool out because it lost once is the failure mode that a fixed table has permanently, and the
        whole point is not to reproduce it in learned form.
        """
        row = self.table.get(str(kind or "UNKNOWN")) or {}
        scored: list[tuple[float, str]] = []
        for tool in TOOLS:
            slot = row.get(tool)
            if not slot or slot.get("seen", 0) <= 0:
                score = 0.35  # unexplored
            else:
                seen = max(1.0, slot["seen"])
                produced_rate = slot["produced"] / seen
                win_rate = slot["won"] / max(1.0, slot["produced"])
                # Producing anything at all is worth a lot (it is the precondition for a repair), and
                # winning is worth more. Shrunk so a single win is not a conclusion.
                score = 0.55 * produced_rate + 0.45 * ((slot["won"] + 0.5) / (slot["produced"] + 2.0))
                score = max(0.0, min(1.0, score))
            scored.append((-score, tool))
        scored.sort()
        return [t for _s, t in scored]

    def has_signal(self, kind: str) -> bool:
        """Is there any evidence at all for this kind? With zero wins every order is a tie.

        MEASURED 2026-11-05: on SIGNATURE the table held `guided produced 6, won 0` and
        `signature produced 6, won 0`. No tool ever won, so the ranking is arbitrary -- and presenting
        it as a learned preference would be exactly the sin the authored prior committed. A model of
        one's own competence has to be able to say "I have no evidence".
        """
        row = self.table.get(str(kind or "UNKNOWN")) or {}
        return any(float(v.get("won") or 0) > 0 for v in row.values())

    def should_consult(self, kind: str, tool: str, *, floor: float = 0.05) -> bool:
        """May this tool be skipped for this kind? Only with strong evidence against it.

        MEASURED 2026-11-05: reordering producers saved exactly nothing -- 14 candidates screened cold
        and 14 warm, identical -- because the screen takes the whole batch and stops on first pass, so
        every tool runs regardless of rank. Ordering is not a decision. This is: a tool may be skipped
        only when it has been consulted on this kind at least 3 times AND never once produced a
        candidate. Producing nothing is the only failure that justifies not asking, because a tool that
        produces wrong candidates still might produce the right one, and only the screen can tell.
        """
        row = self.table.get(str(kind or "UNKNOWN")) or {}
        slot = row.get(str(tool))
        if not slot:
            return True  # never tried: try it
        seen = float(slot.get("seen") or 0)
        produced = float(slot.get("produced") or 0)
        if seen >= 3 and produced <= floor:
            return False
        return True

    def orders(self) -> dict[str, list[str]]:
        return {k: self.rank(k) for k in sorted(self.table)}

    def summary(self) -> Mapping[str, Any]:
        return {
            "schema": SCHEMA,
            "kinds_observed": sorted(self.table),
            "orders": {k: self.rank(k)[:4] for k in sorted(self.table)},
            # Distinguish a measured preference from an arbitrary tie. This is the whole difference
            # between a competence model and a table that looks like one.
            "has_signal": {k: self.has_signal(k) for k in sorted(self.table)},
            "skipped": {k: [t for t in TOOLS if not self.should_consult(k, t)] for k in sorted(self.table)},
            "raw": self.table,
            "persisted_to": str(self.path) if self.path else None,
        }


_LIVE: ToolCompetence | None = None


def live_competence(path: str | pathlib.Path | None = None) -> ToolCompetence:
    global _LIVE
    p = pathlib.Path(path) if path else None
    if _LIVE is None or _LIVE.path != p:
        _LIVE = ToolCompetence(p)
    return _LIVE
