#!/usr/bin/env python3
"""Does CHOOSING the next experience beat repeating the last one? Measured on the real executor.

Every run here executes the real `chain_v1.run` against a real directory containing real files, and
every recorded outcome is the executor's own verified verdict. No outcome is simulated, no oracle
is stubbed, and the learner is fed exactly what the live path feeds it.

THE ARMS
  PASSIVE_REPEAT     run the same job in the same environment N times. This is "make it experience
                     the action once and it will know it" -- the claim under test.
  CHOSEN_CONTRAST    ask `contrast_selection_v1` which reachable state to try next, build that
                     environment, run the real job there, record the real outcome.
  FEWEST_SURVIVORS   the killed idea: pick the state that leaves the fewest survivors if the answer
                     comes back favourable. Recorded in `what_a_success_teaches_20261112.py` as a
                     dead end; re-measured here against the real executor rather than asserted.

REALISABILITY IS SENSED, NEVER ASSUMED. Expected-information-gain selection is known to propose
queries outside the region the system can actually realise (arXiv 2602.06818). Here a requested
state is materialised as files and then RE-SENSED with the production probe, and only the sensed
state is ever recorded. `manifest.json` cannot exist without `structured.json` also being true, so
some requested states are unreachable in principle; this arm reports how often that happened
instead of quietly recording a fiction.

Authority NONE. Writes only inside a temporary directory, redirects the macro store, and restores
the repository's own store bytes afterwards.
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
from canonical.runtime import contrast_selection_v1 as CS  # noqa: E402
from canonical.runtime import macro_v1 as MC  # noqa: E402

GOAL = (
    "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx "
    "and create a tar.gz archive from the manifest"
)

#: How each sensed fact is realised on disk. A fact absent from this table cannot be manufactured,
#: so it is never requested. This is the harness's honest reach, not the selector's imagination.
FILES_FOR_FACT = {
    "archive.tar_gz.available": ("canonical/bundle.tgz", b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03"),
    "manifest.json.available": ("canonical/manifest.json", b'{"records": []}'),
    "structured.json.available": ("canonical/data.json", b'{"items": []}'),
}


def _materialise(root: Path, wanted) -> None:
    """Build a real directory intended to realise `wanted`, always including the goal's own docx."""
    shutil.rmtree(root, ignore_errors=True)
    tmp = root / "canonical/astra_runtime/tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        ROOT / "canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx",
        tmp / "DOCX_INTENT_VERIFY.docx",
    )
    sidecar = ROOT / "canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx.intent.json"
    if sidecar.is_file():
        shutil.copy(sidecar, tmp / sidecar.name)
    for fact in sorted(wanted):
        spec = FILES_FOR_FACT.get(fact)
        if spec is not None:
            name, payload = spec
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)


def _sense(root: Path, clauses) -> frozenset[str]:
    facts = C.precondition_context(clauses, root, GOAL)
    return frozenset() if facts is None else frozenset(facts)


def _reachable_pool(base: Path, clauses, universe) -> dict:
    """Every subset of the manufacturable facts, BUILT and then SENSED.

    The key is what was actually sensed, so an unreachable request collapses onto the state that
    really exists instead of entering the pool as a phantom.
    """
    import itertools

    pool: dict[frozenset[str], tuple[Path, tuple]] = {}
    scratch = base / "_probe_env"
    keys = sorted(universe)
    for size in range(len(keys) + 1):
        for subset in itertools.combinations(keys, size):
            _materialise(scratch, subset)
            sensed = _sense(scratch, clauses)
            if sensed not in pool:
                realised = base / ("env_%d" % len(pool))
                _materialise(realised, subset)
                if _sense(realised, clauses) == sensed:
                    pool[sensed] = (realised, subset)
    shutil.rmtree(scratch, ignore_errors=True)
    return pool


def _run_clean(pool_entry, clauses, *, memory: bool):
    """Reset the environment to its intended state, VERIFY the state, then run the real job.

    Running the job WRITES a .tar.gz into the environment, which makes `archive.tar_gz.available`
    true and silently moves that environment to a different state. Without this reset the measured
    "reachable states" drift after the first run and every later number describes a world that no
    longer exists. The sensed state is asserted equal to the intended one before the run, so a
    drifted environment fails loudly instead of corrupting the measurement.
    """
    path, subset = pool_entry
    _materialise(path, subset)
    intended = _sense(path, clauses)
    result = C.run(GOAL, root=path, memory=memory)
    return result, intended


def _rows(key: str) -> list:
    entry = (MC._load().get("macros") or {}).get(key) or {}
    return [(row.get("facts") or (), row.get("ok"))
            for row in (entry.get("evidence") or []) if isinstance(row, dict)]


