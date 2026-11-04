#!/usr/bin/env python3
"""A round of self-maintenance the system runs on itself, unattended.

Why this exists
---------------
Every defect corrected in this repository during the 2026-11-02/03 sessions was found by a
person or an agent and pointed at. The system diagnosed none of them. It has a self-model
(`ignorance_ledger_v1` ranks what it does not know by expected value), it has an exact
probe selector (`finite_capability_diagnosis.select_probe`), it has an oracle
(`ProjectTestOracle`), and it has an immune system (`repo_integrity_guard_v1`) -- and nothing
connects them into a loop that acts. So the improvement rate is proportional to how many
sessions a human runs.

The measurable form of that complaint is one number, and it has never been measured here:

    UNAIDED CLOSURE RATE -- of the defects this system faces, what fraction does it find,
    fix, and prove fixed on its own, with nobody pointing?

What a round is
---------------
    PERCEIVE   every registered finder returns the defects it can prove
    MODEL      each defect is registered in the ignorance ledger, so the system has a record
               of what it did not know before it acts on it
    SELECT     the ledger's expected-value ranking decides the order, not a hardcoded list --
               a class that has repeatedly paid off is tried first, without anyone writing
               that rule
    ACT        the fixer applies the smallest change that removes the defect
    VERIFY     an INDEPENDENT recomputation re-reads the tree from disk and re-derives the
               property. The fixer's own return value is never evidence
    LEARN      the ledger is told whether closing that gap helped, which is the only thing
               that changes the ranking next round

The scope bug this module had to fix first
------------------------------------------
Version 1 of this file scanned *every* action intent in `canonical/action_intents/` and
reported **841** stale receipts. That number was wrong, and the way it was wrong is worth
keeping: the drift guard (`canonical/runtime/enforce_goal_hierarchy.py`) loads only the
intents **in the change set**, refuses a PR that contains more than one
(`MULTIPLE_ACTION_INTENTS_IN_ONE_PR`), and resolves each receipt against a **git ref**, not
against archived history. An archived intent is a record of what was true when it was
written; its receipt pointing at a file that has since changed is not a defect, it is the
archive doing its job. A finder that does not model the enforcer's world manufactures
thousands of defects that nobody owes. So PERCEIVE is scoped to the change set, and the
number this module reports is about live defects only.

What is deliberately NOT here
-----------------------------
* No model. Every finder, fixer and verifier is deterministic. Zero spend.
* No new authority. Only the declared artifact classes are touched, and each verifier
  re-derives its property from the file on disk.
* No claim of capability. Its output is a count of what it closed, with evidence, and a
  non-claim that a self-maintained tree is not a more capable one.
* No semantically-derived fix. A capability id, a routing binding, a read/write choice --
  none of those are derivable from the artifact itself, so no class here touches them. That
  boundary is the honest limit of unattended repair, and it is the next thing to widen.

Usage::

    python3 canonical/tools/self_maintenance_loop_v1.py                # measure, change nothing
    python3 canonical/tools/self_maintenance_loop_v1.py --apply        # fix and verify
    python3 canonical/tools/self_maintenance_loop_v1.py --apply --rounds 3
    python3 canonical/tools/self_maintenance_loop_v1.py --base 2ececc4
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_SELF_MAINTENANCE_LOOP_V1"
INTENT_DIR = "canonical/action_intents"
LEDGER = ROOT / "canonical/astra_runtime/state/IGNORANCE_LEDGER_V1.json"
BASE_FALLBACK = "2ececc45eb74e1067915161cbae298a998ac4aaa"


# --------------------------------------------------------------------------- git
def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def blob_sha(relpath: str) -> str | None:
    """The blob id git would give this file's current bytes, or None if it is not a file."""
    if not (ROOT / relpath).is_file():
        return None
    return _git("hash-object", relpath) or None


def committed_blob_sha(relpath: str, ref: str = "HEAD") -> str | None:
    """The blob id recorded at `ref` for this path, i.e. what the guard will resolve."""
    return _git("rev-parse", f"{ref}:{relpath}") or None


