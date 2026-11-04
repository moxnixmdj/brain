#!/usr/bin/env python3
"""Derivations the system infers from its own records, then uses as live predicates.

The problem this exists to answer
---------------------------------
Version 1 of `self_maintenance_loop_v1` had three defect classes. A person wrote all three.
The loop executed them, reordered them by expected value, and repaired what they matched. It
looked autonomous and was not: the *set of things worth checking* was mine. Its ceiling was
my enumeration, so the improvement rate stayed proportional to how many sessions a human ran.

The repository already knows this failure by name. `CREATURE_BEHAVIOR_MAP_V1.md` is a list of
attempts that all died the same way -- a learned artifact that the acting path never used:
"the learned adaptation and suggested capabilities are not passed into that solver"; a
self-model that "resolves impasses on any shared token"; an agent with "zero learned patterns
of its own". Learning that does not become the predicate it was learned for is decoration.

So this module is built on one rule:

    a derivation is only counted as learned when it is the thing doing the checking.

What is inferred, not declared
------------------------------
This repository records, tens of thousands of times, a value that is a pure function of the
tree it sits in: a 40-hex blob id next to a path, a byte count next to a path, a total next
to the list it totals. Nobody told this module which function belongs to which field. It is
given a *hypothesis space* -- seven candidate derivations -- and it must work out, from the
records alone, which candidate each recorded number obeys.

That is a real inference, and it can be wrong in ways worth measuring:

    DISCOVER     for each record shape, which candidate reproduces the recorded value?
                 majority agreement establishes the attribution; ambiguity is reported as
                 ambiguity, never resolved by preference
    GENERALISE   (a) fit on some records of a shape, predict the records withheld -- does it
                     know the function or has it memorised values?
                 (b) fit on some shapes, predict a SHAPE it has never seen -- does a rule
                     learned about `git_blob_sha` transfer to a record that also carries
                     `size_bytes` and `source_class`?
    EXPLAIN      records inside an attributed shape that still disagree are anomalies, not
                 misattributions. Separating those two is the difference between a defect
                 nobody owes and a defect that is real
    IGNORANCE    shapes no candidate explains are the system's own ignorance, ranked, each
                 with the reason. This list is the input to the next widening
    WIDEN        for the shapes it cannot explain, compose a NEW derivation from primitives
                 and accept it only if it explains withheld records of that shape without
                 costing accuracy on the shapes already explained. A widening that fails is
                 reported as failed.
    ACT          every accepted derivation is returned as a live predicate and consumed by
                 `self_maintenance_loop_v1` as a defect class. The class count is a number
                 nobody wrote down.

No model. No network. No spend. Deterministic given the tree.

Usage::

    python3 canonical/tools/derivation_inference_v1.py                # measure and report
    python3 canonical/tools/derivation_inference_v1.py --write        # write the artifact
    python3 canonical/tools/derivation_inference_v1.py --widen        # attempt new derivations
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_DERIVATION_INFERENCE_V1"
ARTIFACT = "canonical/verification/DERIVATION_INFERENCE_V1.json"
MODEL_ARTIFACT = "canonical/verification/DERIVATION_MODEL_V1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
# A field needs this many records before an attribution is worth making.
MIN_SUPPORT = 3
# A role-level rule below the binding threshold is still a useful analogy -- but it is a
# suspicion, never a repair. Measured: hex40 fields that name a path are 85.35% blob ids.
ANALOGY_THRESHOLD = 0.80
# How much of a field a derivation must actually compute for before its accuracy means
# anything. Measured 2026-11-04: 32 of the 66 "attributed" fields had their winning candidate
# computing on under 90% of their records -- the worst at 2.5% -- because agreement was
# counted only where the candidate produced a value at all. A recipe that explains 2.5% of a
# field perfectly, and is silent about the rest, has not explained the field; it has found a
# corner of it. This constant is the difference between those two claims.
COVERAGE_MIN = 0.90
# Majority agreement required to call a shape attributed rather than undetermined.
BIND_THRESHOLD = 0.90

PATHISH = ("path", "source_path", "target", "blob_path", "file", "source_file",
           "artifact_path", "receipt_path")
SIZEISH = ("size", "size_bytes", "bytes", "byte_size")


# --------------------------------------------------------------------------- tree access
class Tree:
    """Memoised reads of the working tree, so 40k sites cost one pass over the files."""

    def __init__(self, root: Path = ROOT, ref: str | None = None) -> None:
        self.root = root
        self.ref = ref
        self._bytes: dict[str, bytes | None] = {}
        self._at_ref: dict[tuple[str, str], bytes | None] = {}
        self._derived: dict[tuple[str, str], Any] = {}
        self.derivation_calls = 0
        self._shallow: bool | None = None
        self._doc_commits: dict[str, str] | None = None

    @property
    def history_complete(self) -> bool:
        """Whether "this object is missing" can mean "it never existed" at all.

        Measured 2026-11-04: in this sandbox the clone was depth-1 (8 commits, 21,236 in the
        real repository). Every disagreement sampled under `git_blob_sha` was classified
        NEVER_AN_OBJECT -- 40 of 40 -- and the conclusion was wrong in every case. After
        `git fetch --unshallow`, 0 of 200 sampled disagreements were missing objects: 158
        were historical blobs this path really used to have, 42 were real objects that were
        never this path's.

        So the instrument must know what it cannot currently know. Without full history the
        only honest classification is UNVERIFIABLE_IN_SHALLOW_CLONE, and the report says the
        conclusion is provisional. A self-model that omits its own blindness is how the 841
        phantom defects happened.
        """
        if self._shallow is None:
            try:
                out = subprocess.check_output(["git", "rev-parse", "--is-shallow-repository"],
                                              cwd=self.root, text=True,
                                              stderr=subprocess.DEVNULL).strip()
                self._shallow = (out == "true")
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                self._shallow = True
        return not self._shallow

    def read(self, relpath: str) -> bytes | None:
        if relpath in self._bytes:
            return self._bytes[relpath]
        data = None
        if relpath and ".." not in Path(relpath).parts and not relpath.startswith("/"):
            path = self.root / relpath
            if path.is_file():
                try:
                    data = path.read_bytes()
                except OSError:
                    data = None
        self._bytes[relpath] = data
        return data

    def at_ref(self, relpath: str, ref: str | None = None) -> bytes | None:
        """Memoised: one subprocess per path, not one per recorded value."""
        ref = ref or "HEAD"
        key = (relpath, ref)
        if key in self._at_ref:
            return self._at_ref[key]
        data = None
        if relpath and ".." not in Path(relpath).parts and not relpath.startswith("/"):
            try:
                data = subprocess.check_output(["git", "show", f"{ref}:{relpath}"],
                                               cwd=self.root, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                data = None
        self._at_ref[key] = data
        return data


    def _load_doc_commits(self, depth: int = 4000) -> None:
        """doc -> the most recent commit that touched it, in ONE `git log` call.

        Asking git per document cost minutes: thousands of subprocesses for a fact that
        arrives in a single stream. Reading it once is the difference between an instrument
        that runs and one that does not.
        """
        self._doc_commits = {}
        try:
            out = subprocess.check_output(
                ["git", "log", f"-n{depth}", "--name-only", "--format=%x00%H"],
                cwd=self.root, text=True, errors="replace", stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return
        current = None
        for line in out.splitlines():
            if line.startswith("\x00"):
                current = line[1:].strip()
            elif line.strip() and current:
                self._doc_commits.setdefault(line.strip(), current)

    def document_commit(self, doc_path: str | None) -> str | None:
        if not doc_path:
            return None
        if self._doc_commits is None:
            self._load_doc_commits()
        return self._doc_commits.get(doc_path)

    def property_of(self, relpath: str, kind: str) -> Any:
        """Every file-level fact computed once. 365k records cost one pass, not seven."""
        key = (relpath, kind)
        if key in self._derived:
            return self._derived[key]
        self.derivation_calls += 1
        value = _MISS
        if kind == "exists":
            value = (self.root / relpath).is_file()
        elif kind == "at_head_exists":
            value = self.at_ref(relpath) is not None
        elif kind == "at_head_blob":
            committed = self.at_ref(relpath)
            value = git_blob_sha(committed) if committed is not None else _MISS
        else:
            data = self.read(relpath)
            if data is not None:
                if kind == "git_blob":
                    value = git_blob_sha(data)
                elif kind == "sha1":
                    value = sha1_bytes(data)
                elif kind == "sha256":
                    value = hashlib.sha256(data).hexdigest()
                elif kind == "size":
                    value = len(data)
            else:
                committed = self.at_ref(relpath)
                if committed is not None and kind in {"git_blob", "sha256"}:
                    value = (git_blob_sha(committed) if kind == "git_blob"
                             else hashlib.sha256(committed).hexdigest())
        self._derived[key] = value
        return value


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    """git's object id for these bytes -- the definition, not a call to git."""
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