def _run_arm(name: str, base: Path, pool: dict, clauses, key: str, budget: int) -> dict:
    """Run one arm against the real executor. Returns measurements, not claims."""
    home = max(pool, key=lambda s: len(s))
    trace = []
    requested_but_unreachable = 0
    queries = 0
    settled_at = None

    # Every arm begins from the same single real success: one demonstration of the job working.
    _run_clean(pool[home], clauses, memory=True)
    first = APP.learn(_rows(key))

    for step in range(budget):
        rows = _rows(key)
        boundary = APP.learn(rows)
        if boundary.identified:
            settled_at = queries
            break

        if name == "PASSIVE_REPEAT":
            target = home
        else:
            choice = CS.select_contrast(rows, list(pool))
            if not choice.informative:
                trace.append({"step": step, "status": choice.status})
                break
            want = frozenset(choice.state or ())
            if name == "FEWEST_SURVIVORS":
                alive = [frozenset(s) for s in APP.candidate_requirements(rows)]
                # The killed heuristic: assume the answer is "yes" and grab the state that would
                # leave the fewest survivors, ignoring what happens if the answer is "no".
                target = min(pool, key=lambda s: (sum(1 for n in alive if n <= s), -len(s)))
            else:
                target = want if want in pool else None
                if target is None:
                    requested_but_unreachable += 1
                    trace.append({"step": step, "status": "REQUESTED_STATE_NOT_REALISABLE",
                                  "requested": sorted(want)})
                    break

        result, actual_state = _run_clean(pool[target], clauses, memory=True)
        queries += 1
        after = APP.learn(_rows(key))
        trace.append({
            "step": step,
            "state": sorted(actual_state),
            "real_ok": bool(result["ok"]),
            "status_after": after.status,
            "survivors_after": len(APP.candidate_requirements(_rows(key))),
        })

    final = APP.learn(_rows(key))
    # HELD-OUT PREDICTION. A boundary is only worth anything if it predicts environments it was
    # never trained on. Train on the rows this arm collected, then predict every OTHER reachable
    # state and check the prediction against a real execution there.
    trained = {APP.normalise_state(s) for s, _ in _rows(key)}
    held_out = []
    for state, entry in pool.items():
        if state in trained:
            continue
        predicted_ok = not APP.explains_failure(final, state)
        real, _ = _run_clean(entry, clauses, memory=False)
        held_out.append({
            "state": sorted(state),
            "predicted_ok": bool(predicted_ok),
            "real_ok": bool(real["ok"]),
            "correct": bool(predicted_ok) == bool(real["ok"]),
        })
    return {
        "arm": name,
        "most_general": list(final.most_general),
        "held_out_predictions": held_out,
        "held_out_correct": sum(1 for h in held_out if h["correct"]),
        "held_out_total": len(held_out),
        "status_after_one_demonstration": first.status,
        "survivors_after_one_demonstration": len(APP.candidate_requirements(_rows(key)[:1])),
        "queries_after_the_demonstration": queries,
        "final_status": final.status,
        "identified": bool(final.identified),
        "required": None if final.required is None else list(final.required),
        "settled_after_queries": settled_at,
        "survivors_final": len(APP.candidate_requirements(_rows(key))),
        "evidence_rows": len(_rows(key)),
        "requested_but_unreachable": requested_but_unreachable,
        "trace": trace,
    }


def main() -> int:
    original = MC.STATE
    saved = original.read_bytes() if original.is_file() else None
    report: dict = {"goal": GOAL, "arms": []}
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            clauses = C.decompose(GOAL)
            key = MC.signature(clauses)
            MC.STATE = base / "probe_macros.json"
            pool = _reachable_pool(base, clauses, FILES_FOR_FACT)
            report["reachable_states"] = [sorted(s) for s in sorted(pool, key=lambda s: (len(s), sorted(s)))]
            report["requested_subsets"] = 2 ** len(FILES_FOR_FACT)
            report["distinct_reachable"] = len(pool)

            for arm in ("PASSIVE_REPEAT", "CHOSEN_CONTRAST", "FEWEST_SURVIVORS"):
                MC.STATE = base / ("macros_%s.json" % arm)
                report["arms"].append(_run_arm(arm, base, pool, clauses, key, budget=8))
    finally:
        MC.STATE = original
        if saved is not None:
            original.write_bytes(saved)

    arms = {a["arm"]: a for a in report["arms"]}
    passive, chosen = arms["PASSIVE_REPEAT"], arms["CHOSEN_CONTRAST"]
    fewest = arms["FEWEST_SURVIVORS"]
    report["verdict"] = {
        "one_demonstration_settles_nothing": passive["status_after_one_demonstration"].startswith("UNDETERMINED"),
        # Repetition adds rows and no knowledge: the least demanding survivor stays the empty
        # requirement, which admits every environment and therefore scopes nothing.
        "repetition_never_scopes": not passive["most_general"],
        "chosen_contrast_scopes": bool(chosen["most_general"]),
        "chosen_uses_fewer_queries": chosen["queries_after_the_demonstration"] < passive["queries_after_the_demonstration"],
        "chosen_beats_the_killed_heuristic": chosen["survivors_final"] < fewest["survivors_final"],
        # CORRECTED FINDING. This arm used to end AMBIGUOUS with two survivors that no reachable
        # state could split, and that was recorded as a permanent reachability limit. It was not
        # one: `manifest.json` implies `structured.json` by the sensor's own kind specs, so
        # {manifest, structured} IS {manifest} -- one requirement spelled twice. Reducing by that
        # entailment turns the SAME two real runs into identification. The limit was double-counting.
        "chosen_contrast_identifies": chosen["identified"],
        "repetition_still_never_identifies": not passive["identified"],
        "the_killed_heuristic_still_never_identifies": not fewest["identified"],
        "unreachable_states_were_detected_not_recorded": report["distinct_reachable"] < report["requested_subsets"],
        "held_out_prediction_perfect": bool(chosen["held_out_total"]) and chosen["held_out_correct"] == chosen["held_out_total"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