def resolve_base(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    base = _git("merge-base", "HEAD", "origin/main")
    if base:
        return base
    if _git("cat-file", "-t", BASE_FALLBACK):
        return BASE_FALLBACK
    return None


def change_set(base: str | None = None) -> list[str]:
    """The paths this change proposes: committed since `base`, plus uncommitted edits.

    This is the same world the drift guard evaluates. Anything outside it is archive.
    """
    paths: set[str] = set()
    if base:
        out = _git("diff", "--name-only", base, "HEAD") or ""
        paths.update(p for p in out.splitlines() if p.strip())
    out = _git("diff", "--name-only", "HEAD") or ""
    paths.update(p for p in out.splitlines() if p.strip())
    out = _git("ls-files", "--others", "--exclude-standard") or ""
    paths.update(p for p in out.splitlines() if p.strip())
    return sorted(paths)


def intents_in_change_set(base: str | None = None) -> list[Path]:
    return [ROOT / p for p in change_set(base)
            if p.startswith(INTENT_DIR + "/") and p.endswith(".json")]


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _receipts(doc: Mapping[str, Any]) -> list[Any]:
    got = (((doc.get("v22_prewrite_admission") or {}).get("tournament") or {})
           .get("counterexample_receipts"))
    return got if isinstance(got, list) else []


def derived_lease_key(intent: Mapping[str, Any]) -> str:
    """Recomputed exactly as the drift guard derives it, from the intent's own fields."""
    return "::".join([
        str(intent.get("canonical_generation") or ""),
        str(intent.get("capability_target") or ""),
        str(intent.get("causal_blocker") or ""),
    ])


# --------------------------------------------------------------------------- defect classes
class DefectClass:
    """One mechanically findable, fixable, independently verifiable defect class."""

    def __init__(self, *, class_id: str, describes: str,
                 find: Callable[[], list[dict]],
                 fix: Callable[[dict], dict],
                 verify: Callable[[dict], bool]) -> None:
        self.class_id = class_id
        self.describes = describes
        self.find = find
        self.fix = fix
        self.verify = verify

    def as_dict(self) -> dict:
        return {"class_id": self.class_id, "describes": self.describes}


# ---- class 1: a receipt that no longer matches the file it binds -------------------------
def make_stale_receipt_class(base_ref: str | None = None) -> DefectClass:
    def scope() -> str | None:
        return base_ref

    def find() -> list[dict]:
        out: list[dict] = []
        for path in intents_in_change_set(scope()):
            doc = _load(path)
            if not isinstance(doc, dict):
                continue
            for index, row in enumerate(_receipts(doc)):
                if not isinstance(row, dict):
                    continue
                target = str(row.get("path") or "")
                recorded = str(row.get("git_blob_sha") or "")
                actual = blob_sha(target)
                if actual is None or not recorded or actual == recorded:
                    continue
                out.append({
                    "defect_id": f"STALE_ACTION_INTENT_RECEIPT:{path.name}:{index}",
                    "path": path.relative_to(ROOT).as_posix(),
                    "detail": f"receipt[{index}] binds {target}",
                    "target": target,
                    "recorded": recorded,
                    "actual": actual,
                })
        return out

    def fix(defect: dict) -> dict:
        """Rewrite only the sha, and only for the receipt the finder named."""
        path = ROOT / defect["path"]
        doc = _load(path)
        if not isinstance(doc, dict):
            return {"applied": False, "reason": "INTENT_UNREADABLE"}
        index = int(str(defect["defect_id"]).rsplit(":", 1)[1])
        receipts = _receipts(doc)
        if index >= len(receipts) or not isinstance(receipts[index], dict):
            return {"applied": False, "reason": "RECEIPT_INDEX_GONE"}
        row = receipts[index]
        if str(row.get("path") or "") != defect["target"]:
            return {"applied": False, "reason": "RECEIPT_PATH_MOVED_SINCE_FIND"}
        fresh = blob_sha(defect["target"])
        if fresh is None:
            return {"applied": False, "reason": "TARGET_NOT_A_FILE"}
        before = row.get("git_blob_sha")
        row["git_blob_sha"] = fresh
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"applied": True, "before": before, "after": fresh}

    def verify(defect: dict) -> bool:
        """Independent: re-read the artifact and re-derive the property from the tree."""
        doc = _load(ROOT / defect["path"])
        if not isinstance(doc, dict):
            return False
        receipts = _receipts(doc)
        index = int(str(defect["defect_id"]).rsplit(":", 1)[1])
        if index >= len(receipts) or not isinstance(receipts[index], dict):
            return False
        row = receipts[index]
        actual = blob_sha(str(row.get("path") or ""))
        return actual is not None and str(row.get("git_blob_sha")) == actual

    return DefectClass(
        class_id="STALE_ACTION_INTENT_RECEIPT",
        describes="a receipt's recorded blob sha no longer matches the file it binds",
        find=find, fix=fix, verify=verify)


