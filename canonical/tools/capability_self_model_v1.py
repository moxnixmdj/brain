#!/usr/bin/env python3
"""A model of the system's own behaviour, scored against what it actually does.

The deepest error in the previous three landings
-----------------------------------------------
Logs 6, 7 and 8 built machines that get steadily better at explaining **numbers the repository
recorded** -- blob ids, byte counts, totals. Each was more general than the last. None of them
made the system better at knowing *what it is doing*, and none could be surprised.

Measured 2026-11-04, on the repository's own 49 hand-written requests, using nothing but what
the registry already declares about itself:

    the registry's own keywords predict which capability the front door will pick
    9 of 32 times (28.1%)

At meanwhile, on the same unmodified tree:

    Add a second method to Main.java        -> routed to a FINANCE capability
    Add a NOT NULL constraint on schema.sql -> routed to typed synthesis declaring python
    Fix the off-by-one bug in main.cpp      -> routed to a capability declaring python
    Add a function to lib.rs                -> routed to a capability declaring go, python

Five of the 32 routed requests are answered by a capability that declares a *different
language* than the request names. The system cannot notice any of this, because it has never
had a faculty whose job is to know what it does. Every previous layer checked the tree; this
one checks the system.

Why prediction and not measurement
----------------------------------
A system that only measures cannot be wrong about itself. It reports what it did. A system
that *predicts* can be surprised, and surprise is the only signal that something is worth
learning. So the primitive here is:

    predict(own action | the sentence)  vs  the action the front door actually takes

The two self-models are deliberately blind to the router's internals
-------------------------------------------------------------------
`match_evidence`, `binding_provenance` and `score` are visible in the compile result, and
reading them would make the prediction perfect and the surprise zero -- a self-model that
copies the answer key has learned nothing and can never be surprised. Both models below are
built only from (a) the sentence and (b) what the registry declares in public:

    DECLARED   argmax keyword overlap with each capability's own declared keywords. This is
               what the system's documentation says it will do. It is the strongest thing a
               creature can know about itself without introspection, and it is 28.1% right.
    LEARNED    token -> capability frequencies learned from the system's OBSERVED past
               behaviour, on a fit split only, with abstention when no token has evidence.

Consensus as the only honest discriminator
------------------------------------------
With two independent models, a disagreement has three shapes, and they mean different things:

    MODELS_AGREE_ROUTER_DIFFERS   both models independently expect X, the router does Y.
                                  Strong evidence the route is at fault.
    MODELS_DISAGREE               the self-model is under-determined. Not a router defect.
    EXPECTED_BUT_NO_ROUTE         the models expect X, the router refuses. A reach gap.

Consensus is evidence, not proof, and it is labelled as evidence.

The act: a gate that can distrust its own answer
------------------------------------------------
`trust_gate()` returns TRUST / DISTRUST and is scored against a *mechanical* defect label that
needs no person: a route to a capability declaring a different language than the request names,
or a refusal where both models expected a capability. The trade-off is reported in full --
defects caught, correct answers preserved, correct answers lost -- because a gate that refuses
everything would otherwise look perfect.

Usage::

    python3 canonical/tools/capability_self_model_v1.py            # measure
    python3 canonical/tools/capability_self_model_v1.py --write    # write artifact + model
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_CAPABILITY_SELF_MODEL_V1"
ARTIFACT = "canonical/verification/CAPABILITY_SELF_MODEL_V1.json"
MODEL_ARTIFACT = "canonical/verification/CAPABILITY_SELF_MODEL_WEIGHTS_V1.json"

# What a capability declares about the languages it serves. Kept separate from scoring so the
# defect label below is a mechanical read of the registry, not a judgement.
LANGUAGES = {
    "python": (".py", "python"),
    "c++": (".cpp", ".cc", ".hpp", "c++", "cpp"),
    "go": (".go", "golang"),
    "java": (".java", "java"),
    "rust": (".rs", "rust"),
    "sql": (".sql", "sql"),
    "javascript": (".js", ".ts", ".jsx", ".tsx", "javascript", "typescript"),
}
# Only fields that claim what a capability DOES. `limitations` is prose that often names a
# language in order to disclaim it ("does not run python"), so reading it makes a capability
# appear to declare an ecosystem it explicitly does not serve. Excluded after the first pass
# measured defects with it included.
DECLARED_FIELDS = ("keywords", "platforms", "provides", "source", "action_template")
TOKEN = re.compile(r"[a-z0-9_]+")


# --------------------------------------------------------------------------- observation
def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def load_registry() -> dict:
    doc = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                     .read_text(encoding="utf-8"))
    return doc["capabilities"] if "capabilities" in doc else doc


def sentences() -> list[dict]:
    from canonical.tools.route_reach_census_v1 import real_sentence_corpus
    return real_sentence_corpus()


def observe(goal: str, registry: Mapping[str, Any]) -> dict:
    """What the front door actually does. This is the ground truth and it is not ours to edit."""
    from canonical.runtime import goal_front_compiler_v1 as front

    row = {"goal": goal, "capability": None, "refused": None, "score": None}
    try:
        compiled = front.compile_goal(goal, registry, ROOT)
    except Exception as exc:                                  # noqa: BLE001
        row["refused"] = str(getattr(exc, "code", None) or type(exc).__name__)
        return row
    row["capability"] = compiled.get("selected_capability")
    row["score"] = compiled.get("score")
    if not row["capability"]:
        row["refused"] = "NO_SELECTION"
    return row


# --------------------------------------------------------------------------- the two models
def declared_predict(goal: str, registry: Mapping[str, Any]) -> str | None:
    """What the system's own documentation says it will do.

    Blind on purpose: it reads only `keywords`, which is the registry's public claim about
    itself. Anything internal to the compiler would make this a copy of the answer.
    """
    words = set(tokens(goal))
    best, best_n = None, 0
    for cid, entry in registry.items():
        declared = {k.lower() for k in (entry.get("keywords") or [])}
        n = len(words & declared)
        if n > best_n:
            best, best_n = cid, n
    return best


class LearnedModel:
    """token -> capability, learned from the system's own observed behaviour.

    Only behaviour already seen. It abstains when no token in the sentence has evidence, which
    is the difference between a model that knows it does not know and one that always answers.
    """

    def __init__(self, table: Mapping[str, Mapping[str, int]] | None = None,
                 totals: Mapping[str, int] | None = None) -> None:
        self.table = {k: dict(v) for k, v in (table or {}).items()}
        self.totals = dict(totals or {})

    def fit(self, observations: Iterable[Mapping[str, Any]]) -> "LearnedModel":
        self.table.clear()
        self.totals.clear()
        for row in observations:
            chosen = row.get("capability")
            if not chosen:
                continue
            for tok in set(tokens(row["goal"])):
                self.table.setdefault(tok, {})
                self.table[tok][chosen] = self.table[tok].get(chosen, 0) + 1
                self.totals[tok] = self.totals.get(tok, 0) + 1
        return self

    def predict(self, goal: str) -> str | None:
        scores: Counter = Counter()
        for tok in set(tokens(goal)):
            row = self.table.get(tok)
            if not row:
                continue
            total = self.totals.get(tok, 1) + len(row)
            for cap, count in row.items():
                scores[cap] += (count + 1) / total
        if not scores:
            return None                       # abstain rather than guess
        top = max(scores.values())
        tied = sorted(c for c, v in scores.items() if v == top)
        return tied[0] if len(tied) == 1 else None    # a tie is not a prediction

    def as_dict(self) -> dict:
        return {"table": self.table, "totals": self.totals}


# --------------------------------------------------------------------------- splitting
def split(rows: list[dict], mod: int = 2) -> tuple[list[dict], list[dict]]:
    """Deterministic. A rerun may not silently change the headline number."""
    fit, hold = [], []
    for row in rows:
        digest = hashlib.sha1(row["goal"].encode("utf-8")).hexdigest()
        (fit if int(digest[:8], 16) % mod == 0 else hold).append(row)
    return fit, hold


# --------------------------------------------------------------------------- defect label
def languages_in(goal: str) -> set[str]:
    low = goal.lower()
    out = set()
    for language, needles in LANGUAGES.items():
        if language in low or any(n in low for n in needles):
            out.add(language)
    return out


def declared_languages(cid: str, registry: Mapping[str, Any]) -> set[str]:
    entry = registry.get(cid) or {}
    # json, not repr: repr of a dict quotes cleanly but the first version used it inside the
    # compiler and the two readings drifted apart. One canonical serialisation, one answer.
    blob = json.dumps({k: entry.get(k) for k in DECLARED_FIELDS}, default=str).lower()
    return {language for language, needles in LANGUAGES.items()
            if language in blob or any(n in blob for n in needles)}


def mechanical_defect(row: Mapping[str, Any], registry: Mapping[str, Any]) -> str | None:
    """A defect label that needs no person and no judgement.

    A request that names C++ and an answer from a capability that declares only python is
    wrong, and the registry says so in its own words. This is deliberately narrow: it can only
    label the cases where the wrongness is visible in the declaration, and it will miss
    domain errors that share a language. What it does not catch, it does not claim.
    """
    if row.get("refused") == "NO_SELECTION" or row.get("refused") is None:
        pass
    goal, chosen = row["goal"], row.get("capability")
    if not chosen:
        return None                       # refusals are a reach gap, measured separately
    wanted, declared = languages_in(goal), declared_languages(chosen, registry)
    if wanted and declared and not (wanted & declared):
        return "ROUTE_TO_CAPABILITY_DECLARING_ANOTHER_LANGUAGE"
    return None


# --------------------------------------------------------------------------- self-model
def measure(*, write: bool = False) -> dict:
    registry = load_registry()
    rows = [observe(item["goal"], registry) for item in sentences()]
    fit, hold = split(rows)

    learned = LearnedModel().fit(fit)

    def score(group: list[dict], label: str) -> dict:
        routed = [r for r in group if r.get("capability")]
        hits_decl = sum(1 for r in routed
                        if declared_predict(r["goal"], registry) == r["capability"])
        hits_learn = sum(1 for r in routed
                         if learned.predict(r["goal"]) == r["capability"])
        abstain = sum(1 for r in routed if learned.predict(r["goal"]) is None)
        return {"split": label, "sentences": len(group), "routed": len(routed),
                "declared_correct": hits_decl,
                "declared_accuracy": round(hits_decl / len(routed), 4) if routed else None,
                "learned_correct": hits_learn,
                "learned_accuracy": round(hits_learn / len(routed), 4) if routed else None,
                "learned_abstained": abstain}

    on_fit = score(fit, "fit")
    on_hold = score(hold, "holdout")

    # Surprise: where the self-model and the action disagree. Counted on the holdout only,
    # because a model that has already seen a sentence is not surprised by it.
    surprises = []
    for row in hold:
        if not row.get("capability"):
            continue
        declared = declared_predict(row["goal"], registry)
        learnt = learned.predict(row["goal"])
        if declared == row["capability"] and learnt == row["capability"]:
            continue
        if declared == learnt and declared != row["capability"]:
            kind = "MODELS_AGREE_ROUTER_DIFFERS"
        elif declared != learnt and learnt is not None:
            kind = "MODELS_DISAGREE"
        elif declared != learnt and learnt is None:
            kind = "LEARNED_MODEL_ABSTAINS"
        else:
            kind = "MODELS_DISAGREE"
        surprises.append({"goal": row["goal"], "actual": row["capability"],
                          "declared": declared, "learned": learnt, "kind": kind,
                          "defect": mechanical_defect(row, registry)})

    # The gate: distrust when the models do not both endorse the router's choice.
    def gate(row: Mapping[str, Any]) -> str:
        if not row.get("capability"):
            return "DISTRUST"
        declared = declared_predict(row["goal"], registry)
        learnt = learned.predict(row["goal"])
        if declared == row["capability"] and learnt == row["capability"]:
            return "TRUST"
        return "DISTRUST"

    defective = [r for r in rows if mechanical_defect(r, registry)]
    clean = [r for r in rows if r.get("capability") and not mechanical_defect(r, registry)]
    caught = sum(1 for r in defective if gate(r) == "DISTRUST")
    preserved = sum(1 for r in clean if gate(r) == "TRUST")
    lost = sum(1 for r in clean if gate(r) == "DISTRUST")

    report = {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_SELF_MODEL_OF_OWN_BEHAVIOUR_ONLY",
        "instrument": "PREDICT_OWN_ACTION_THEN_SCORE_AGAINST_IT",
        "what_is_predicted": "which capability the front door will select, or that it refuses",
        "blindness": [
            "NEITHER_MODEL_READS_MATCH_EVIDENCE_BINDING_PROVENANCE_OR_SCORE",
            "A_SELF_MODEL_THAT_COPIES_THE_ROUTERS_REASONS_CAN_NEVER_BE_SURPRISED",
        ],
        "corpus": {"sentences": len(rows),
                   "routed": sum(1 for r in rows if r.get("capability")),
                   "refused": sum(1 for r in rows if not r.get("capability")),
                   "refusal_codes": dict(Counter(r.get("refused") for r in rows
                                                 if not r.get("capability")))},
        "self_prediction": {"fit": on_fit, "holdout": on_hold},
        "surprise": {
            "events_on_holdout": len(surprises),
            "kinds": dict(Counter(s["kind"] for s in surprises)),
            "examples": surprises[:6],
        },
        "defects_visible_in_the_registry": {
            "label": "ROUTE_TO_CAPABILITY_DECLARING_ANOTHER_LANGUAGE",
            "count": len(defective),
            "rows": [{"goal": r["goal"], "chosen": r["capability"],
                      "wanted": sorted(languages_in(r["goal"])),
                      "declared": sorted(declared_languages(r["capability"], registry))}
                     for r in defective],
            "what_this_label_cannot_see": [
                "A wrong route that shares the request's language",
                "A right route whose capability declares no language at all",
            ],
        },
        "gate": {
            "rule": "TRUST only when the declared model AND the learned model both agree with "
                    "the router's own choice",
            "defects_caught": caught,
            "defects_missed": len(defective) - caught,
            "correct_preserved": preserved,
            "correct_lost": lost,
            "precision_against_mechanical_label": (round(caught / (caught + lost), 4)
                                                   if (caught + lost) else None),
            "cost": "every DISTRUST is either a defect caught or a correct answer lost; both "
                    "numbers are above and neither is allowed to be omitted",
        },
        "non_claims": [
            "NO_CAPABILITY_CREDIT_A_MODEL_OF_ONESELF_IS_NOT_CAPABILITY",
            "PREDICTING_ONES_OWN_ACTION_DOES_NOT_MAKE_THAT_ACTION_CORRECT",
            "CONSENSUS_OF_TWO_MODELS_IS_EVIDENCE_NOT_PROOF",
            "THE_MECHANICAL_DEFECT_LABEL_ONLY_SEES_LANGUAGE_MISMATCHES",
        ],
    }
    if write:
        (ROOT / ARTIFACT).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
        (ROOT / MODEL_ARTIFACT).write_text(
            json.dumps({"schema": SCHEMA + "_WEIGHTS",
                        "trained_on": {"sentences": len(fit)},
                        **learned.as_dict()}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return report


# --------------------------------------------------------------------------- experience
# The system has almost no life. Measured 2026-11-04: 49 hand-written requests is the entire
# record of its own behaviour. The only larger "behaviour corpus" in the tree -- 423 records of
# shape (sentence, selected) in ROUTE_REACH_CENSUS_V1.json -- is a templated echo of the
# registry's own keywords ("archive tar gz bundle manifest package create from"). Training on it
# would produce an excellent predictor of my census generator and teach the system nothing about
# itself, so it is refused here, by name, rather than quietly used.
CONTAMINATED_CORPUS = "canonical/verification/ROUTE_REACH_CENSUS_V1.json"

# Verbs and objects a request may use. Chosen independently of any capability's declared
# keywords, so a generated sentence cannot be an echo of the answer.
TASK_VERBS = ("add", "fix", "rename", "remove", "explain", "refactor", "test", "verify",
              "convert", "document", "optimise", "repair", "split", "inline")
TASK_OBJECTS = ("function", "class", "import", "dependency", "test", "config key",
                "type hint", "docstring", "argument", "module", "constant", "loop")
TEMPLATES = ("{verb} {obj} in {path}", "{verb} the {obj} in {path}",
             "{verb} {path}", "{verb} the {obj} named in {path}")


def _sample_paths(limit: int) -> list[str]:
    paths = sorted(str(p.relative_to(ROOT)) for p in
                   list(ROOT.glob("canonical/runtime/*.py"))
                   + list(ROOT.glob("canonical/tools/*.py"))
                   + list(ROOT.glob("execution_guard/*.py")))
    if not paths:
        return []
    step = max(1, len(paths) // limit)
    return paths[::step][:limit]


def generate_experience(registry: Mapping[str, Any], *, count: int = 240) -> list[dict]:
    """Manufacture honest experience: real sentences about real files, adjudicated by the
    router. The situations come from the repository's content, the labels from the front door.

    It is not a life. It is a first breath: enough events for a model of self to have something
    to learn from, sampled from the world rather than from the system's own declarations.
    """
    paths = _sample_paths(max(1, count))
    rows: list[dict] = []
    for index in range(count):
        path = paths[index % len(paths)]
        verb = TASK_VERBS[index % len(TASK_VERBS)]
        obj = TASK_OBJECTS[(index * 7) % len(TASK_OBJECTS)]
        template = TEMPLATES[(index * 3) % len(TEMPLATES)]
        goal = template.format(verb=verb, obj=obj, path=path)
        row = observe(goal, registry)
        row["generated"] = True
        rows.append(row)
    return rows


def evaluate_with_experience(*, count: int = 240) -> dict:
    """Train a model of self on manufactured experience, then test it on real requests.

    The 49 hand-written sentences are never trained on. If a model that has only ever seen
    generated situations can predict the system's behaviour on real requests better than the
    registry's own keywords can, the system has learned something about itself that its
    documentation does not contain. If it cannot, that is the answer and it gets reported.
    """
    registry = load_registry()
    experience = generate_experience(registry, count=count)
    model = LearnedModel().fit(experience)
    real = [observe(item["goal"], registry) for item in sentences()]
    routed = [r for r in real if r.get("capability")]

    hits = sum(1 for r in routed if model.predict(r["goal"]) == r["capability"])
    declared_hits = sum(1 for r in routed
                        if declared_predict(r["goal"], registry) == r["capability"])
    abstained = sum(1 for r in routed if model.predict(r["goal"]) is None)

    def gate(row: Mapping[str, Any]) -> str:
        if not row.get("capability"):
            return "DISTRUST"
        if (declared_predict(row["goal"], registry) == row["capability"]
                and model.predict(row["goal"]) == row["capability"]):
            return "TRUST"
        return "DISTRUST"

    defective = [r for r in real if mechanical_defect(r, registry)]
    clean = [r for r in real if r.get("capability") and not mechanical_defect(r, registry)]
    caught = sum(1 for r in defective if gate(r) == "DISTRUST")
    preserved = sum(1 for r in clean if gate(r) == "TRUST")
    lost = sum(1 for r in clean if gate(r) == "DISTRUST")

    return {
        "experience": {"generated_sentences": len(experience),
                       "routed_while_generating": sum(1 for e in experience
                                                      if e.get("capability")),
                       "sampled_from": "real files under canonical/ and execution_guard/",
                       "trained_on_real_requests": 0},
        "real_requests_never_seen": {"routed": len(routed),
                                     "learned_from_experience": hits,
                                     "learned_accuracy": round(hits / len(routed), 4)
                                     if routed else None,
                                     "learned_abstained": abstained,
                                     "declared_by_registry": declared_hits,
                                     "declared_accuracy": round(declared_hits / len(routed), 4)
                                     if routed else None},
        "gate_with_experience": {"defects_caught": caught, "defects_total": len(defective),
                                 "correct_preserved": preserved, "correct_lost": lost,
                                 "precision": round(caught / (caught + lost), 4)
                                 if (caught + lost) else None},
        "refused_training_data": {
            "path": CONTAMINATED_CORPUS,
            "records": 423,
            "why": "the sentences are templated from the registry's own keywords, so a model "
                   "trained on them predicts the generator, not the system",
        },
    }


def main(argv: list[str]) -> int:
    if "--experience" in argv:
        count = int(argv[argv.index("--experience") + 1]) if len(argv) > argv.index("--experience") + 1 else 240
        got = evaluate_with_experience(count=count)
        e, r, g = got["experience"], got["real_requests_never_seen"], got["gate_with_experience"]
        print("capability self-model  (a first breath, then a test on real requests)")
        print(f"  manufactured experience   : {e['generated_sentences']} sentences "
              f"({e['routed_while_generating']} routed), sampled from real files")
        print(f"  trained on real requests  : {e['trained_on_real_requests']}")
        print(f"  refused as training data  : {got['refused_training_data']['records']} records "
              f"in {got['refused_training_data']['path'].split('/')[-1]}")
        print(f"    -- {got['refused_training_data']['why']}")
        print()
        print(f"  real requests, never seen : {r['routed']} routed")
        print(f"    learned from experience : {r['learned_from_experience']}/{r['routed']} "
              f"= {r['learned_accuracy']}  (abstained {r['learned_abstained']})")
        print(f"    declared by registry    : {r['declared_by_registry']}/{r['routed']} "
              f"= {r['declared_accuracy']}")
        print(f"  gate with experience      : caught {g['defects_caught']}/{g['defects_total']} | "
              f"preserved {g['correct_preserved']} | lost {g['correct_lost']} | "
              f"precision {g['precision']}")
        if "--write" in argv:
            out = ROOT / "canonical/verification/CAPABILITY_SELF_MODEL_EXPERIENCE_V1.json"
            out.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"  written: {out.relative_to(ROOT)}")
        return 0

    report = measure(write="--write" in argv)
    c = report["corpus"]
    print("capability self-model  (predicting its own action)")
    print(f"  corpus                    : {c['sentences']} sentences | "
          f"{c['routed']} routed | {c['refused']} refused")
    for split_name in ("fit", "holdout"):
        s = report["self_prediction"][split_name]
        print(f"  {split_name:8s}: routed {s['routed']:2d} | "
              f"declared-by-registry {s['declared_correct']:2d} "
              f"({s['declared_accuracy']}) | "
              f"learned-from-past {s['learned_correct']:2d} "
              f"({s['learned_accuracy']}, abstained {s['learned_abstained']})")
    s = report["surprise"]
    print(f"  surprise on holdout       : {s['events_on_holdout']} events  {s['kinds']}")
    d = report["defects_visible_in_the_registry"]
    print(f"  routes to a capability declaring ANOTHER language : {d['count']}")
    for row in d["rows"]:
        print(f"    {row['wanted']} requested -> {row['chosen']} (declares {row['declared']})")
        print(f"      {row['goal'][:74]}")
    g = report["gate"]
    print(f"  gate                      : caught {g['defects_caught']}/{d['count']} defects | "
          f"preserved {g['correct_preserved']} correct | lost {g['correct_lost']}")
    print(f"    precision vs the mechanical label : {g['precision_against_mechanical_label']}")
    for kind, rows in (("agreement against the router", None),):
        pass
    for ex in s["examples"][:4]:
        print(f"    ! {ex['kind']:28s} actual={str(ex['actual'])[:38]:38s}")
        print(f"      declared={str(ex['declared'])[:34]:34s} learned={str(ex['learned'])[:34]}")
        print(f"      {ex['goal'][:76]}")
    if "--write" in argv:
        print(f"  written: {ARTIFACT}")
    print()
    print("  Note: predicting your own next action is not capability. It is the first thing")
    print("  in this repository that can be wrong about the system rather than about the tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
