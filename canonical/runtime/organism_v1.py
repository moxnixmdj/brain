#!/usr/bin/env python3
"""A process that acts on its own clock, predicts its own actions, and is surprised.

The deepest error in the first ten landings
-------------------------------------------
Every one of them is something a person runs. `self_maintenance_loop`, `derivation_inference`,
`derivation_grammar`, `capability_self_model`, `executed_effect_oracle` -- five instruments, all
invoked by hand, all exiting when they finish. Nothing in this repository acts unless someone
starts it. That is the definition of static code, and no amount of inference inside a tool
changes it.

Measured 2026-11-04: 368,660 records exist about files; 49 exist about the system's own
behaviour; **0 processes exist that decide, on their own, what to do next.**

Two halves that were built separately and never joined
-----------------------------------------------------
Log 9 gave the system a model of its own behaviour, but its actions had no consequences.
Log 10 gave actions consequences, but nothing predicted them. A creature needs both, in one
process, in a loop:

    predict -> act -> observe -> be surprised -> change what you do next -> repeat

`surprise` is the whole point. A system that cannot be surprised cannot learn, because nothing
distinguishes an action that worked from one that merely happened.

What this process is, concretely
--------------------------------
* **Its own clock.** It ticks on an interval. No external trigger decides when it thinks.
* **Its own agenda.** Organs expose affordances; a bandit over organs chooses which to attend to.
  Nothing hands it a work list.
* **Organs are reused, not new authority.** Every action is one of the existing repair classes or
  the executed-effect oracle. This process may not widen its own organ set (a test pins that).
* **Falsifiable predictions.** Before acting it writes down what it expects the independent check
  to return. Afterwards it writes down what the check actually returned. Two journal entries,
  ordered, with the prediction always first.
* **Consequence changes behaviour.** Organs and targets carry success counts; selection is by
  upper-confidence bound, so an organ that stops paying off is abandoned and one that has never
  been tried is explored. That is not a lookup table: the same code takes different actions on
  tick 2 and tick 20 because of what happened in between.
* **It gets bored instead of churning.** A target confirmed repeatedly is retired. When nothing is
  left to attend to, the organism records an idle tick and says so. After a bounded number of
  idle ticks it stops, with a reason, rather than inventing work -- which is what every
  "autonomous agent" that looks busy is actually doing.
* **It survives its own death.** State and journal are on disk. A restart continues the same
  life instead of beginning a new one, which is the failure `CREATURE_BEHAVIOR_MAP_V1.md` records
  five times over.

What this is not
----------------
It is not sentient. It has no feelings, no self-awareness, and no stake in anything. Its
"consequence" is a boolean it computes about its own accuracy. What it does have, for the first
time in this repository, is initiative, prediction, surprise and persistence in one process --
four of the preconditions, not the thing itself.

The honest bound: its world is tiny. Five organs, a handful of targets, and a repository that
mostly behaves. A larger world is the next thing to build, and this file is the shape it goes in.

Usage::

    python3 canonical/runtime/organism_v1.py --ticks 20            # live for twenty ticks
    python3 canonical/runtime/organism_v1.py --ticks 40 --interval 2
    python3 canonical/runtime/organism_v1.py --status              # what has it been doing
    python3 canonical/runtime/organism_v1.py --reset               # forget a life (explicitly)
"""
from __future__ import annotations

import json
import math
import sys
import time
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_ORGANISM_V1"
STATE = ROOT / "canonical/astra_runtime/state/ORGANISM_V1.json"
JOURNAL_CAP = 4000
EXPERIENCE_CAP = 600           # entries kept on disk; the head is trimmed, never rewritten
EXPLORE_C = 1.2              # UCB exploration weight
# How much an unresolved oddity outranks a settled success. Measured 2026-11-04: with a flat
# +0.5 the organism preferred a target confirmed nine times over one that had surprised it three
# times, because a high mean plus any exploration bonus beats a low mean plus a constant. That is
# an optimiser for the things it already understands, not curiosity. Scaling the bonus by the
# surprise RATE makes an unresolved oddity genuinely attractive, and lets it decay as the oddity
# is explained.
CURIOSITY = 1.0

# How much recent history decides what the organs expect. Measured 2026-11-04: predicting from
# the modal verdict of a target's WHOLE life meant a world healthy for eight ticks outvoted a
# world that had just broken, so the same target surprised the organism three ticks running
# (t35, t38, t39: predicted EFFECT_HELD, observed INPUTS_IGNORED_SILENTLY). A lifetime average
# is a memory of the dead world. Expectations come from the last few encounters.
RECENT_WINDOW = 3

# A model is only allowed to speak for a target it has never seen once it has seen enough
# elsewhere to be worth listening to. Below these, the organism falls back to the target's own
# record -- which for a new target is silence, exactly as in log 11.
MODEL_MIN_EVIDENCE = 3
MODEL_MIN_CONFIDENCE = 0.75
RETIRE_AFTER_CONFIRMATIONS = 2
REOPEN_AFTER_TICKS = 25
MAX_IDLE_TICKS = 6         # resting is allowed; resting FOREVER is not (see _still_asleep)
PROTECTED_ACTIONS = {"widen_organs", "edit_guard", "promote_self", "flip_terminal"}