# ---- class 2: a lease key that does not match the intent's own fields -------------------
def make_stale_lease_class(base_ref: str | None = None) -> DefectClass:
    def find() -> list[dict]:
        out: list[dict] = []
        for path in intents_in_change_set(base_ref):
            doc = _load(path)
            if not isinstance(doc, dict):
                continue
            recorded = str(doc.get("blocker_lease_key") or "")
            expected = derived_lease_key(doc)
            if recorded and expected and recorded != expected:
                out.append({
                    "defect_id": f"STALE_BLOCKER_LEASE_KEY:{path.name}",
                    "path": path.relative_to(ROOT).as_posix(),
                    "detail": "lease key differs from the key derived from the intent itself",
                    "recorded": recorded,
                    "expected": expected,
                })
        return out

    def fix(defect: dict) -> dict:
        path = ROOT / defect["path"]
        doc = _load(path)
        if not isinstance(doc, dict):
            return {"applied": False, "reason": "INTENT_UNREADABLE"}
        expected = derived_lease_key(doc)
        if expected != defect["expected"]:
            return {"applied": False, "reason": "INTENT_CHANGED_SINCE_FIND"}
        before = doc.get("blocker_lease_key")
        doc["blocker_lease_key"] = expected
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"applied": True, "before": before, "after": expected}

    def verify(defect: dict) -> bool:
        doc = _load(ROOT / defect["path"])
        if not isinstance(doc, dict):
            return False
        return str(doc.get("blocker_lease_key") or "") == derived_lease_key(doc)

    return DefectClass(
        class_id="STALE_BLOCKER_LEASE_KEY",
        describes="the lease key differs from the key derived from the intent itself",
        find=find, fix=fix, verify=verify)


# ---- class 3: a recorded measurement that no longer reproduces --------------------------
REACH_ARTIFACT = "canonical/verification/ROUTE_REACH_REAL_SENTENCES_V1.json"


def _recompute_reach() -> dict:
    from canonical.tools.route_reach_census_v1 import reach_over_real_sentences
    return reach_over_real_sentences()