# --------------------------------------------------------------------------- hypothesis space
class Candidate:
    """A named derivation, and the reason a person would ever suppose it."""

    def __init__(self, name: str, why: str, fn: Callable[[Mapping[str, Any], Tree], Any]):
        self.name = name
        self.why = why
        self.fn = fn

    def derive(self, site: Any, tree: Tree) -> Any:
        try:
            return self.fn(site, tree)
        except (KeyError, TypeError, ValueError, OSError):
            return _MISS

    def as_dict(self) -> dict:
        return {"name": self.name, "why": self.why}


class _Miss:
    def __repr__(self) -> str:
        return "MISS"


_MISS = _Miss()


_PATH_CACHE: dict[int, str | None] = {}



def _path_in(record: Mapping[str, Any]) -> str | None:
    key = id(record)
    if key in _PATH_CACHE:
        return _PATH_CACHE[key]
    found = None
    for name in PATHISH:
        value = record.get(name)
        if isinstance(value, str) and value.strip():
            found = value
            break
    _PATH_CACHE[key] = found
    _KEEPALIVE.append(record)
    return found


def _derive_git_blob(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else tree.property_of(path, "git_blob")

def _derive_sha1(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else tree.property_of(path, "sha1")

def _derive_sha256(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else tree.property_of(path, "sha256")

def _derive_size(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else tree.property_of(path, "size")

def _derive_sha1_of_path_string(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else sha1_bytes(path.encode("utf-8"))

def _derive_git_blob_at_head(site, tree):
    path = _path_in(site.record)
    return _MISS if not path else tree.property_of(path, "at_head_blob")

def _derive_git_blob_at_record_commit(site, tree):
    """The blob of the referenced file at the last commit that touched the record's document.

    Measured 2026-11-04: `git_blob_sha` binds at only 85.4% against the current blob, and at
    54.4% when the corpus is restricted to recent documents. Neither is a defect rate; both
    are the wrong hypothesis. A receipt records what the file was when the receipt was
    written. This candidate says that, and whether the records obey it is for the data to
    answer.
    """
    path = _path_in(site.record)
    if not path:
        return _MISS
    ref = tree.document_commit(site.doc)
    if not ref:
        return _MISS
    committed = tree.at_ref(path, ref)
    return _MISS if committed is None else git_blob_sha(committed)

def _derive_list_length(site, tree):
    for key, value in site.record.items():
        if isinstance(value, list) and len(value) > 0:
            return len(value)
    return _MISS

SPACE = [
    Candidate("git_blob_of_referenced_file",
              "the field is a content address of the file its record points at",
              _derive_git_blob),
    Candidate("git_blob_at_head",
              "the field is a content address of the file as last committed",
              _derive_git_blob_at_head),
    Candidate("git_blob_at_record_commit",
              "the blob of the referenced file at the commit that last wrote this record",
              _derive_git_blob_at_record_commit),
    Candidate("sha1_of_referenced_file", "a plain sha1 of the referenced bytes",
              _derive_sha1),
    Candidate("sha256_of_referenced_file", "a sha256 of the referenced bytes",
              _derive_sha256),
    Candidate("size_of_referenced_file", "a byte count of the referenced file",
              _derive_size),
    Candidate("sha1_of_path_string", "a hash of the path itself, not of its contents",
              _derive_sha1_of_path_string),
    Candidate("length_of_sibling_list", "a total that is just the length of a sibling list",
              _derive_list_length),
]

# Which candidates describe the tree as it is now, and which describe a moment in history.
# Only current-tensed derivations may ever rewrite a document: a historical derivation that
# disagrees is not a wrong record, it is a record written at a different commit.
CURRENCY = {
    "git_blob_of_referenced_file": "CURRENT",
    "sha1_of_referenced_file": "CURRENT",
    "sha256_of_referenced_file": "CURRENT",
    "size_of_referenced_file": "CURRENT",
    "length_of_sibling_list": "CURRENT",
    "sha1_of_path_string": "CURRENT",
    "git_blob_at_head": "CURRENT_AT_HEAD",
    "git_blob_at_record_commit": "HISTORICAL",
}


def value_class(value: Any) -> str | None:
    """Only values that could BE a derivation. Everything else is not a site.

    Booleans are excluded on purpose: a `true` in a policy document is a decision somebody
    made, not a computation over bytes, and a hypothesis space of byte-functions has nothing
    to say about it. Counting them would fill the ignorance list with 100,893 things that
    were never claims of derivability, which is the opposite of a self-model.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        if HEX40.match(value):
            return "hex40"
        if HEX64.match(value):
            return "hex64"
    return None


class Site:
    """One recorded value that claims to be derivable, and where it sits.

    Two levels, and the difference between them is the whole measurement:

      FIELD   (field name, value class) -- what the record is asserting
      CONTEXT (the sibling keys it keeps) -- one arrangement the assertion appears in

    Inference happens at FIELD level, where 40k records share a few hundred names and there
    is support enough to bind. Generalisation is measured at CONTEXT level: does a rule
    learned about `git_blob_sha` in 600 arrangements predict the arrangements it never saw?
    v1 of this file keyed on the exact sibling set, which produced 477 shapes with 523
    records -- nothing had support, and every state was INSUFFICIENT_SUPPORT. That is a
    measurement of my granularity, not of the repository.
    """

    __slots__ = ("doc", "pointer", "field", "record", "value", "cls")

    def __init__(self, doc, pointer, field, record, value, cls):
        self.doc = doc
        self.pointer = pointer
        self.field = field
        self.record = record
        self.value = value
        self.cls = cls

    @property
    def field_key(self) -> str:
        return f"{self.field}|{self.cls}"

    @property
    def role_key(self) -> str:
        """What generalises past the literal field name.

        `git_blob_sha`, `sha`, `source_blob_sha` and `parent_blob_sha` are different names
        for what may be the same assertion. A model keyed only on names can never say
        anything about a field it has not seen; a model keyed on (value class, does the
        record name a path) can, and that ability is what makes an inference transfer
        instead of accumulate.
        """
        named_path = "path" if _path_in(self.record) else "nopath"
        return f"{self.cls}|{named_path}"

    @property
    def context(self) -> str:
        return ",".join(sorted(k for k in self.record if k != self.field))

    @property
    def shape(self) -> str:
        return f"{self.field}|{self.cls}|{self.context}"

    @property
    def key(self) -> str:
        return f"{self.doc}#{self.pointer}"

    def as_dict(self) -> dict:
        return {"doc": self.doc, "pointer": self.pointer, "field": self.field,
                "shape": self.shape, "value": self.value}


def sites_in(doc: Any, doc_path: str, prefix: str = "") -> Iterable[Site]:
    if isinstance(doc, dict):
        for key, value in doc.items():
            pointer = f"{prefix}/{key}"
            cls = value_class(value)
            if cls is not None and not isinstance(value, (dict, list)):
                yield Site(doc_path, pointer, key, doc, value, cls)
            yield from sites_in(value, doc_path, pointer)
    elif isinstance(doc, list):
        for index, value in enumerate(doc):
            yield from sites_in(value, doc_path, f"{prefix}[{index}]")


def corpus(limit_files: int | None = None) -> list[Site]:
    out: list[Site] = []
    paths = sorted(set(list(ROOT.glob("canonical/**/*.json"))
                       + list(ROOT.glob("execution_guard/**/*.json"))))
    if limit_files:
        paths = paths[:limit_files]
    for path in paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        out.extend(sites_in(doc, rel))
    return out


# --------------------------------------------------------------------------- DISCOVER
def _agrees(derived: Any, recorded: Any) -> bool | None:
    if derived is _MISS:
        return None
    if isinstance(recorded, bool) or isinstance(derived, bool):
        return bool(derived) == bool(recorded) and type(derived) is type(recorded)
    return derived == recorded


# Derived values per (record, field). A record that carries three value-shaped fields is
# evaluated once, not three times, and the generalisation stages reuse the same answers
# instead of recomputing them. Cleared at the start of every `measure()`.
_RECORD_CACHE: dict[tuple[int, str], dict[str, Any]] = {}
_KEEPALIVE: list = []


def reset_cache() -> None:
    _RECORD_CACHE.clear()
    _PATH_CACHE.clear()
    _KEEPALIVE.clear()


def values_for(site: Site, tree: Tree,
               space: list[Candidate] | None = None) -> dict[str, Any]:
    space = space or SPACE
    key = (id(site.record), site.field)
    got = _RECORD_CACHE.get(key)
    if got is not None and len(got) == len(space):
        return got
    out = {c.name: c.derive(site, tree) for c in space}
    _RECORD_CACHE[key] = out
    _KEEPALIVE.append(site.record)          # ids stay unique while these are held
    return out


def _rate(candidates: Iterable[Candidate], sites: list[Site], tree: Tree) -> list[dict]:
    candidates = list(candidates)
    tallies: dict[str, list[int]] = {c.name: [0, 0] for c in candidates}
    for site in sites:
        for name, derived in values_for(site, tree, candidates).items():
            verdict = _agrees(derived, site.value)
            if verdict is None:
                continue
            tallies[name][1] += 1
            if verdict:
                tallies[name][0] += 1
    scored = [{"candidate": name, "agreements": ok, "computable": total,
               "rate": round(ok / total, 4),
               "coverage": round(total / len(sites), 4) if sites else None}
              for name, (ok, total) in tallies.items() if total]
    scored.sort(key=lambda r: (-r["rate"], -r["computable"], r["candidate"]))
    return scored


def attribute(sites: list[Site], tree: Tree,
              space: list[Candidate] | None = None) -> dict:
    """For every FIELD: which candidate explains it, how well, and is it ambiguous?

    Majority, not best-of-a-bad-lot. A field is attributed only when one candidate reproduces
    the great majority of its records; otherwise it is declared unexplained. The temptation to
    report the runner-up as an answer is how a system convinces itself it understands
    something it does not.
    """
    space = space or SPACE
    by_field: dict[str, list[Site]] = defaultdict(list)
    for site in sites:
        by_field[site.field_key].append(site)

    fields: dict[str, dict] = {}
    for key, group in by_field.items():
        scored = _rate(space, group, tree)
        best = scored[0] if scored else None
        contenders = [r["candidate"] for r in scored
                      if best and r["rate"] == best["rate"] and r["computable"] > 0]
        contexts = len({s.context for s in group})
        if best is None or best["computable"] < MIN_SUPPORT:
            state = "INSUFFICIENT_SUPPORT"
        elif (best.get("coverage") or 0) < COVERAGE_MIN:
            state = "LOW_COVERAGE"
        elif best["rate"] >= BIND_THRESHOLD:
            state = "UNDERDETERMINED" if len(contenders) > 1 else "ATTRIBUTED"
        else:
            state = "UNEXPLAINED"
        fields[key] = {
            "field": key, "records": len(group), "contexts": contexts, "state": state,
            "candidate": best["candidate"] if best else None,
            "rate": best["rate"] if best else None,
            "coverage": best.get("coverage") if best else None,
            "contenders": contenders if len(contenders) > 1 else [],
            "runner_up": scored[1] if len(scored) > 1 else None,
            "scored": scored,
        }
    return fields


def attribute_roles(sites: list[Site], tree: Tree,
                    space: list[Candidate] | None = None) -> dict:
    """The same inference one level up, on what a value class means in a record that names a
    path. This is what lets the model say something about a field name it has never seen."""
    space = space or SPACE
    by_role: dict[str, list[Site]] = defaultdict(list)
    for site in sites:
        by_role[site.role_key].append(site)
    roles: dict[str, dict] = {}
    for key, group in by_role.items():
        scored = _rate(space, group, tree)
        best = scored[0] if scored else None
        contenders = [r["candidate"] for r in scored
                      if best and r["rate"] == best["rate"] and r["computable"] > 0]
        if best is None or best["computable"] < MIN_SUPPORT:
            state = "INSUFFICIENT_SUPPORT"
        elif (best.get("coverage") or 0) < COVERAGE_MIN:
            state = "LOW_COVERAGE"
        elif len(contenders) > 1:
            state = "UNDERDETERMINED"
        elif best["rate"] >= BIND_THRESHOLD:
            state = "ATTRIBUTED"
        else:
            state = "TRANSFERABLE_BY_ANALOGY" if best["rate"] >= ANALOGY_THRESHOLD else "UNEXPLAINED"
        roles[key] = {"role": key, "records": len(group), "state": state,
                      "candidate": best["candidate"] if best else None,
                      "rate": best["rate"] if best else None, "scored": scored[:4]}
    return roles


# --------------------------------------------------------------------------- GENERALISE
def _split(sites: list[Site], mod: int = 2) -> tuple[list[Site], list[Site]]:
    """Deterministic split. No RNG, so a rerun cannot silently change the headline number."""
    train, holdout = [], []
    for site in sites:
        digest = hashlib.sha1(site.key.encode("utf-8")).hexdigest()
        (train if int(digest[:8], 16) % mod == 0 else holdout).append(site)
    return train, holdout


def generalise_within_field(sites: list[Site], tree: Tree) -> dict:
    """Fit on half the records of a field, predict the other half.

    Distinguishes a rule from memorised values: a system that has merely seen these exact
    documents cannot answer for ones withheld.
    """
    fields = attribute(sites, tree)
    per_candidate = {c.name: c for c in SPACE}
    by_field: dict[str, list[Site]] = defaultdict(list)
    for site in sites:
        if fields.get(site.field_key, {}).get("state") == "ATTRIBUTED":
            by_field[site.field_key].append(site)
    checked = agreed = 0
    failures = []
    bound_fields = 0
    for key, group in by_field.items():
        train, holdout = _split(group)
        if not train or not holdout:
            continue
        learned = attribute(train, tree).get(key)
        if not learned or learned["state"] != "ATTRIBUTED":
            continue                       # the rule did not survive withholding
        bound_fields += 1
        cand = per_candidate[learned["candidate"]]
        for site in holdout:
            verdict = _agrees(cand.derive(site, tree), site.value)
            if verdict is None:
                continue
            checked += 1
            if verdict:
                agreed += 1
            elif len(failures) < 10:
                failures.append({"field": key, "site": site.as_dict(),
                                 "candidate": cand.name})
    return {"fields_bound_on_half": bound_fields,
            "records_predicted": checked, "agreed": agreed,
            "accuracy": round(agreed / checked, 4) if checked else None,
            "note_on_denominator": "checked counts only records where the candidate computed; "
                                   "fields with low coverage are no longer attributed at all",
            "failures": failures,
            "note": "fit on half of each attributed field, predicted the other half"}


def generalise_across_contexts(sites: list[Site], tree: Tree) -> dict:
    """Learn a field's meaning from some record ARRANGEMENTS, predict arrangements never seen.

    This is the measurement that separates a rule from a lookup table. If the system only
    knows that `git_blob_sha` in one particular layout is a blob id, it has carried nothing.
    Each context (the company a field keeps) is withheld in effect by being counted
    separately: the rule is bound from the field's other neighbours and then scored on this
    one. A field whose meaning survives with its own neighbourhood removed is a field the
    system can carry.
    """
    fields = attribute(sites, tree)
    per_candidate = {c.name: c for c in SPACE}
    by_field: dict[str, list[Site]] = defaultdict(list)
    for site in sites:
        if fields.get(site.field_key, {}).get("state") == "ATTRIBUTED":
            by_field[site.field_key].append(site)

    checked = agreed = shapes = carried = 0
    detail = []
    for key, group in sorted(by_field.items()):
        contexts = sorted({s.context for s in group})
        if len(contexts) < 2:
            continue
        # bind the rule using records that are NOT in the largest context
        biggest = max(contexts, key=lambda c: sum(1 for s in group if s.context == c))
        others = [s for s in group if s.context != biggest]
        held = [s for s in group if s.context == biggest]
        if not others or not held:
            continue
        learned = attribute(others, tree).get(key)
        if not learned or learned["state"] != "ATTRIBUTED":
            continue
        cand = per_candidate[learned["candidate"]]
        hit = miss = 0
        for site in held:
            verdict = _agrees(cand.derive(site, tree), site.value)
            if verdict is None:
                continue
            hit += verdict
            miss += (not verdict)
        if hit + miss == 0:
            continue
        shapes += 1
        checked += hit + miss
        agreed += hit
        if learned["candidate"] == fields[key]["candidate"]:
            carried += 1
        detail.append({"field": key, "withheld_context": biggest, "records": hit + miss,
                       "agreed": hit, "candidate": learned["candidate"]})
    return {"fields_tested": shapes,
            "contexts_withheld_and_predicted": shapes,
            "rule_identical_when_neighbourhood_removed": carried,
            "records_predicted": checked, "agreed": agreed,
            "accuracy": round(agreed / checked, 4) if checked else None,
            "detail": sorted(detail, key=lambda d: -d["records"])[:10],
            "note": "each field's largest context withheld; rule bound from the others"}


# --------------------------------------------------------------------------- EXPLAIN
def anomalies(sites: list[Site], tree: Tree, shapes: dict | None = None) -> list[dict]:
    """Inside an attributed shape, a disagreeing record is an anomaly -- not noise.

    Keeping these separate from misattribution is the whole difference between the 841
    phantom defects of loop v1 and a real defect: a record whose shape is understood, whose
    derivation is known, and whose value no longer follows, is a record that is wrong.
    """
    shapes = shapes or attribute(sites, tree)
    per_candidate = {c.name: c for c in SPACE}
    out = []
    for site in sites:
        info = shapes.get(site.field_key)
        if not info or info["state"] != "ATTRIBUTED":
            continue
        cand = per_candidate[info["candidate"]]
        if _agrees(cand.derive(site, tree), site.value) is False:
            out.append({"site": site.as_dict(), "candidate": cand.name,
                        "derived": cand.derive(site, tree)})
    return out


# --------------------------------------------------------------------------- DIAGNOSE
def _object_exists(sha: str) -> bool:
    try:
        subprocess.check_output(["git", "cat-file", "-e", sha], cwd=ROOT,
                                stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def _historical_blobs(path: str, limit: int = 60) -> set[str]:
    """Every blob this path has ever had, within a bounded number of commits."""
    shas: set[str] = set()
    try:
        commits = subprocess.check_output(
            ["git", "rev-list", f"-n{limit}", "--all", "--", path],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL).split()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return shas
    for commit in commits:
        try:
            shas.add(subprocess.check_output(["git", "rev-parse", f"{commit}:{path}"],
                                             cwd=ROOT, text=True,
                                             stderr=subprocess.DEVNULL).strip())
        except (subprocess.CalledProcessError, OSError):
            continue
    return shas


def diagnose_residuals(field_key: str, sites: list[Site], tree: Tree,
                       sample: int = 40, candidate: str | None = None) -> dict:
    """Why do records in an almost-explained field disagree? Five causes, not one.

    A field at 85% is the interesting case, and lumping its residuals into "unexplained" is
    the mistake `self_maintenance_loop_v1` v1 made when it called 841 historical records
    defects. So each DISAGREEMENT is interrogated (agreeing records are not sampled -- the
    first version did that and reported 31 "current" values, which is a measurement of the
    wrong population):

      CURRENT                  the value matches the file now; only reachable when the record
                               carries several path-ish keys and the wrong one was chosen
      PATH_MISSING             the record names a file this tree does not have
      HISTORICAL_BLOB          the value is a real object this repository has held for that
                               path -- an archive record doing its job, not a debt
      REAL_OBJECT_OTHER_PATH   the value is a real object, but never this path's blob
      NEVER_AN_OBJECT          the value is not in the object database at all. The repository
                               is quoting a sha that never existed
      NO_PATH_FIELD            the record carries a value with nothing to derive it from

    Only NEVER_AN_OBJECT is unambiguously a lie. The rest is archive discipline, and saying
    so is the difference between a self-model and a defect generator.
    """
    group = [s for s in sites if s.field_key == field_key]
    if candidate is None:
        candidate = attribute(group, tree).get(field_key, {}).get("candidate")
    per_candidate = {c.name: c for c in SPACE}
    cand = per_candidate.get(candidate) if candidate else None

    disagreements = []
    for site in group:
        if cand is not None and _agrees(values_for(site, tree).get(cand.name), site.value) is not False:
            continue
        disagreements.append(site)

    tally = Counter()
    examples: dict[str, list[dict]] = defaultdict(list)
    for site in disagreements[:sample]:
        path = _path_in(site.record)
        value = str(site.value)
        if not path:
            cause = "NO_PATH_FIELD"
        elif tree.property_of(path, "exists") is not True:
            cause = "PATH_MISSING"
        elif tree.property_of(path, "git_blob") == value:
            cause = "CURRENT"
        elif not _object_exists(value):
            cause = ("NEVER_AN_OBJECT" if tree.history_complete
                     else "UNVERIFIABLE_IN_SHALLOW_CLONE")
        elif value in _historical_blobs(path):
            cause = "HISTORICAL_BLOB"
        else:
            cause = "REAL_OBJECT_OTHER_PATH"
        tally[cause] += 1
        if len(examples[cause]) < 3:
            examples[cause].append({"path": path, "value": value,
                                    "site": site.as_dict()})
    return {"field": field_key, "records": len(group),
            "disagreements": len(disagreements),
            "sampled_disagreements": min(sample, len(disagreements)),
            "candidate": candidate, "causes": dict(tally), "examples": dict(examples),
            "history_complete": tree.history_complete,
            "conclusion": ("PROVISIONAL_THE_CLONE_IS_SHALLOW_A_MISSING_OBJECT_MAY_ONLY_BE_UNFETCHED"
                           if not tree.history_complete else "FINAL"),
            "note": ("only NEVER_AN_OBJECT is a defect; the rest is archive discipline. "
                     "In a shallow clone not even that can be concluded.")}


# --------------------------------------------------------------------------- IGNORANCE
def ignorance(shapes: Mapping[str, dict], limit: int = 12) -> dict:
    """What the system cannot explain, ranked, with the reason -- the next thing to widen.

    Ranked by how many records are stranded, because a shape that strands 3,974 records is
    worth more than one that strands 3. This list is not a report; it is the queue.
    """
    unbound = [v for v in shapes.values() if v["state"] in {"UNEXPLAINED",
                                                            "INSUFFICIENT_SUPPORT",
                                                            "UNDERDETERMINED"}]
    unbound.sort(key=lambda v: (-v["records"], v.get("shape") or v.get("field", "")))
    reasons = Counter(v["state"] for v in unbound)
    stranded = sum(v["records"] for v in unbound)
    return {
        "shapes_unexplained": len(unbound),
        "records_stranded": stranded,
        "by_reason": dict(reasons),
        "ranked": [{"shape": v.get("shape") or v.get("field"), "records": v["records"], "state": v["state"],
                    "best_candidate": v["candidate"], "best_rate": v["rate"],
                    "contenders": v["contenders"]}
                   for v in unbound[:limit]],
    }


# --------------------------------------------------------------------------- WIDEN
def composite_candidates(record: Mapping[str, Any]) -> list[Candidate]:
    """Derivations nobody put in the space, composed for a shape that defeated all of them.

    Each one is a real hypothesis about a record this system could not explain, and each is
    quoted with the reason it might hold. They are not accepted here; they are proposed, then
    tested against withheld records like anything else.
    """
    paths = sorted({v for k, v in record.items()
                    if isinstance(v, str) and (v.endswith((".py", ".json", ".md"))
                                               or "/" in v)})
    out: list[Candidate] = []
    if paths:
        joined = "\n".join(paths).encode("utf-8")

        def _concat_sha1(_site, _tree, blob=joined):
            return sha1_bytes(blob)

        out.append(Candidate("sha1_of_sorted_path_list",
                             "the value covers every path the record names, not one of them",
                             _concat_sha1))
        if len(paths) >= 2:
            def _concat_git(_site, _tree, blob=joined):
                return git_blob_sha(blob)

            out.append(Candidate("git_blob_of_sorted_path_list",
                                 "a content address over the record's whole path set",
                                 _concat_git))
        if any((ROOT / p).is_dir() for p in paths):
            def _dir_count(_site, _tree, ps=paths):
                total = 0
                for p in ps:
                    directory = ROOT / p
                    if directory.is_dir():
                        total += sum(1 for _ in directory.rglob("*") if _.is_file())
                return total

            out.append(Candidate("recursive_file_count_of_referenced_dirs",
                                 "a total over the tree under the referenced directory",
                                 _dir_count))
    return out


def widen(sites: list[Site], tree: Tree, *, target_state: Iterable[str] = ("UNEXPLAINED",),
          limit: int = 6) -> dict:
    """Try to bring a shape the system could not explain into the set it can.

    Acceptance is falsification, not enthusiasm: the new derivation must explain the withheld
    half of the target shape at the same threshold as anything else, AND must not reduce
    agreement on the shapes already explained. A widening that costs the existing model is
    rejected even when it wins on the target.
    """
    shapes = attribute(sites, tree)
    baseline = {s: v for s, v in shapes.items() if v["state"] == "ATTRIBUTED"}
    baseline_rate = _mean_rate(baseline)

    by_shape: dict[str, list[Site]] = defaultdict(list)
    for site in sites:
        by_shape[site.shape].append(site)

    targets = [v for v in shapes.values() if v["state"] in set(target_state)]
    targets.sort(key=lambda v: (-v["records"], v["shape"]))
    accepted, rejected = [], []

    for target in targets[:limit]:
        group = by_shape[target["shape"]]
        train, holdout = _split(group)
        if not holdout:
            continue
        proposals = composite_candidates(group[0].record)
        if not proposals:
            rejected.append({"shape": target["shape"], "records": len(group),
                             "reason": "NO_COMPOSITION_APPLIES"})
            continue

        # Does the proposal bind the withheld records of the target shape?
        best = None
        for cand in proposals:
            g = _grade(cand, train, tree)
            if g is None:
                continue
            if best is None or g["rate"] > best[1]["rate"]:
                best = (cand, g)
        if best is None:
            rejected.append({"shape": target["shape"], "records": len(group),
                             "reason": "NO_PROPOSAL_BINDS_TRAINING_RECORDS"})
            continue
        cand, train_grade = best
        hold_grade = _grade(cand, holdout, tree)
        if hold_grade is None or train_grade["rate"] < BIND_THRESHOLD:
            rejected.append({"shape": target["shape"], "records": len(group),
                             "reason": "PROPOSAL_DOES_NOT_BIND",
                             "candidate": cand.name,
                             "train_rate": train_grade["rate"] if train_grade else None})
            continue
        if hold_grade["rate"] < BIND_THRESHOLD:
            rejected.append({"shape": target["shape"], "records": len(group),
                             "reason": "DOES_NOT_GENERALISE_TO_WITHHELD_RECORDS",
                             "candidate": cand.name,
                             "train_rate": train_grade["rate"],
                             "holdout_rate": hold_grade["rate"]})
            continue
        # Cost check: does the enlarged space damage what already worked?
        enlarged = _mean_rate_with(baseline, cand, by_shape, tree)
        if baseline_rate is not None and enlarged is not None and enlarged < baseline_rate:
            rejected.append({"shape": target["shape"], "records": len(group),
                             "reason": "COSTS_ACCURACY_ON_ATTRIBUTED_SHAPES",
                             "baseline": baseline_rate, "enlarged": enlarged})
            continue
        accepted.append({"shape": target["shape"], "records": len(group),
                         "candidate": cand.name, "why": cand.why,
                         "train_rate": train_grade["rate"],
                         "holdout_rate": hold_grade["rate"]})
        target["state"] = "ATTRIBUTED_BY_WIDENING"
        target["candidate"] = cand.name

    return {"attempted": min(len(targets), limit), "accepted": accepted,
            "rejected": rejected,
            "baseline_mean_rate": baseline_rate,
            "shapes_after": sum(1 for v in shapes.values()
                                if str(v["state"]).startswith("ATTRIBUTED"))}


def _grade(cand: Candidate, sites: list[Site], tree: Tree) -> dict | None:
    ok = total = 0
    for site in sites:
        verdict = _agrees(cand.derive(site, tree), site.value)
        if verdict is None:
            continue
        total += 1
        ok += 1 if verdict else 0
    if total < 2:
        return None
    return {"agreements": ok, "computable": total, "rate": round(ok / total, 4)}


def _mean_coverage(shapes: Mapping[str, dict]) -> float | None:
    vals = [v["coverage"] for v in shapes.values() if v.get("coverage") is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def _mean_rate(shapes: Mapping[str, dict]) -> float | None:
    rates = [v["rate"] for v in shapes.values() if v.get("rate") is not None]
    return round(sum(rates) / len(rates), 4) if rates else None


def _mean_rate_with(baseline, cand: Candidate, by_shape, tree) -> float | None:
    rates = [v["rate"] for v in baseline.values() if v.get("rate") is not None]
    for shape, group in by_shape.items():
        if shape in baseline:
            continue
        grade = _grade(cand, group, tree)
        if grade:
            rates.append(grade["rate"])
    return round(sum(rates) / len(rates), 4) if rates else None


# --------------------------------------------------------------------------- ACT
def live_predicates(sites: list[Site] | None = None, tree: Tree | None = None) -> dict:
    """The learned thing, returned as the checking thing.

    Every attributed shape becomes a predicate that re-derives a recorded value from the tree
    and says whether it still holds. `self_maintenance_loop_v1` consumes these as defect
    classes, which is what stops this module from becoming another learned artifact nobody
    acts on -- the failure `CREATURE_BEHAVIOR_MAP_V1.md` records five times over.
    """
    tree = tree or Tree()
    sites = sites if sites is not None else corpus()
    shapes = attribute(sites, tree)
    per_candidate = {c.name: c for c in SPACE}

    def make(field_key: str):
        info = shapes[field_key]
        cand = per_candidate[info["candidate"]]

        def holds(record: Mapping[str, Any]) -> bool | None:
            derived = cand.derive(record, tree)
            return _agrees(derived, record.get(field_key.split("|", 1)[0]))

        return holds

    return {field: make(field) for field, v in shapes.items()
            if v["state"] == "ATTRIBUTED"}


# --------------------------------------------------------------------------- MODEL
_MODEL_CACHE: dict | None = None


def model_document(limit_files: int | None = None) -> dict:
    """Learn every field's and role's meaning once, in a form that can be written down."""
    reset_cache()
    tree = Tree()
    sites = corpus(limit_files=limit_files)
    fields = attribute(sites, tree)
    roles = attribute_roles(sites, tree)
    return {
        "schema": SCHEMA + "_MODEL",
        "learned_at_commit": (subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                      text=True).strip()
                              if _git_ok() else None),
        "history_complete": tree.history_complete,
        "records_seen": len(sites),
        # Only fields the system actually learned something about. 37,875 fields with a
        # single record each carry no knowledge, and writing them out made a 7.5 MB artifact
        # that said nothing; this is 200 KB that does.
        "fields": {k: {"state": v["state"], "candidate": v["candidate"], "rate": v["rate"],
                       "coverage": v.get("coverage"),
                       "records": v["records"], "contexts": v["contexts"],
                       "runner_up": v["runner_up"]}
                   for k, v in fields.items() if v["state"] != "INSUFFICIENT_SUPPORT"},
        "fields_not_written": sum(1 for v in fields.values()
                                  if v["state"] == "INSUFFICIENT_SUPPORT"),
        "roles": roles,
        "hypothesis_space": [c.as_dict() for c in SPACE],
        "non_claims": [
            "THE_HYPOTHESIS_SPACE_IS_SUPPLIED_THE_ATTRIBUTION_IS_INFERRED",
            "AN_ATTRIBUTION_IS_AGREEMENT_WITH_RECORDS_NOT_CAUSAL_PROOF",
        ],
    }


def _git_ok() -> bool:
    try:
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def save_model(path: str | Path = None, *, limit_files: int | None = None) -> dict:
    doc = model_document(limit_files=limit_files)
    out = Path(path) if path else ROOT / MODEL_ARTIFACT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def load_model(path: str | Path = None, *, recompute_if_missing: bool = True) -> dict | None:
    """Persistence of learning. The creature map's most repeated failure is learned things
    that vanish with the process; this is stored on disk and read back."""
    global _MODEL_CACHE
    path = Path(path) if path else ROOT / MODEL_ARTIFACT
    if path.is_file():
        try:
            _MODEL_CACHE = json.loads(path.read_text(encoding="utf-8"))
            return _MODEL_CACHE
        except (OSError, ValueError):
            pass
    if not recompute_if_missing:
        return None
    return model_document()


# --------------------------------------------------------------------------- ACT ON IT
def pointer_parts(pointer: str) -> list[str | int]:
    """"/a/b[0]/c" -> ["a", "b", 0, "c"]; nested indices ("/x[1][2]") included."""
    parts: list[str | int] = []
    for chunk in [c for c in pointer.split("/") if c]:
        head, sep, rest = chunk.partition("[")
        if head:
            parts.append(head)
        if not sep:
            continue
        for index in re.findall(r"\[(\d+)\]", "[" + rest):
            parts.append(int(index))
    return parts


def get_at(doc: Any, pointer: str) -> Any:
    node = doc
    for part in pointer_parts(pointer):
        node = node[part]
    return node


def set_at(doc: Any, pointer: str, value: Any) -> None:
    parts = pointer_parts(pointer)
    node = doc
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def make_derived_value_class(base_ref: str | None = None, *, model: dict | None = None,
                             model_path: str | Path | None = None) -> Any:
    """The learned thing, used as the checking thing -- the loop's fourth defect class.

    Each recorded value in the change set is checked against what the persisted model says
    its field means. Two tiers, kept apart on purpose:

      EXPLICIT   the field itself was attributed at >= 90% agreement. A disagreement is a
                 defect, and the fix writes the derived value.
      ANALOGY    the field name was never seen, but its role (value class + whether the
                 record names a path) is understood at >= 80%. A disagreement is a
                 SUSPICION and is reported, never repaired -- there is no version of "I
                 guessed what this field means" that should silently rewrite a document.
    """
    from canonical.tools.self_maintenance_loop_v1 import DefectClass

    def _loop():
        """The loop module, resolved at call time.

        Binding `change_set`, `_load` and `ROOT` at construction time captured the real ones,
        so the class kept scanning the real tree no matter where it was pointed -- a coupling
        that only shows up when someone attempts to test it.
        """
        from canonical.tools import self_maintenance_loop_v1 as loop
        return loop

    def _model() -> dict:
        nonlocal model
        if model is None:
            model = load_model(model_path) or model_document()
        return model

    def find() -> list[dict]:
        doc_model = _model()
        fields = doc_model.get("fields", {})
        roles = doc_model.get("roles", {})
        tree = Tree()
        out: list[dict] = []
        for rel in _loop().change_set(base_ref):
            if not rel.endswith(".json"):
                continue
            doc = _loop()._load(_loop().ROOT / rel)
            if not isinstance(doc, dict):
                continue
            for site in sites_in(doc, rel):
                info = fields.get(site.field_key)
                tier = "EXPLICIT"
                if not info or info.get("state") != "ATTRIBUTED":
                    info = roles.get(site.role_key)
                    tier = "ANALOGY"
                if not info:
                    continue
                if tier == "EXPLICIT" and info.get("state") != "ATTRIBUTED":
                    continue
                if tier == "ANALOGY" and info.get("state") not in {
                        "ATTRIBUTED", "TRANSFERABLE_BY_ANALOGY"}:
                    continue
                cand = {c.name: c for c in SPACE}.get(info.get("candidate"))
                if cand is None:
                    continue
                derived = cand.derive(site, tree)
                if _agrees(derived, site.value) is not False:
                    continue
                out.append({"defect_id": f"DERIVED_VALUE_DISAGREES:{site.doc}:{site.pointer}",
                            "path": site.doc, "pointer": site.pointer, "field": site.field,
                            "detail": f"{site.field} does not follow {cand.name} ({tier})",
                            "recorded": site.value, "derived": derived,
                            "candidate": cand.name, "tier": tier,
                            "confidence": info.get("rate")})
        return out

    def fix(defect: dict) -> dict:
        if defect.get("tier") != "EXPLICIT":
            return {"applied": False, "reason": "ANALOGY_IS_A_SUSPICION_NOT_A_REPAIR"}
        path = _loop().ROOT / defect["path"]
        doc = _loop()._load(path)
        if not isinstance(doc, dict):
            return {"applied": False, "reason": "DOC_UNREADABLE"}
        try:
            current = get_at(doc, defect["pointer"])
        except (KeyError, IndexError, TypeError):
            return {"applied": False, "reason": "POINTER_GONE"}
        if current != defect["recorded"]:
            return {"applied": False, "reason": "VALUE_CHANGED_SINCE_FIND"}
        set_at(doc, defect["pointer"], defect["derived"])
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"applied": True, "before": current, "after": defect["derived"]}

    def verify(defect: dict) -> bool:
        """Independent: re-read the document from disk and re-derive from the tree.

        No use of `defect["derived"]`, no use of the fixer's return value.
        """
        doc = _loop()._load(_loop().ROOT / defect["path"])
        if not isinstance(doc, dict):
            return False
        parent = defect["pointer"].rsplit("/", 1)[0] or "/"
        try:
            record = get_at(doc, parent)
            recorded = get_at(doc, defect["pointer"])
        except (KeyError, IndexError, TypeError):
            return False
        if not isinstance(record, Mapping):
            return False
        cand = {c.name: c for c in SPACE}.get(defect["candidate"])
        if cand is None:
            return False
        site = type("S", (), {"record": record, "doc": defect["path"]})()
        return _agrees(cand.derive(site, Tree()), recorded) is True

    return DefectClass(
        class_id="DERIVED_VALUE_DISAGREES",
        describes="a recorded value no longer follows the derivation the system inferred for its field",
        find=find, fix=fix, verify=verify)


# --------------------------------------------------------------------------- report
def measure(*, widen_shapes: bool = False, limit_files: int | None = None) -> dict:
    reset_cache()
    tree = Tree()
    sites = corpus(limit_files=limit_files)
    shapes = attribute(sites, tree)
    counts = Counter(v["state"] for v in shapes.values())
    attributed = {s: v for s, v in shapes.items() if v["state"] == "ATTRIBUTED"}

    within = generalise_within_field(sites, tree)
    across = generalise_across_contexts(sites, tree)
    anom = anomalies(sites, tree, shapes)
    roles = attribute_roles(sites, tree)
    residuals = diagnose_residuals("git_blob_sha|hex40", sites, tree,
                                   sample=60) if "git_blob_sha|hex40" in shapes else None
    ign = ignorance(shapes)
    widening = widen(sites, tree) if widen_shapes else None
    if widening:
        counts = Counter(v["state"] for v in shapes.values())

    return {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_INFERENCE_MEASUREMENT_ONLY",
        "instrument": "DERIVATION_INFERENCE_FROM_OWN_RECORDS",
        "corpus": {"sites": len(sites), "fields": len(shapes),
                   "contexts": len({s.shape for s in sites}),
                   "documents": len({s.doc for s in sites})},
        "hypothesis_space": [c.as_dict() for c in SPACE],
        "fields_by_state": dict(counts),
        "attributed_fields": len(attributed),
        "attribution_agreement": _mean_rate(attributed),
        "attribution_coverage": _mean_coverage(attributed),
        "coverage_floor": COVERAGE_MIN,
        "generalisation_within_field": within,
        "generalisation_across_contexts": across,
        "anomalies": {"count": len(anom), "examples": anom[:8]},
        "ignorance": ign,
        "roles": {k: {"state": v["state"], "candidate": v["candidate"], "rate": v["rate"],
                      "records": v["records"]} for k, v in roles.items()},
        "residual_diagnosis": residuals,
        "history_complete": tree.history_complete,
        "widening": widening,
        "non_claims": [
            "NO_CAPABILITY_CREDIT_KNOWING_A_HASH_IS_NOT_BEING_CAPABLE",
            "HYPOTHESIS_SPACE_IS_SUPPLIED_BY_A_PERSON_THE_ATTRIBUTION_IS_NOT",
            "AN_ATTRIBUTION_IS_AGREEMENT_WITH_DATA_NOT_PROOF_OF_CAUSATION",
            "ACCURACY_WITHOUT_COVERAGE_IS_A_MEASUREMENT_OF_THE_SUBSET_THAT_WORKED",
            "ARCHIVE_ANOMALIES_ARE_HISTORY_NOT_DEBT",
        ],
    }


def main(argv: list[str]) -> int:
    if "--model" in argv:
        doc = save_model()
        print(f"model learned: {len(doc['fields'])} fields, {len(doc['roles'])} roles, "
              f"{doc['records_seen']} records, history_complete={doc['history_complete']}")
        print(f"written: {MODEL_ARTIFACT}")
        return 0

    report = measure(widen_shapes="--widen" in argv,
                     limit_files=int(argv[argv.index("--limit") + 1])
                     if "--limit" in argv else None)
    print("derivation inference  (from the repository's own records)")
    print(f"  documents / records       : {report['corpus']['documents']} / "
          f"{report['corpus']['sites']}")
    print(f"  record contexts seen      : {report['corpus']['contexts']}")
    print(f"  hypothesis space          : {len(report['hypothesis_space'])} candidates "
          f"(supplied); attribution (inferred)")
    print(f"  fields by state           : {report['fields_by_state']}")
    print(f"  attribution agreement     : {report['attribution_agreement']}")
    print(f"  attribution coverage      : {report['attribution_coverage']} "
          f"(floor {report['coverage_floor']})")
    within = report["generalisation_within_field"]
    across = report["generalisation_across_contexts"]
    print(f"  held-out records (same shape) : {within['agreed']}/{within['records_predicted']}"
          f"  accuracy {within['accuracy']}")
    print(f"  withheld contexts (transfer)  : {across['agreed']}/{across['records_predicted']}"
          f"  accuracy {across['accuracy']}  over {across['contexts_withheld_and_predicted']} withheld contexts")
    print(f"  anomalies inside known fields : {report['anomalies']['count']}")
    resid = report.get("residual_diagnosis") or {}
    if resid.get("causes"):
        print(f"  residual causes ({resid['disagreements']} disagree, "
              f"{resid['sampled_disagreements']} sampled) : {resid['causes']}")
        print(f"  conclusion                : {resid['conclusion']}")
    ign = report["ignorance"]
    print(f"  fields it cannot explain      : {ign['shapes_unexplained']} "
          f"stranding {ign['records_stranded']} records  {ign['by_reason']}")
    for row in ign["ranked"][:6]:
        print(f"    ?? {row['records']:5d} rec  {row['state']:20s} {row['shape'][:96]}")
    if report["widening"]:
        w = report["widening"]
        print(f"  widening                  : tried {w['attempted']}, "
              f"accepted {len(w['accepted'])}, rejected {len(w['rejected'])}")
        for row in w["accepted"]:
            print(f"    ++ {row['candidate']} binds {row['records']} records "
                  f"(holdout {row['holdout_rate']}) {row['shape'][:70]}")
        for row in w["rejected"][:6]:
            print(f"    -- {row['reason']} {row.get('candidate', '')} {row['shape'][:60]}")
    if "--write" in argv:
        out = ROOT / ARTIFACT
        out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"  written: {ARTIFACT}")
    print()
    print("  Note: knowing that a recorded number equals a function of the tree is not")
    print("  capability. It is the system working out what its own records mean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