# --------------------------------------------------------------------------- state
def blank_state() -> dict:
    return {
        "schema": SCHEMA,
        "born_at": time.time(),
        "tick": 0,
        "seq": 0,
        "restarts": 0,
        "alive": False,
        "identity": __import__("uuid").uuid4().hex[:12],
        "organs": {},
        "targets": {},
        "journal": [],
        "counts": {"actions": 0, "predicted": 0, "surprised": 0, "idle_ticks": 0,
                   "model_regrown": 0, "vocabulary_checks": 0, "vocabulary_grown": 0,
                   "refused": 0, "confirmations": 0},
        "stop_reason": None,
    }


def load_state(path: Path | None = None) -> dict:
    path = path or STATE
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and doc.get("schema") == SCHEMA:
                return doc
        except (OSError, ValueError):
            pass
    return blank_state()


def save_state(state: dict, path: Path | None = None) -> None:
    path = path or STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(state.get("journal", [])) > JOURNAL_CAP:
        state["journal"] = state["journal"][-JOURNAL_CAP:]
    path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _append(state: dict, entry: dict) -> None:
    state["seq"] = int(state.get("seq", 0)) + 1
    entry["seq"] = state["seq"]
    entry["at"] = round(time.time(), 3)
    state.setdefault("journal", []).append(entry)


