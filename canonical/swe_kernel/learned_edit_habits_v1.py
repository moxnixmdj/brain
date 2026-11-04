"""Edit habits learned from the creature's own successful repairs, persisted between runs.

Why this exists (pass sixteen). Passes twelve to fifteen added four producers, and every one of them
is an authored table: an operator family list, a NameError rule, arity regexes, syntax patterns. I was
adding one hand-written table per failure class, forever, which is exactly the static code the owner
rejects. Meanwhile `derived_edit_classes_v1` -- the one mechanism that DERIVES its knowledge from
successes -- was validated in pass eleven and left unwired, with the limitation written down and then
walked past.

This wires it, and makes the wiring the point:

  - OBSERVE is automatic. Every crystallized repair already hands (before_snippet, after_snippet) to
    the durable skill store; the same pair is now also observed here, so learning costs no extra run.
  - PERSIST is automatic. Habits are written to a JSON file beside the skill store and reloaded on the
    next process start, so the creature is different at the beginning of run N+1 than it was at the
    beginning of run N.
  - PROPOSE enters the live candidate list as just one more producer, screened by execution like all
    the others. Nothing here is trusted; it only gets to suggest.

The difference that matters: a hand-written table is knowledge the AUTHOR had. A habit is knowledge
the CREATURE earned, in a form it can grow by composition (`*->+` and `+->-` imply `*->-`).
"""

from __future__ import annotations

import json
import pathlib
from typing import Mapping

from canonical.swe_kernel.derived_edit_classes_v1 import DerivedEditClasses

SCHEMA = "BRAIN_LEARNED_EDIT_HABITS_V1"


class LearnedEditHabits:
    """Derived edit classes plus the durable store they live in."""

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        self.path = pathlib.Path(path) if path is not None else None
        self.classes = DerivedEditClasses()
        self._loaded = False

    # -- persistence ---------------------------------------------------------------------
    def load(self) -> "LearnedEditHabits":
        if self._loaded or self.path is None or not self.path.is_file():
            self._loaded = True
            return self
        try:
            row = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(row, dict) and row.get("schema") == SCHEMA:
                self.classes.observe_all(
                    (str(a), str(b)) for a, b in (row.get("observed") or []) if isinstance(a, str) or True
                )
        except (OSError, ValueError, TypeError):
            pass  # a corrupt habit file must never take the creature down; it simply learns again
        self._loaded = True
        return self

    def save(self) -> bool:
        if self.path is None:
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema": SCHEMA,
                "observed": sorted(list(p) for p in self.classes.observed()),
                "inferred": sorted(list(p) for p in self.classes.inferred()),
            }
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
            tmp.replace(self.path)
            return True
        except OSError:
            return False

    # -- learning ------------------------------------------------------------------------
    def observe_repair(self, before: str, after: str) -> tuple[str, str] | None:
        """Called on every verified repair. Returns the substitution learned, if any."""
        pair = self.classes.observe(before, after)
        if pair is not None:
            self.save()
        return pair

    # -- proposing -----------------------------------------------------------------------
    def propose(self, source_text: str, limit: int = 16) -> list[str]:
        return self.classes.propose(source_text, limit=limit)

    def summary(self) -> Mapping[str, object]:
        s = dict(self.classes.summary())
        s["persisted_to"] = str(self.path) if self.path else None
        return s


# The live instance the awake loop uses. Deliberately a module-level singleton: exactly one creature
# process learns at a time, and two instances writing the same JSON would race.
_LIVE: LearnedEditHabits | None = None


def live_habits(path: pathlib.Path | str | None = None) -> LearnedEditHabits:
    global _LIVE
    if _LIVE is None or (path is not None and _LIVE.path != pathlib.Path(path)):
        _LIVE = LearnedEditHabits(path).load()
    return _LIVE
