"""When a remembered route meets a higher-scoring rival, what decides?

The story this file records happened in three steps, each of which I got wrong.

STEP ONE. A forged csv counter was beating a source-code analyser on a csv goal and
producing a false pass. The analyser scored 17.62; the right tool scored 42.86. I added
a rule: if the top rival outscores the remembered route by the module's decisive margin
(1.25), memory yields. It fixed that case.

STEP TWO. The rule broke a pdf goal. A markdown->pdf *converter* scored 36.39 against
the remembered pdf text extractor at 28.39 -- ratio 1.28, just past the threshold. Memory
was suppressed, a converter was chosen, and the call failed. But a converter cannot read a
pdf; it writes one. The remembered route was the only correct one. The ratio could not tell
a stale memory from a load-bearing one, and no threshold could: raising it re-opened the
csv defect, lowering it broke the pdf case. The two differed by DEGREE (2.43x vs 1.28x)
when what separated them was KIND.

STEP THREE. The distinguishing fact is fit. Every bad rival here is a capability that
PRODUCES the kind of file the goal asks to CONSUME. A markdown->pdf converter produces
pdf. A source analyser produces a report, not rows. That is checkable directly, and it is
now checked before scoring is consulted at all -- the kind gate
(INPUT_KIND_CONTRADICTS_GOAL_FILE), which reads what a capability declares it processes
against the extension of the file the goal names.

With the fit check in place, the ratio guard was removed, and measured, EVERY case is
correct: csv 3 rows, README unresolved, pdf remembered, all four ast paraphrases
remembered. The guard was not merely unnecessary; it had been suppressing correct
memories on two of three families.

The law: a remembered route may not outrule evidence of FIT -- but weight of words is not
evidence of fit. Score how well prose matches a goal; decide what a capability can do with
what the goal has.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import capability_forge_v1 as Forge  # noqa: E402
from canonical.runtime import grounded_action_v1 as Act  # noqa: E402
from canonical.runtime import room_census_v1 as Census  # noqa: E402
from canonical.runtime import world_probe_v1 as Probe  # noqa: E402


class TheFitCheckAndTheScoreAreDifferentQuestions(unittest.TestCase):
    """No network, no fixtures beyond a temp room, no dependence on prior state."""

    def setUp(self) -> None:
        # The room must live inside the repository: safe_repo_path refuses to run a
        # capability against a path outside it, and that refusal is deliberate (it is not
        # a generalisation failure). A /tmp fixture therefore tests nothing at all --
        # measured, it yields {"ran": "0/3"} and every assertion below is vacuous.
        _tmp = REPO / "canonical" / "astra_runtime" / "tmp"
        _tmp.mkdir(parents=True, exist_ok=True)
        self.room = pathlib.Path(tempfile.mkdtemp(prefix="fit_not_words_", dir=_tmp))
        (self.room / "rows.py").write_text(
            "def count_rows(path, delimiter=\",\"):\n"
            "    import csv\n"
            "    with open(path, newline=\"\") as fh:\n"
            "        return {\"rows\": sum(1 for _ in csv.reader(fh, delimiter=delimiter)) - 1}\n",
            encoding="utf-8",
        )
        (self.room / "people.csv").write_text("name,age\nann,31\nbo,24\ncy,45\n", encoding="utf-8")
        (self.room / "notes.md").write_text("# t\n\na\nb\n", encoding="utf-8")
        self._forged: list[str] = []
        self._state = REPO / "canonical" / "runtime" / "state" / "forged_capabilities_v1.json"
        self._before = self._state.read_text(encoding="utf-8") if self._state.is_file() else None

    def tearDown(self) -> None:
        shutil.rmtree(self.room, ignore_errors=True)
        # A test that learns must also forget, and these tests learn: the only honest
        # way to unlearn a forged capability in this tree is to put the state file back
        # as it was found (there is no retire()). Restoring the whole file is stronger
        # than popping the ids, because a refusal may also have been recorded.
        if self._before is None:
            if self._state.is_file():
                self._state.unlink()
        else:
            self._state.write_text(self._before, encoding="utf-8")

    def _forge_rows(self) -> str:
        survey = Census.survey(self.room)
        row = [f for f in survey["functions"] if f["function"] == "count_rows"][0]
        entry = Census.forge_entry(row)
        result = Forge.forge_and_record(
            entry, root=REPO, seed_cases=[{"path": str(self.room / "people.csv")}]
        )
        self.assertTrue(result["admitted"], result.get("checks"))
        self._forged.append(result["capability_id"])
        return result["capability_id"]

    # ---- the two facts that no single threshold could hold at once -------------------

    def test_a_route_that_cannot_consume_the_kind_is_rejected_even_when_it_scores_higher(self) -> None:
        """The pdf failure, reduced: fit decides, and it decides before scoring runs.

        There are two places the contradiction can be caught, and this tree now catches it
        in the earlier one. Measured: the goal says "csv" and names notes.md, so the run is
        REFUSED before any capability is ranked -- the receipt carries no rejected list at
        all, because ranking never happened. That is stronger than eliminating a rival
        after scoring, and it is why no threshold is needed to protect the kind gate.

        The later place still exists and is asserted separately; this test pins the first.
        """
        forged = self._forge_rows()
        notes = str(self.room / "notes.md")
        people = str(self.room / "people.csv")
        # The module-level check, called directly, on the exact question. A forged id can
        # never spell its kind (`forged.rows.count_rows`), so the declaration is passed in
        # on its own -- that separation is the whole repair.
        self.assertTrue(
            Probe.kind_contradiction(forged, goal_paths=(notes,), declared_kinds=["csv"]),
            "a csv tool offered a .md file must contradict",
        )
        self.assertFalse(
            Probe.kind_contradiction(forged, goal_paths=(people,), declared_kinds=["csv"]),
            "the same tool on its own kind must not contradict",
        )
        # .py IS a known kind, so csv-vs-python is a real contradiction -- I asserted the
        # opposite here first and the code corrected me.
        self.assertTrue(
            Probe.kind_contradiction(forged, goal_paths=(str(self.room / "rows.py"),), declared_kinds=["csv"]),
            "csv is not python; that is a genuine contradiction",
        )
        # But not knowing is not contradicting: an unrecognized extension is never a rejection.
        odd = self.room / "blob.zzz"
        odd.write_text("x", encoding="utf-8")
        self.assertFalse(
            Probe.kind_contradiction(forged, goal_paths=(str(odd),), declared_kinds=["csv"]),
            "an extension this tree does not recognize cannot contradict anything",
        )

        # And in a real run: a goal that names csv but points at markdown is refused outright.
        out = Act.act(f"count the rows in the csv {self.room / 'notes.md'}", root=REPO)
        self.assertEqual(out.get("status"), "REFUSED__GOAL_KIND_CONTRADICTS_NAMED_FILE", out)
        self.assertFalse(out.get("executed"), "nothing may execute on a contradiction of kinds")

    def test_the_same_route_is_allowed_when_the_goal_names_its_own_kind(self) -> None:
        """The pair to the test above: the gate must not reject the file it is FOR."""
        forged = self._forge_rows()
        out = Act.act(f"count the rows in the csv {self.room / 'people.csv'}", root=REPO)
        self.assertEqual(out.get("status"), "VERIFIED_ACTION", out.get("detail"))
        self.assertEqual(out.get("capability_id"), forged)
        self.assertEqual((out.get("result") or {}).get("rows"), 3)

    # ---- the guard that was removed, and must stay removed --------------------------

    def test_no_ratio_threshold_suppresses_a_remembered_route(self) -> None:
        """A higher score alone must not make memory yield.

        This is the guard I added and then deleted. It is asserted as an ABSENCE because
        its absence is the fix: with it present, a pdf converter at 36.39 overruled the
        remembered extractor at 28.39 and an honest goal failed. If someone reintroduces a
        score-ratio veto on this path, this test says so by name.
        """
        source = (REPO / "canonical/runtime/grounded_action_v1.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "_MEMORY_OVERRIDE_MIN_GAP",
            source,
            "a raw-score gap veto on remembered routes was measured wrong on two of three "
            "families and was removed; fit is checked instead",
        )
        # And the reason must still be recorded where the decision is made, or the next
        # person re-adds the threshold with the same good intentions.
        self.assertIn("word agreement is not fit", source.lower())

    def test_the_elimination_is_visible_in_the_receipt(self) -> None:
        """A guard that cannot be observed is decoration."""
        self._forge_rows()
        out = Act.act(f"count the rows in the csv {self.room / 'notes.md'}", root=REPO)
        text = json.dumps(out, default=str)
        self.assertIn("GOAL_KIND_CONTRADICTS_NAMED_FILE", text)
        # The receipt must name the file it refused, or a reader cannot tell which of
        # several named paths contradicted.
        self.assertIn("notes.md", text)


if __name__ == "__main__":
    unittest.main()