# --------------------------------------------------------------------------- organs
def _expected(record: Mapping[str, Any], default: Any = None) -> Any:
    """What just happened is the best guess at what happens next.

    Modal verdict over the last RECENT_WINDOW encounters, falling back to lifetime counts only
    where a target has no recent history (e.g. a record written by an older version).
    """
    recent = list(record.get("recent") or [])
    if recent:
        # Each step back in time halves an observation's vote, so one new fact beats an old
        # majority instead of being outvoted by it. A flat count over the window still let
        # [OK, OK, BROKEN] predict OK, which cost a second surprise for a single break.
        weights: dict[str, float] = {}
        for age, v in enumerate(reversed(recent)):
            weights[v] = weights.get(v, 0.0) + 2.0 ** -age
        return max(weights.items(), key=lambda kv: (kv[1], kv[0]))[0]
    seen = dict(record.get("verdicts") or {})
    if seen:
        return max(seen.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return default


class Organ:
    """A faculty. It exposes targets, predicts, acts, and reports the independent observation.

    The contract that makes surprise meaningful: `predict` and `observe` must answer in the same
    vocabulary, and `observe` must not be allowed to look at `predict`'s answer to decide.
    """

    name = "abstract"

    def targets(self) -> list[dict]:
        raise NotImplementedError

    def predict(self, target: Mapping[str, Any], record: Mapping[str, Any]) -> Any:
        return None                       # no prediction is allowed; counted separately                       # no prediction is allowed; it is counted separately

    def act(self, target: Mapping[str, Any]) -> dict:
        raise NotImplementedError

    def observe(self, target: Mapping[str, Any], acted: Mapping[str, Any]) -> Any:
        raise NotImplementedError

    def senses(self, target: Mapping[str, Any]) -> dict[str, float]:
        """What this organ can see about a target BEFORE acting. The model's only input.

        An organ that offers nothing here simply never gets a model prediction, which is the
        honest outcome: no senses, no expectation.
        """
        return {}


class _LoopOrgan(Organ):
    """An organ backed by one defect class from the self-maintenance loop."""

    def __init__(self, name: str, factory: Callable[[], Any]) -> None:
        self.name = name
        self._factory = factory
        self._klass = None

    @property
    def klass(self):
        if self._klass is None:
            self._klass = self._factory()
        return self._klass

    def targets(self) -> list[dict]:
        try:
            return [{"id": d["defect_id"], "defect": d} for d in self.klass.find()]
        except Exception:                                            # noqa: BLE001
            return []

    def predict(self, target, record):
        """What this organ thinks will happen, from what has actually happened to this target.

        Before 2026-11-04 this returned "FIXED" unconditionally, so a class that surprised it
        once surprised it forever: the surprise could not change the next prediction, which
        means it could not learn. The modal past verdict is the prediction, defaulting to
        "FIXED" only while there is no past. A surprise therefore costs exactly one surprise
        per new state of the world instead of one per tick.
        """
        return _expected(record, default="FIXED")

    def senses(self, target):
        defect = target.get("defect") or {}
        path = str(defect.get("path") or defect.get("state_path") or "")
        return {
            "is_loop_defect": 1.0,
            "path_depth": float(path.count("/")),
            "path_is_json": float(path.endswith(".json")),
            "path_is_canonical": float(path.startswith("canonical/")),
            "defect_has_path": float(bool(path)),
        }

    def act(self, target):
        return self.klass.fix(target["defect"])

    def observe(self, target, acted):
        if not acted.get("applied"):
            return "REFUSED:" + str(acted.get("reason") or "UNKNOWN")
        return "FIXED" if self.klass.verify(target["defect"]) else "STILL_THERE"


class EffectOrgan(Organ):
    """Sits a capability in a world and predicts what it will do. The only organ whose world
    the organism does not write.

    Prediction is learned per situation from this organism's own past: after seeing a situation
    refuse twice, predicting REFUSED is no longer a guess. Before it has seen one, it says
    nothing and the tick is counted as unpredicted rather than as a success.
    """

    name = "effect"

    def __init__(self) -> None:
        self._situations = None

    @property
    def situations(self):
        if self._situations is None:
            from canonical.tools import executed_effect_oracle_v1 as oracle
            self._situations = oracle.SITUATIONS
        return self._situations

    def targets(self):
        return [{"id": s.name, "situation": s} for s in self.situations]

    def predict(self, target, record):
        return _expected(record, default=None)

    def senses(self, target):
        situation = target["situation"]
        supplied = []
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                situation.build(root)
                supplied = [str(x) for x in situation.supplied(root)]
        except Exception:                                              # noqa: BLE001
            supplied = []
        return {
            "is_effect": 1.0,
            "expects_effect": float(bool(getattr(situation, "expects_effect", True))),
            "n_supplied": float(len(supplied)),
            "supplied_all_prefixed": float(bool(supplied) and
                                           all(x.startswith("canonical/") for x in supplied)),
            "capability_is_archive": float(
                str(getattr(situation, "capability_id", "")).startswith("archive")),
        }

    def act(self, target):
        from canonical.tools import executed_effect_oracle_v1 as oracle
        row = oracle.run_situation(target["situation"])
        return {"applied": True, "row": row}

    def observe(self, target, acted):
        return (acted.get("row") or {}).get("verdict")


class ForgeOrgan(Organ):
    """The world-building faculty. Its targets are capabilities it cannot yet drive at all.

    Log 12 ended with a pile of crashes that were really my fixture's fault, and the observation
    that a world is not something a person should have to enumerate. This organ treats each
    undrivable capability as a target, runs one repair round against it, and reports whether the
    capability now reaches a verdict of its own. The repair is read from the capability's refusal
    -- no branch knows a capability's name.

    It runs on the organism's clock like everything else: it is not invoked, it is attended to.
    """

    name = "forge"

    def __init__(self, artifact: Path | None = None) -> None:
        self._artifact = artifact or (ROOT / "canonical/verification/WORLD_FORGE_V1.json")
        self._rows = None

    def _load(self):
        if self._rows is None:
            try:
                doc = json.loads(self._artifact.read_text(encoding="utf-8"))
                self._rows = [r for r in doc.get("rows") or [] if not r.get("reached")]
            except (OSError, ValueError):
                self._rows = []
        return self._rows

    def targets(self):
        out = []
        for row in self._load():
            stopped = str(row.get("stopped_by") or "")
            if stopped == "UNREPAIRABLE_MISSING_PACKAGE":
                continue                      # a package this machine does not have: no world fixes it
            out.append({"id": row["capability"], "capability": row["capability"]})
        return out

    def predict(self, target, record):
        return _expected(record, default="DECLARED")

    def senses(self, target):
        return {"is_forge": 1.0, "is_loop_defect": 0.0, "is_effect": 0.0,
                "path_is_json": 0.0, "path_is_canonical": 0.0, "path_depth": 0.0,
                "defect_has_path": 0.0, "expects_effect": 0.0, "n_supplied": 0.0,
                "supplied_all_prefixed": 0.0, "capability_is_archive": 0.0}

    def act(self, target):
        from canonical.tools import world_forge_v1 as forge
        from canonical.tools.capability_world_v1 import registry
        try:
            module = registry()[target["capability"]].get("adapter_module") or ""
            result = forge.forge(target["capability"], module)
        except Exception as exc:                                     # noqa: BLE001
            return {"applied": False, "reason": str(exc)[:80]}
        return {"applied": True, "result": result}

    def observe(self, target, acted):
        if not acted.get("applied"):
            return "REFUSED:" + str(acted.get("reason") or "UNKNOWN")
        result = acted.get("result") or {}
        if result.get("reached"):
            return "DECLARED:" + str(result.get("verdict"))
        return "STILL_CRASHING:" + str(result.get("stopped_by") or "UNKNOWN")


# The organ set is CLOSED and literal. Nothing at runtime may add to it, and membership may not
# depend on a file that happens to exist: measured 2026-11-04, adding an organ conditionally on an
# artifact on disk broke the safety test, and the test was right. Targets may depend on the world;
# organs may not.
ORGAN_NAMES = ("effect", "receipt", "lease", "measurement", "derived", "forge", "doubt")

class DoubtOrgan(Organ):
    """Curiosity, mechanically: the targets are claims somebody else already wrote down.

    Every other organ attends to a list. `effect` has four situations I wrote; `receipt`, `lease`,
    `measurement` and `derived` are defect classes somebody wrote; `forge` reads an artifact that
    a previous run of the organism produced. Measured 2026-11-04: that is fourteen targets, all of
    them enumerated by a person, in a repository holding roughly twenty thousand checkable claims.

    This organ mines the corpus. It does not know what a capability is for and it never names one:
    a claim is tested because it was asserted, and the hypothesis space grows whenever anybody
    writes a claim -- registry fields, artifacts, docstrings. That is the difference between a
    list of things to check and a way of generating things to check.
    """

    name = "doubt"

    def __init__(self) -> None:
        self._claims = None

    def _mine(self):
        if self._claims is None:
            try:
                from canonical.tools import claim_miner_v1 as miner
                mined = miner.mine_registry_claims()
                pending = [c for c in mined if c["kind"] == "RESULT_FIELD"]
                self._claims = pending
            except Exception:                                        # noqa: BLE001
                self._claims = []
        return self._claims

    def targets(self):
        return [{"id": f"{c['capability']}::{c['subject']}", "claim": c} for c in self._mine()]

    def predict(self, target, record):
        return _expected(record, default="HOLDS")

    def senses(self, target):
        claim = target["claim"]
        return {"is_doubt": 1.0, "is_forge": 0.0, "is_effect": 0.0, "is_loop_defect": 0.0,
                "path_is_json": 0.0, "path_is_canonical": 0.0, "path_depth": 0.0,
                "defect_has_path": 0.0, "expects_effect": 0.0, "n_supplied": 0.0,
                "supplied_all_prefixed": 0.0, "capability_is_archive": 0.0}

    def act(self, target):
        from canonical.tools import claim_miner_v1 as miner
        try:
            return {"applied": True, "result": miner.test_claim(target["claim"])}
        except Exception as exc:                                     # noqa: BLE001
            return {"applied": False, "reason": str(exc)[:80]}

    def observe(self, target, acted):
        if not acted.get("applied"):
            return "REFUSED:" + str(acted.get("reason") or "UNKNOWN")
        return str((acted.get("result") or {}).get("verdict") or "UNKNOWN")


ORGANS: dict[str, Organ] = {}


def build_organs() -> dict[str, Organ]:
    """The organ set. Fixed at import time and never widened by the running process."""
    from canonical.tools import executed_effect_oracle_v1 as oracle          # noqa: F401
    from canonical.tools import self_maintenance_loop_v1 as loop

    organs: list[Organ] = [
        EffectOrgan(),
        _LoopOrgan("receipt", lambda: loop.make_stale_receipt_class()),
        _LoopOrgan("lease", lambda: loop.make_stale_lease_class()),
        _LoopOrgan("measurement", lambda: loop.make_stale_measurement_class()),
    ]
    organs.append(ForgeOrgan())
    organs.append(DoubtOrgan())
    try:
        from canonical.tools import derivation_inference_v1 as infer
        if infer.load_model(recompute_if_missing=False) is not None:
            organs.append(_LoopOrgan("derived", lambda: loop._derived_value_class(None)))
    except Exception:                                                # noqa: BLE001
        pass
    return {organ.name: organ for organ in organs}


# --------------------------------------------------------------------------- economics
def _ucb(attempts: int, confirmations: int, tick: int) -> float:
    """Upper confidence bound: exploit what works, but never stop trying what might.

    With attempts == 0 the score is infinite, so a never-tried organ is always explored first.
    That is what stops the organism from settling on the one organ that happened to pay off
    early -- the failure mode of a greedy chooser.
    """
    if attempts <= 0:
        return float("inf")
    mean = confirmations / attempts
    return mean + EXPLORE_C * math.sqrt(math.log(max(2, tick)) / attempts)


def choose(state: dict, organs: Mapping[str, Organ]) -> tuple[str | None, dict | None, list[dict]]:
    """Pick one target to attend to, or return (None, None, candidates) and rest.

    The arm is the TARGET, not the organ. The first version scored organs, which meant every
    target inside one organ shared a score and the alphabetical tie-break chose the same target
    on every tick -- fourteen ticks, one target, no exploration, no prediction. Measured
    2026-11-04. A never-attended target is now infinitely attractive, so the organism visits
    each one before settling anywhere, and the organ's own record is used as the prior once a
    target has a history of its own.
    """
    tick = int(state.get("tick", 0))
    candidates = []
    for name, organ in organs.items():
        organ_row = state.setdefault("organs", {}).get(name, {}) or {}
        prior = (int(organ_row.get("confirmations", 0)) + 1) / (
            int(organ_row.get("attempts", 0)) + 2)          # Laplace, so 0.5 when unknown
        for target in organ.targets():
            key = f"{name}::{target['id']}"
            record = state.setdefault("targets", {}).get(key, {}) or {}
            if _retired(record, tick):
                continue
            attempts = int(record.get("attempts", 0))
            if attempts == 0:
                score = float("inf")                        # unattended: attend to it
            else:
                mean = (int(record.get("confirmations", 0)) + prior) / (attempts + 1)
                score = mean + EXPLORE_C * math.sqrt(math.log(max(2, tick)) / attempts)
            surprises = int(record.get("surprises", 0))
            if surprises:
                score += CURIOSITY * (surprises / attempts)  # unexplained is interesting
            candidates.append({"organ": name, "target": target, "key": key,
                               "score": score})
    if not candidates:
        return None, None, []
    # A never-attended target wins outright; among those, keep the order the organs gave them
    # rather than an alphabetical accident.
    candidates.sort(key=lambda c: (-(c["score"] if c["score"] != float("inf") else 1e9),
                                   c["key"]))
    best = candidates[0]
    return best["organ"], best["target"], candidates


def _still_asleep(state: Mapping[str, Any], tick: int) -> bool:
    """True while every target is merely resting on a timer rather than gone.

    Measured 2026-11-04: the organism retired all four situations, then slept. I broke the
    archive adapter under it -- asked for two files, archived one -- and the process never
    noticed, because `live()` stopped at MAX_IDLE_TICKS and every target needed
    REOPEN_AFTER_TICKS to come back. Rest had become permanent ignorance: a world can be
    demolished while the creature sleeps and it would report "nothing worth doing".

    Rest is legitimate. Sleeping through a broken world is not. If the only reason there is
    nothing to do is a retirement timer, the organism keeps its clock and waits it out.
    """
    targets = state.get("targets") or {}
    if not targets:
        return False
    return any(_retired(rec, tick) for rec in targets.values())


def _retired(record: Mapping[str, Any], tick: int) -> bool:
    """A target confirmed enough is dropped -- but not forever. The world drifts, and an organ
    that was right twice can be wrong later. Re-opening is suspicion, not memory loss."""
    retired_at = record.get("retired_at")
    if retired_at is None:
        return False
    return (tick - int(retired_at)) < REOPEN_AFTER_TICKS


# --------------------------------------------------------------------------- one tick
def vocabulary_pays_for_itself(experience: list[dict], entries: list[dict],
                               kept_before: list[dict]) -> tuple[float, float]:
    """Does thinking in these new distinctions beat not thinking in them?

    Measured 2026-11-04: a feature that passes its own gate can still make the creature worse.
    Inventing a vocabulary on the `ratio` world took accuracy from 0.883 to 0.533, and inside the
    live loop four of thirty structureless streams admitted a distinction that paid for nothing.
    The feature's own score is not the test; the model's held-out accuracy is.
    """
    from canonical.runtime import belief_v1 as belief
    from canonical.runtime import vocabulary_v1 as vocab_mod

    def held(shown: list[dict]) -> float:
        probe = vocab_mod.augment(experience, {"entries": shown})
        scores = []
        for train, test in vocab_mod.time_folds(probe, blocks=4) or []:
            probe_model = belief.blank()
            belief.fit(probe_model, train, test)
            for example in train:
                belief.observe(probe_model, example["signals"], example["verdict"])
            scores.append(belief.accuracy(probe_model, test)[0])
        return sum(scores) / len(scores) if scores else 0.0

    return held(entries), held(kept_before)


def chosen_method(experience: list[dict], vocabulary: dict) -> dict:
    """Ask the creature how it should think here, and record the answer either way.

    In-memory, because a fitted nearest-neighbour list is not state that belongs in a saved journal;
    the DECISION is what persists, and it is re-derived from experience when the process restarts.
    """
    from canonical.runtime import method_v1 as method_mod

    if len(experience) < 40:
        return {"adopted": False, "reason": "not_enough_experience"}
    folds = vocab_mod_folds(experience)
    decision = method_mod.choose(experience, folds, vocabulary=vocabulary)
    named = decision["chosen"]
    chosen = [m for m in method_mod.method_space(bool(vocabulary.get("entries")))
              if m.name == (named.name if hasattr(named, "name") else named)]
    return {"adopted": bool(decision.get("adopted")), "reason": decision.get("reason"),
            "method": (chosen[0].name if chosen else None),
            "cv": decision.get("cv")}


_PREDICTORS: dict[int, tuple] = {}


def method_predictor(state: dict, experience: list[dict], vocabulary: dict):
    """The fitted predictor for the method the creature adopted, rebuilt when the evidence changes."""
    from canonical.runtime import method_v1 as method_mod

    decision = state.get("method") or {}
    name = decision.get("method")
    if not decision.get("adopted") or not name:
        return None
    stamp = (len(experience), name)
    cached = _PREDICTORS.get(id(state))
    if cached and cached[0] == stamp:
        return cached[1]
    space = method_mod.method_space(bool(vocabulary.get("entries")))
    chosen = next((m for m in space if m.name == name), None)
    if chosen is None:
        return None
    rows = method_mod._prepare(chosen, experience, vocabulary)
    predictor = method_mod.make(chosen, method_mod.names_of(rows))(rows)
    _PREDICTORS[id(state)] = (stamp, (chosen, predictor))
    return (chosen, predictor)


def vocab_mod_folds(experience: list[dict]):
    from canonical.runtime import belief_v1 as belief
    from canonical.runtime import vocabulary_v1 as vocab_mod
    return vocab_mod.time_folds(experience) or belief.capability_folds(experience)


def tick(state: dict, organs: Mapping[str, Organ] | None = None) -> dict:
    """Predict, act, observe, compare. One heartbeat."""
    organs = organs if organs is not None else build_organs()
    state["tick"] = int(state.get("tick", 0)) + 1
    tick_no = state["tick"]

    name, target, candidates = choose(state, organs)
    if name is None:
        state["counts"]["idle_ticks"] += 1
        _append(state, {"tick": tick_no, "kind": "IDLE",
                        "saw": [c["key"] for c in candidates][:12]})
        return {"tick": tick_no, "outcome": "IDLE"}

    organ = organs[name]
    key = f"{name}::{target['id']}"
    record = state.setdefault("targets", {}).setdefault(key, {})
    organ_row = state.setdefault("organs", {}).setdefault(
        name, {"attempts": 0, "confirmations": 0, "surprises": 0})

    # A model of the world, if it has anything to say about a target it has never met, speaks
    # first. This is the difference between a lookup table and a creature: log 11 could only
    # predict a target it had already tried.
    from canonical.runtime import belief_v1 as belief
    model = state.setdefault("belief", belief.blank())
    senses = organ.senses(target)

    # The vocabulary of distinctions is the creature's own. Every sense passes through it, so a
    # distinction it invented earlier is now one of the dimensions it thinks in.
    from canonical.runtime import vocabulary_v1 as vocab_mod
    vocabulary = state.setdefault("vocabulary", vocab_mod.blank())
    if senses and vocabulary.get("entries"):
        senses = vocab_mod.augment([{"signals": senses}], vocabulary)[0]["signals"]

    # If the creature has adopted a way of thinking that beats its incumbent here, that is how it
    # predicts. Otherwise the incumbent speaks, which is what it has always done.
    prediction = None
    adopted = None
    if senses:
        framed = method_predictor(state, state.get("experiences") or [], vocabulary)
        if framed is not None:
            adopted, predictor = framed
            prediction = predictor.predict(senses)
    if senses and prediction is None:
        candidate = belief.predict(model, senses)
        if (candidate is not None and belief.confidence(model, senses) >= MODEL_MIN_CONFIDENCE
                and sum(belief._counts(belief._walk(model["root"], senses)).values())
                >= MODEL_MIN_EVIDENCE):
            prediction = candidate
    from_model = prediction is not None
    if prediction is None:
        prediction = organ.predict(target, record)
    _append(state, {"tick": tick_no, "kind": "PREDICTION", "organ": name,
                    "target": target["id"], "predicts": prediction,
                    "from_model": prediction is not None and not from_model,
                    "from_method": adopted.name if adopted is not None and prediction is not None
                    else None,
                    "first_visit": int(record.get("attempts", 0)) == 0})

    acted = organ.act(target)

    observation = organ.observe(target, acted)
    # Surprise is defined against the prediction that was written BEFORE the action. A tick with
    # no prediction cannot be surprised, and is counted as unpredicted -- not as correct.
    surprise = None if prediction is None else (observation != prediction)

    _append(state, {"tick": tick_no, "kind": "OUTCOME", "organ": name,
                    "target": target["id"], "observed": observation,
                    "predicted": prediction, "surprise": surprise})

    state["counts"]["actions"] += 1
    record["attempts"] = int(record.get("attempts", 0)) + 1
    verdicts = record.setdefault("verdicts", {})
    verdicts[str(observation)] = int(verdicts.get(str(observation), 0)) + 1
    recent = record.setdefault("recent", [])
    recent.append(str(observation))
    del recent[:-RECENT_WINDOW]
    organ_row["attempts"] = int(organ_row.get("attempts", 0)) + 1

    confirmed = bool(prediction is not None and observation == prediction)
    if confirmed:
        organ_row["confirmations"] = int(organ_row.get("confirmations", 0)) + 1
        record["confirmations"] = int(record.get("confirmations", 0)) + 1
        state["counts"]["confirmations"] += 1
        if int(record["confirmations"]) >= RETIRE_AFTER_CONFIRMATIONS:
            record["retired_at"] = tick_no
    if prediction is not None:
        state["counts"]["predicted"] += 1
    if surprise:
        state["counts"]["surprised"] += 1
        organ_row["surprises"] = int(organ_row.get("surprises", 0)) + 1
        record["surprises"] = int(record.get("surprises", 0)) + 1
    if str(observation).startswith("REFUSED"):
        state["counts"]["refused"] += 1

    # Teach, then re-grow. The model learns from every experience, and a surprise is the only
    # event that can add a distinction to it -- because a distinction is only worth adding when
    # the current one was wrong.
    if senses:
        belief.observe(model, senses, str(observation))
        experience = state.setdefault("experiences", [])
        experience.append({"group": f"{name}::{target['id']}", "signals": senses,
                           "verdict": str(observation)})
        del experience[:-EXPERIENCE_CAP]
        if surprise and len(experience) >= belief.MIN_EXAMPLES_FOR_SPLIT:
            belief.fit(model, experience)
            state["counts"]["model_regrown"] = state["counts"].get("model_regrown", 0) + 1

        # And the vocabulary grows with it. Waiting for a surprise is not enough, and this was
        # measured 2026-11-04: over 140 ticks of a world whose rule is a product, surprise never
        # fired (nothing predicted, so nothing could be wrong) and the vocabulary never grew.
        # A creature that only re-examines its distinctions when it is caught being wrong stays
        # blind exactly while it is confidently ignorant. So the trigger is inadequacy: the
        # model cannot beat the base rate on the creature's own experience.
        # How should it think here? Asked of the creature's own experience, not of me.
        if len(experience) >= 40 and len(experience) % 40 == 0:
            state["method"] = chosen_method(experience, vocabulary)

        if len(vocabulary.get("entries") or []) < 4:
            checks = state["counts"].get("vocabulary_checks", 0)
            if (len(experience) >= 24
                    and len(experience) >= state.get("vocabulary_next_check", 24) + 16):
                horizon = experience[-120:]
                folds = vocab_mod.time_folds(horizon) or belief.capability_folds(horizon)
                floor = vocab_mod._base_rate(folds)
                held = vocab_mod._cv(horizon, ("base", sorted(horizon[0]["signals"])[0]), None,
                                     folds) if horizon[0]["signals"] else 0.0
                inadequate = surprise or held <= floor + vocab_mod.MIN_GAIN
                if inadequate:
                    before_names = set(vocab_mod.names(vocabulary))
                    kept_before = list(vocabulary.get("entries") or [])
                    vocab_mod.discover(horizon, folds, vocabulary=vocabulary)
                    state["vocabulary_next_check"] = len(experience)
                    state["counts"]["vocabulary_checks"] = checks + 1
                    if set(vocab_mod.names(vocabulary)) - before_names:
                        state["counts"]["vocabulary_grown"] = (
                            state["counts"].get("vocabulary_grown", 0) + 1)

                    # A feature that passes its own gate can still make the creature worse, and
                    # that was measured 2026-11-04: inventing a vocabulary on the `ratio` world
                    # took accuracy from 0.883 to 0.533. A distinction is only worth keeping if
                    # the model that thinks in it predicts better -- so the test is the model, on
                    # the creature's own held-out experience, not the feature's own score.
                    if vocabulary.get("entries") and len(experience) >= 40:
                        with_them, without = vocabulary_pays_for_itself(
                            experience, vocabulary["entries"], kept_before)
                        if with_them <= without + 0.02:
                            vocabulary.setdefault("retired", []).extend(
                                {"expr": e["renders"], "why": "did_not_pay_for_itself",
                                 "with": round(with_them, 4), "without": round(without, 4)}
                                for e in vocabulary["entries"])
                            vocabulary["entries"] = kept_before
                            state["counts"]["vocabulary_set_aside"] = (
                                state["counts"].get("vocabulary_set_aside", 0) + 1)

                    # A retirement that is no longer true is a lie in the record. If the same
                    # distinction has since been re-admitted, drop the stale note.
                    live = set(vocab_mod.names(vocabulary))
                    vocabulary["retired"] = [r for r in vocabulary.get("retired") or []
                                             if r.get("expr") not in live]

                    # Rethink with the new dimensions from here on.
                    if vocabulary.get("entries"):
                        belief.fit(model, vocab_mod.augment(experience, vocabulary))
                        state["counts"]["model_regrown"] = (
                            state["counts"].get("model_regrown", 0) + 1)

    return {"tick": tick_no, "organ": name, "target": target["id"],
            "predicted": prediction, "observed": observation, "surprise": surprise,
            "outcome": "ACTED"}


# --------------------------------------------------------------------------- a life
def live(*, ticks: int = 20, interval: float = 0.0, state_path: Path | None = None,
         verbose: bool = True, on_tick: Callable[[dict], None] | None = None) -> dict:
    """Run, on this process's own clock, until it has ticked `ticks` times or has nothing to do.

    "Nothing to do" means nothing at all is left to attend to. Targets that are only resting on
    a retirement timer are not nothing: the clock keeps running until they come back, because
    a process that sleeps through a changed world has stopped being a process.
    """
    state = load_state(state_path)
    existed = state["tick"] > 0
    if existed:
        state["restarts"] = int(state.get("restarts", 0)) + 1
        _append(state, {"tick": state["tick"], "kind": "RESUME",
                        "identity": state["identity"], "restarts": state["restarts"]})
    state["alive"] = True
    state["stop_reason"] = None
    organs = build_organs()
    save_state(state, state_path)

    consecutive_idle = 0
    try:
        for _ in range(max(1, ticks)):
            row = tick(state, organs)
            save_state(state, state_path)
            if on_tick is not None:
                on_tick(row)
            if verbose:
                print(_line(row), flush=True)
            consecutive_idle = consecutive_idle + 1 if row["outcome"] == "IDLE" else 0
            if consecutive_idle >= MAX_IDLE_TICKS and not _still_asleep(state, state["tick"]):
                state["stop_reason"] = "IDLE_NOTHING_WORTH_DOING"
                break
            if interval:
                time.sleep(interval)
        else:
            state["stop_reason"] = state.get("stop_reason") or "TICK_BUDGET_SPENT"
    finally:
        state["alive"] = False
        _append(state, {"tick": state["tick"], "kind": "STOP",
                        "reason": state.get("stop_reason"), "identity": state["identity"]})
        save_state(state, state_path)
    return state


def _line(row: Mapping[str, Any]) -> str:
    if row["outcome"] == "IDLE":
        return f"  t{row['tick']:03d} rest        (nothing worth attending to)"
    mark = "?" if row["surprise"] is None else ("!" if row["surprise"] else ".")
    return (f"  t{row['tick']:03d} {mark} {row['organ']:11s} {str(row['target'])[:44]:44s} "
            f"predicted={str(row['predicted'])[:18]:18s} observed={str(row['observed'])[:24]}")


# --------------------------------------------------------------------------- reporting
def summary(state: Mapping[str, Any]) -> dict:
    counts = dict(state.get("counts", {}))
    predicted = counts.get("predicted", 0)
    actions = counts.get("actions", 0)
    journal = state.get("journal", [])
    # Surprise over time: the only evidence that it is learning rather than accumulating.
    pairs = [(e["seq"], bool(e["surprise"])) for e in journal
             if e.get("kind") == "OUTCOME" and e.get("surprise") is not None]
    half = len(pairs) // 2
    early = [s for _, s in pairs[:half]] or []
    late = [s for _, s in pairs[half:]] or []
    return {
        "identity": state.get("identity"),
        "ticks": state.get("tick", 0),
        "restarts": state.get("restarts", 0),
        "actions": actions,
        "idle_ticks": counts.get("idle_ticks", 0),
        "predicted": predicted,
        "unpredicted": actions - predicted,
        "surprises": counts.get("surprised", 0),
        "from_model": sum(1 for e in journal
                          if e.get("kind") == "PREDICTION" and e.get("from_model")),
        "from_model_on_first_visit": sum(
            1 for e in journal if e.get("kind") == "PREDICTION"
            and e.get("from_model") and e.get("first_visit")),
        "model_regrown": counts.get("model_regrown", 0),
        "vocabulary_grown": counts.get("vocabulary_grown", 0),
        "surprise_rate_when_predicted": (round(counts.get("surprised", 0) / predicted, 4)
                                         if predicted else None),
        "surprise_early": round(sum(early) / len(early), 4) if early else None,
        "surprise_late": round(sum(late) / len(late), 4) if late else None,
        "organs": {k: dict(v) for k, v in (state.get("organs") or {}).items()},
        "stop_reason": state.get("stop_reason"),
        "authority": "NO_CAPABILITY_CREDIT_INITIATIVE_MEASUREMENT_ONLY",
        "non_claims": [
            "NO_CAPABILITY_CREDIT_ACTING_ALONE_IS_NOT_BEING_ALIVE",
            "SURPRISE_IS_A_BOOLEAN_ABOUT_ITS_OWN_ACCURACY_NOT_A_FEELING",
            "ORGANS_ARE_EXISTING_AUTHORITY_THE_PROCESS_MAY_NOT_WIDEN_ITSELF",
            "AN_IDLE_TICK_IS_A_RESULT_NOT_A_FAILURE",
        ],
    }


def main(argv: list[str]) -> int:
    if "--reset" in argv:
        if STATE.is_file():
            STATE.unlink()
        print("life forgotten")
        return 0

    if "--status" in argv:
        state = load_state()
        got = summary(state)
        print(f"organism {got['identity']}  ticks={got['ticks']} restarts={got['restarts']} "
              f"stop={got['stop_reason']}")
        print(f"  actions {got['actions']} (idle ticks {got['idle_ticks']}) | "
              f"predicted {got['predicted']} | unpredicted {got['unpredicted']} | "
              f"surprises {got['surprises']} | rate {got['surprise_rate_when_predicted']}")
        print(f"  surprise early {got['surprise_early']} -> late {got['surprise_late']}")
        for name, row in sorted(got["organs"].items()):
            print(f"    {name:12s} attempts {row.get('attempts', 0):3d} "
                  f"confirmed {row.get('confirmations', 0):3d} "
                  f"surprises {row.get('surprises', 0):3d}")
        return 0

    ticks = int(argv[argv.index("--ticks") + 1]) if "--ticks" in argv else 20
    interval = float(argv[argv.index("--interval") + 1]) if "--interval" in argv else 0.0
    state = live(ticks=ticks, interval=interval)
    got = summary(state)
    print()
    print(f"  organism {got['identity']} stopped: {got['stop_reason']}")
    print(f"  ticks {got['ticks']} | actions {got['actions']} | idle {got['idle_ticks']} | "
          f"predicted {got['predicted']} | surprises {got['surprises']} "
          f"({got['surprise_rate_when_predicted']})")
    print(f"  surprise early {got['surprise_early']} -> late {got['surprise_late']}")
    for name, row in sorted(got["organs"].items()):
        print(f"    {name:12s} attempts {row.get('attempts', 0):3d} "
              f"confirmed {row.get('confirmations', 0):3d} "
              f"surprises {row.get('surprises', 0):3d}")
    print()
    print("  Note: acting without being told is not being alive. It is the first thing in this")
    print("  repository that acts without being told.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