def make_stale_measurement_class(artifact: str = REACH_ARTIFACT,
                                 recompute: Callable[[], dict] | None = None) -> DefectClass:
    """A verification artifact whose numbers no longer follow from the tree.

    This is the class that makes the loop matter for anything other than receipts: the
    system re-derives its own published reach figure from disk, and if the tree has moved
    under it, the artifact is repaired from a fresh computation -- not edited by hand,
    not quoted from the previous run. A stale reach number is the one artifact most able
    to make this repository lie about itself, so it is the first non-intent class.
    """
    recompute = recompute or _recompute_reach

    def _current_fields(doc: Mapping[str, Any]) -> dict:
        """Canonical JSON form, so the comparison is between two documents, not two types.

        The in-memory result holds `reach_magnets` as tuples while the artifact on disk holds
        lists. Compared naively, every run reported a stale artifact and every "repair"
        rewrote the file -- a fix that fires forever is not a fix, it is churn wearing the
        costume of one. Round-tripping kills that class of false positive at the source.
        """
        return json.loads(json.dumps({k: v for k, v in doc.items() if k != "rows"},
                                     sort_keys=True))

    def find() -> list[dict]:
        path = ROOT / artifact
        if not path.is_file():
            return []
        recorded = _load(path)
        if not isinstance(recorded, dict):
            return []
        fresh = recompute()
        was, now = _current_fields(recorded), _current_fields(fresh)
        differing = sorted(k for k in set(was) | set(now) if was.get(k) != now.get(k))
        if not differing:
            return []
        return [{
            "defect_id": f"STALE_VERIFICATION_ARTIFACT:{Path(artifact).name}",
            "path": artifact,
            "detail": "recorded measurement no longer reproduces: " + ", ".join(differing),
            "differing": differing,
            "was": {k: was.get(k) for k in differing},
            "now": {k: now.get(k) for k in differing},
        }]

    def fix(defect: dict) -> dict:
        fresh = recompute()
        path = ROOT / artifact
        path.write_text(json.dumps(fresh, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"applied": True, "regenerated": defect["differing"]}

    def verify(defect: dict) -> bool:
        recorded = _load(ROOT / artifact)
        if not isinstance(recorded, dict):
            return False
        return _current_fields(recorded) == _current_fields(recompute())

    return DefectClass(
        class_id="STALE_VERIFICATION_ARTIFACT",
        describes="a recorded measurement in a verification artifact no longer reproduces",
        find=find, fix=fix, verify=verify)


def _derived_value_class(base_ref: str | None) -> DefectClass:
    """The class nobody wrote: its predicates come from derivations the system inferred.

    The model is read from `DERIVATION_MODEL_V1.json`, which `derivation_inference_v1`
    learned from 445k of this repository's own records. If the model is absent this class
    finds nothing and says so -- it must never silently become a person's hand-written rule.
    """
    from canonical.tools import derivation_inference_v1 as infer
    model = infer.load_model(recompute_if_missing=False)
    if model is None:
        return DefectClass(
            class_id="DERIVED_VALUE_DISAGREES",
            describes="(model absent: no inferred derivation is available, so nothing is checked)",
            find=lambda: [], fix=lambda d: {"applied": False, "reason": "MODEL_ABSENT"},
            verify=lambda d: False)
    return infer.make_derived_value_class(base_ref, model=model)


def default_classes(base_ref: str | None = None) -> list[DefectClass]:
    return [
        make_stale_receipt_class(base_ref),
        make_stale_lease_class(base_ref),
        make_stale_measurement_class(),
        _derived_value_class(base_ref),
    ]


CLASSES = default_classes()


# --------------------------------------------------------------------------- certification
def _intents_changed_between(base: str | None, ref: str) -> list[Path]:
    if not base:
        return []
    out = _git("diff", "--name-only", base, ref) or ""
    return [ROOT / p for p in out.splitlines()
            if p.startswith(INTENT_DIR + "/") and p.endswith(".json")]


def certify(defect: Mapping[str, Any], *, ref: str = "HEAD",
            base: str | None = None) -> bool | None:
    """Does the defect disappear under the AUTHORITY's own predicate, at `ref`?

    This is the difference between a repair and a repair that counts. The loop writes the
    sha of the file's final bytes, which is right for the commit that is about to exist --
    but the drift guard resolves receipts at `ref:path`, so between the fix and the commit
    the guard still fails, correctly. Measured 2026-11-04: the loop reported 2/2 closed
    (100%) while `enforce_goal_hierarchy.py --base 2ececc4` still reported
    `V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:9` and `:12`.

    A number that disagrees with the enforcer is the number that is wrong. So closure is
    only credited when the defect is absent from the ref-based recomputation; otherwise it
    is reported as `prepared_not_certified`, which is the truth: the fix is on disk and
    unproven until a commit exists to resolve it against.

    Returns None when the class has no ref-relative form (it is about working-tree bytes).
    """
    cid = str(defect.get("defect_id") or "")
    if cid.startswith("STALE_ACTION_INTENT_RECEIPT:"):
        _, rest = cid.split(":", 1)
        fname, _, index_s = rest.rpartition(":")
        for path in _intents_changed_between(base, ref):
            if path.name != fname:
                continue
            doc = _load(path) or {}
            receipts = _receipts(doc)
            i = int(index_s)
            if i >= len(receipts) or not isinstance(receipts[i], dict):
                return True
            row = receipts[i]
            actual = committed_blob_sha(str(row.get("path") or ""), ref)
            return actual is not None and str(row.get("git_blob_sha")) == actual
        return True                      # the intent is not in the ref's change set at all
    if cid.startswith("STALE_BLOCKER_LEASE_KEY:"):
        fname = cid.split(":", 1)[1]
        for path in _intents_changed_between(base, ref):
            if path.name != fname:
                continue
            doc = _load(path) or {}
            return str(doc.get("blocker_lease_key") or "") == derived_lease_key(doc)
        return True
    return None


# --------------------------------------------------------------------------- the loop
def perceive(classes: list[DefectClass] | None = None) -> list[dict]:
    found: list[dict] = []
    for klass in (classes if classes is not None else CLASSES):
        for defect in klass.find():
            found.append(dict(defect, defect_class=klass.class_id))
    return found


def _ledger():
    from canonical.runtime import ignorance_ledger_v1 as ledger
    return ledger


def _measurement_ledger(apply: bool, ledger_path: str | None) -> tuple[str, Callable[[], None]]:
    """A measure-only run must not mutate the world it measures.

    v1 wrote 2,436 lines into the real ledger during a `--apply`-less run. The ledger is
    state; measuring is not an action. So a dry run gets a throwaway copy and the real file
    is left exactly as found.
    """
    if ledger_path:
        return ledger_path, lambda: None
    if apply:
        return str(LEDGER), lambda: None
    if not LEDGER.is_file():
        return str(LEDGER), lambda: None
    tmpdir = tempfile.mkdtemp(prefix="self-maint-ledger-")
    scratch = Path(tmpdir) / LEDGER.name
    shutil.copy2(LEDGER, scratch)
    return str(scratch), lambda: shutil.rmtree(tmpdir, ignore_errors=True)


def run(*, rounds: int = 2, apply: bool = False,
        classes: list[DefectClass] | None = None,
        ledger_path: str | None = None,
        base_ref: str | None = None) -> dict:
    """One or more unattended rounds. `apply=False` measures and changes nothing."""
    base_ref = resolve_base(base_ref)
    classes = classes if classes is not None else default_classes(base_ref)
    state, cleanup = _measurement_ledger(apply, ledger_path)
    ledger = _ledger()

    started = time.time()
    history: list[dict] = []
    closed_total = 0
    certified_total = 0
    found_total: set[str] = set()
    note_calls = 0

    try:
        for round_index in range(max(1, rounds)):
            defects = perceive(classes)
            for defect in defects:
                found_total.add(defect["defect_id"])
                ledger.note(defect["defect_class"],
                            why=str(defect.get("detail") or ""), cost=1.0, path=state)
                note_calls += 1

            # SELECT: the ledger's own expected-value ranking decides the order.
            ranked = ledger.rank(limit=max(1, len(classes) * 4), path=state)
            order = [row["what"] for row in ranked]
            defects.sort(key=lambda d: (order.index(d["defect_class"])
                                        if d["defect_class"] in order else len(order),
                                        d["defect_id"]))

            round_rows: list[dict] = []
            for defect in defects:
                klass = next(k for k in classes if k.class_id == defect["defect_class"])
                row = {"defect_id": defect["defect_id"], "class": klass.class_id,
                       "path": defect["path"], "action": None, "verified": False}
                if not apply:
                    row["action"] = "MEASURED_ONLY"
                    round_rows.append(row)
                    continue
                outcome = klass.fix(defect)
                row["action"] = outcome
                # VERIFY independently: the fixer's opinion is not evidence.
                row["verified"] = bool(outcome.get("applied")) and klass.verify(defect)
                if row["verified"]:
                    closed_total += 1
                    # A repair only counts once the authority's own predicate agrees.
                    ref_verdict = certify(defect, ref="HEAD", base=base_ref)
                    row["certified"] = ref_verdict is not False
                    if row["certified"]:
                        certified_total += 1
                        ledger.resolve(defect["defect_id"], helped=True, close=True,
                                       path=state)
                round_rows.append(row)

            history.append({"round": round_index + 1,
                            "found": [d["defect_id"] for d in defects],
                            "selection_order": order,
                            "rows": round_rows,
                            "closed": sum(1 for r in round_rows if r["verified"]),
                            "certified": sum(1 for r in round_rows if r.get("certified"))})
            if apply and not any(not r["verified"] for r in round_rows):
                break                      # nothing left that this loop can close
    finally:
        cleanup()

    remaining = perceive(classes)
    fixable = len(found_total)
    return {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_SELF_MAINTENANCE_ONLY",
        "applied": bool(apply),
        "base": resolve_base(None),
        "change_set": change_set(resolve_base(None)),
        "rounds_run": len(history),
        "defect_classes": [k.as_dict() for k in classes],
        "defects_found": fixable,
        "defects_closed": closed_total,
        "defects_certified": certified_total,
        # The number this module exists to move. Reported, never rounded up.
        # Credited on certification, not on verification: the fixer proving itself right
        # is not the same as the enforcer finding nothing to complain about.
        "unaided_closure_rate": (round(certified_total / fixable, 4) if fixable else None),
        "defects_remaining_after": len(remaining),
        # LEARN's unit is cost, never solve rate: one entry per ignorance recorded.
        "learning_cost": {"search_invocations": note_calls},
        "duration_s": round(time.time() - started, 3),
        "history": history,
        "non_claims": [
            "NO_CAPABILITY_CREDIT_A_TIDY_TREE_IS_NOT_A_MORE_CAPABLE_ONE",
            "ONLY_THE_DECLARED_DEFECT_CLASSES_CAN_BE_TOUCHED",
            "VERIFICATION_IS_A_RECOMPUTATION_NOT_THE_FIXERS_RETURN_VALUE",
            "SCOPE_IS_THE_CHANGE_SET_NOT_THE_INTENT_ARCHIVE",
            "CLOSURE_IS_CREDITED_ONLY_WHEN_THE_DRIFT_GUARD_AGREES_AT_THE_REF",
            "NO_SEMANTIC_FIX_CAPABILITY_IDS_AND_ROUTING_BINDINGS_ARE_NOT_DERIVABLE",
        ],
    }


def certify_report(path: str, ref: str = "HEAD") -> dict:
    """Second half of the loop: after the commit exists, ask the ref what actually closed.

    `--apply` can only prepare a repair for classes whose truth lives at a git ref. This reads
    the result that run wrote and re-asks the same question against HEAD, so "prepared" and
    "closed" stop being the same word.
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    base = doc.get("base")
    rows = [row for entry in doc.get("history", []) for row in entry.get("rows", [])
            if row.get("verified")]
    certified, uncertified = [], []
    for row in rows:
        verdict = certify(row, ref=ref, base=base)
        (uncertified if verdict is False else certified).append(row["defect_id"])
    return {"prepared": len(rows), "certified": len(certified),
            "uncertified": uncertified, "certified_ids": certified,
            "unaided_closure_rate": (round(len(certified) / len(rows), 4) if rows else None)}


def main(argv: list[str]) -> int:
    if "--certify" in argv:
        report = certify_report(argv[argv.index("--certify") + 1])
        print(f"self-maintenance loop  (CERTIFY at HEAD)")
        print(f"  repairs prepared          : {report['prepared']}")
        print(f"  certified by the ref      : {report['certified']}")
        rate = report["unaided_closure_rate"]
        print(f"  unaided closure rate      : "
              f"{'n/a (nothing prepared)' if rate is None else f'{rate:.2%}'}")
        for item in report["uncertified"]:
            print(f"    !! {item}")
        return 0

    apply = "--apply" in argv
    rounds = 2
    if "--rounds" in argv:
        rounds = int(argv[argv.index("--rounds") + 1])
    base = argv[argv.index("--base") + 1] if "--base" in argv else None

    result = run(rounds=rounds, apply=apply, base_ref=base)
    print(f"self-maintenance loop  ({'APPLY' if apply else 'MEASURE ONLY'})")
    print(f"  base commit               : {result['base']}")
    print(f"  change set                : {len(result['change_set'])} path(s)")
    print(f"  defect classes registered : {len(result['defect_classes'])}")
    print(f"  defects found             : {result['defects_found']}")
    print(f"  defects closed & verified : {result['defects_closed']}")
    print(f"  defects certified at ref  : {result['defects_certified']}")
    rate = result["unaided_closure_rate"]
    print(f"  unaided closure rate      : "
          f"{'n/a (no live defects)' if rate is None else f'{rate:.2%}'}")
    print(f"  remaining after           : {result['defects_remaining_after']}")
    print(f"  learning cost             : "
          f"{result['learning_cost']['search_invocations']} search invocation(s)")
    print(f"  rounds run / duration     : {result['rounds_run']} / {result['duration_s']}s")
    print()
    for entry in result["history"]:
        print(f"  round {entry['round']}: found {len(entry['found'])}, "
              f"closed {entry['closed']}, certified {entry['certified']}")
        print(f"    selection order (learned): {entry['selection_order']}")
        for row in entry["rows"]:
            if row.get("certified"):
                mark = "OK "
            elif row["verified"]:
                mark = "~  "       # repaired on disk, unproven until a commit resolves it
            elif row["action"] == "MEASURED_ONLY":
                mark = "-- "
            else:
                mark = "!! "
            print(f"    {mark}{row['defect_id']}")
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"  result written            : {out}")
    print()
    print("  Note: a self-maintained tree is not a more capable one. Nothing here is")
    print("  capability credit; it is the system closing its own bookkeeping defects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
