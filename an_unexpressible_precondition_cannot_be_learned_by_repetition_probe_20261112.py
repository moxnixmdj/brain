#!/usr/bin/env python3
"""The wall behind "show it once and it learns permanently", measured -- and then repaired.

Two real directories can be IDENTICAL to the sensor and DIFFERENT to the executor. Here one has a
`.docx.intent.json` sidecar beside the document and one does not. Every fact the sensor can express
is the same in both. The real chain succeeds in one and fails `DOCX_INTENT_SIDECAR_MISSING` in the
other. No amount of repetition can learn that, because every run reports the same fact vector.

ARMS
  REPEAT_FOREVER      run the same pair many times. Measures that experience does not help.
  DISCOVER_THEN_LEARN detect the vocabulary gap, discover a suffix observable from the real
                      directories, FALSIFY it on held-out worlds whose document is named
                      differently, then re-record the real outcomes with the new fact included and
                      re-learn.

Every outcome is the real executor's own verified verdict. The held-out worlds are never used to
choose the suffix. Nothing is registered into the sensor: adoption is a governance act, so this
reports what was verified and stops there.

Authority NONE. Writes only inside a temporary directory, redirects the macro store, restores the
repository's own store bytes afterwards.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import chain_v1 as C  # noqa: E402
from canonical.runtime import macro_v1 as MC  # noqa: E402
from canonical.runtime import precondition_discovery_v1 as PD  # noqa: E402
from canonical.runtime import world_probe_v1 as WP  # noqa: E402

GOAL_TEMPLATE = (
    "verify the docx canonical/astra_runtime/tmp/{doc}.docx "
    "and create a tar.gz archive from the manifest"
)
SRC = ROOT / "canonical/astra_runtime/tmp"
DOC = "DOCX_INTENT_VERIFY"


def _world(base: Path, name: str, *, doc: str, sidecar: bool) -> Path:
    root = base / name
    shutil.rmtree(root, ignore_errors=True)
    tmp = root / "canonical/astra_runtime/tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / (doc + ".docx")).write_bytes((SRC / (DOC + ".docx")).read_bytes())
    if sidecar:
        # The sidecar belongs to the document being verified, so a renamed document needs a
        # renamed sidecar. This is what makes the held-out worlds a real test of generality.
        (tmp / (doc + ".docx.intent.json")).write_bytes(
            (SRC / (DOC + ".docx.intent.json")).read_bytes())
    (root / "canonical/manifest.json").write_text('{"records": []}', encoding="utf-8")
    return root


def _run(root: Path, doc: str, *, memory: bool):
    goal = GOAL_TEMPLATE.format(doc=doc)
    clauses = C.decompose(goal)
    facts = C.precondition_context(clauses, root, goal)
    result = C.run(goal, root=root, memory=memory)
    return clauses, (frozenset() if facts is None else frozenset(facts)), result


def main() -> int:
    original = MC.STATE
    saved = original.read_bytes() if original.is_file() else None
    report: dict = {}
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            MC.STATE = base / "macros.json"

            good = _world(base, "with_sidecar", doc=DOC, sidecar=True)
            bad = _world(base, "without_sidecar", doc=DOC, sidecar=False)

            clauses, facts_good, res_good = _run(good, DOC, memory=True)
            _, facts_bad, res_bad = _run(bad, DOC, memory=True)
            key = MC.signature(clauses)

            report["real_outcomes"] = {
                "with_sidecar_ok": bool(res_good["ok"]),
                "without_sidecar_ok": bool(res_bad["ok"]),
                "without_sidecar_error": next(
                    (s.get("error") for s in res_bad["steps"] if s.get("error")), None),
            }
            report["sensed_facts_identical"] = sorted(facts_good) == sorted(facts_bad)
            report["sensed_facts"] = sorted(facts_good)
            report["sidecar_fact_is_undecidable"] = WP.probe_effect(
                "docx.intent_sidecar.available", goal="", goal_paths=(), root=good).get("how")

            # ARM 1 -- repetition. Same two worlds, ten more real runs each way.
            before = MC.applicability(key)
            for _ in range(10):
                _run(good, DOC, memory=True)
                _run(bad, DOC, memory=True)
            after = MC.applicability(key)
            report["repeat_forever"] = {
                "extra_real_runs": 20,
                "status_before": before.status,
                "status_after": after.status,
                "changed": before.status != after.status,
                "evidence_rows": len(MC._evidence_rows(
                    (MC._load().get("macros") or {}).get(key) or {})),
            }

            gap = MC.vocabulary_gap(key)
            report["vocabulary_gap"] = gap
            report["offered_where_it_failed"] = bool(MC.applicable(key, facts_bad))

            # ARM 2 -- discover the missing observable, falsify it, then learn with it.
            ho_good = _world(base, "held_out_renamed_with", doc="RENAMED_ALPHA", sidecar=True)
            ho_bad = _world(base, "held_out_renamed_without", doc="RENAMED_BETA", sidecar=False)
            discovery = PD.discover([good], [bad],
                                    held_out_success=[ho_good], held_out_failure=[ho_bad])
            report["discovery"] = discovery.as_row()

            if discovery.found:
                suffix = discovery.suffix
                # Re-record the SAME real outcomes, now with the discovered observable included.
                MC.STATE = base / "macros_with_new_fact.json"
                rows = []
                for root, doc in ((good, DOC), (bad, DOC), (ho_good, "RENAMED_ALPHA"), (ho_bad, "RENAMED_BETA")):
                    _, facts, result = _run(root, doc, memory=False)
                    augmented = frozenset(facts) | (
                        frozenset({"docx.intent_sidecar.available"}) if PD.holds(root, suffix) else frozenset())
                    if result["ok"]:
                        # The REAL verified steps, not a synthetic stand-in: `record` requires one
                        # verified step per clause and rightly refuses a fabricated plan.
                        MC.record(clauses, result["steps"], context=augmented)
                    else:
                        MC.note_failure(key, context=augmented)
                    rows.append({"world": Path(root).name, "ok": bool(result["ok"]),
                                 "sidecar_observable": PD.holds(root, suffix)})
                report["with_discovered_observable"] = {"rows": rows}
                learned = MC.applicability(key)
                report["with_discovered_observable"].update({
                    "status": learned.status,
                    "required": None if learned.required is None else list(learned.required),
                    "refuses_the_failing_world": not MC.applicable(
                        key, frozenset(facts_bad)),
                    "admits_the_working_world": bool(MC.applicable(
                        key, frozenset(facts_good) | {"docx.intent_sidecar.available"})),
                    "most_general": list(learned.most_general),
                    # Identification is NOT the bar here. The other sensed facts were never absent
                    # in a success, so requirements including them also survive -- genuine
                    # ambiguity that only a further CHOSEN CONTRAST can resolve. Withholding is
                    # sound as soon as G rejects a world, which is exactly what happens.
                    "next_contrast": MC.next_contrast(key).as_row(),
                })
    finally:
        MC.STATE = original
        if saved is not None:
            original.write_bytes(saved)

    learned = report.get("with_discovered_observable", {})
    disc = report.get("discovery", {})
    report["verdict"] = {
        "the_two_worlds_really_differ": (report["real_outcomes"]["with_sidecar_ok"]
                                        and not report["real_outcomes"]["without_sidecar_ok"]),
        "the_sensor_cannot_see_the_difference": report["sensed_facts_identical"],
        "repetition_never_resolves_it": not report["repeat_forever"]["changed"],
        "the_gap_is_detected_and_witnessed": bool(report.get("vocabulary_gap")),
        "the_plan_was_offered_where_it_failed": report["offered_where_it_failed"],
        "an_observable_was_discovered": disc.get("status") == PD.DISCOVERED,
        "it_survived_renamed_held_out_worlds": bool(disc.get("suffix")) and all(
            v["correct"] for v in disc.get("verified_on", [])),
        "it_is_a_kind_not_a_filename": bool(disc.get("suffix")) and DOC.lower() not in disc["suffix"],
        "with_it_the_boundary_scopes_the_plan": "docx.intent_sidecar.available" in (
            learned.get("most_general") or []),
        "further_identification_is_a_named_chosen_query": (
            learned.get("next_contrast", {}).get("status") == "SELECTED__A_REACHABLE_STATE_SPLITS_THE_SURVIVORS"),
        "and_the_failing_world_is_now_refused": bool(learned.get("refuses_the_failing_world")),
        "and_the_working_world_is_still_admitted": bool(learned.get("admits_the_working_world")),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
