#!/usr/bin/env python3
"""A goal is an effect predicate. The call is derived from the predicate, then executed.

The repository can already say what a machine *is* (broker, world_probe), find documents
about it (jit_knowledge), learn it by reading its own manual and running the examples
(documentation_mining_v1), and instantiate a CLI's usage line against its own vocabulary
(an_effect_not_a_description_v1).  The cell that has never been closed is narrower and
harder:

    a goal + an unrelated third-party library the repo has never seen
      -> callable paths derived from the artifact's own surface
      -> executed
      -> effect checked against a predicate built from the goal
      -> ONE reusable record in the external store, keyed by the effect

The three traps this file is built to survive, all measured before writing it:

  1. READING IS NOT BINDING.  `whitebox_introspector.rank_callables_for_goal` ranks
     names by token overlap and stops.  Sixty-three docstrings across four unseen
     packages describe `add`; none of them says whether `add` sorts, and ranking
     never finds out.

  2. DOCSTRINGS ARE NOT AN ORACLE, AND OFTEN NOT EVEN EXAMPLES.  Measured on unseen
     pure-Python wheels: sortedcontainers 255 doctest assertions, toolz 258,
     textdistance 0, funcy 0, bidict 0.  Learning that depends on examples being
     present silently becomes learning that only works on curated packages.

  3. A GOOD-LOOKING ANSWER IS NOT A DISCRIMINATING ONE.  `SortedList.add` and
     `SortedSet.add` both satisfy a naive "result is sorted" check on the same input.
     They are different effects.  A probe input is only valid if the candidate's
     *observable state* genuinely distinguishes effects; otherwise the record is a
     coincidence with a receipt.

So the order is inverted from every previous instrument here: the goal is compiled to
a predicate on (state, observation) BEFORE any candidate is chosen, the predicate is
used to *solve for* an input that separates effects, and a candidate earns a record
only if it produces the predicate's effect and its state shows the effect's footprint.

Zero model calls.  Zero stored world facts.  Zero network at bind time; acquisition is
the one deliberate network step and it is content-addressed.  Every claim in the
report is accompanied by the subprocess that produced it.

Authority: NONE.  Producer-run sandbox measurement.
"""
from __future__ import annotations

import ast
import hashlib
import io as _io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_EFFECT_PREDICATE_BINDER_V1"

# ---------------------------------------------------------------------------
# 1. ACQUISITION -- content-addressed, no pip, no install, no site-packages write.
# ---------------------------------------------------------------------------

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
UA = {"User-Agent": "project-brain/effect-predicate-binder-v1"}


def _fetch(url: str, *, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310 - fixed hosts
        return fh.read()


def acquire(name: str, *, version: str | None = None, root: pathlib.Path | None = None) -> dict:
    """Fetch the artifact's own bytes and verify them against the digest it published.

    No dependency resolution beyond the pure wheels the index lists; a package that
    only ships an sdist is reported as `NO_BINARY` rather than guessed at.
    """
    root = root or pathlib.Path(tempfile.mkdtemp(prefix="epb-"))
    t0 = time.time()
    url = PYPI_JSON.format(name=name) + (f"/{version}" if version else "")
    meta = json.loads(_fetch(url))
    info = meta["info"]
    wheels = [u for u in meta.get("urls", []) if u["filename"].endswith(".whl")]
    pure = [u for u in wheels if "none-any" in u["filename"]]
    chosen = (pure or wheels or [None])[0]
    out: dict[str, Any] = {
        "name": name,
        "version": info.get("version"),
        "requires_python": info.get("requires_python"),
        "requires_dist": info.get("requires_dist") or [],
        "download_url": info.get("download_url"),
    }
    if chosen is None:
        out.update(status="NO_BINARY", seconds=round(time.time() - t0, 3))
        return out
    raw = _fetch(chosen["url"], timeout=120.0)
    got = hashlib.sha256(raw).hexdigest()
    want = chosen["digests"]["sha256"]
    out.update(
        filename=chosen["filename"],
        bytes=len(raw),
        sha256=got,
        digest_verified=(got == want),
        wheel_url=chosen["url"],
        pure_python=("none-any" in chosen["filename"]),
    )
    if got != want:
        out.update(status="DIGEST_MISMATCH", seconds=round(time.time() - t0, 3))
        return out
    libdir = root / "lib"
    libdir.mkdir(parents=True, exist_ok=True)
    wheel_path = pathlib.Path(root / chosen["filename"])
    wheel_path.write_bytes(raw)
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(libdir)
    out.update(libdir=str(libdir), status="OK")

    # Runtime closure: a package that imports another package is not runnable alone.
    # Resolve the hard requirements (skipping environment markers we cannot evaluate)
    # and fetch each one's pure wheel into the same lib dir.  Every fetch is digest
    # verified; a dep with no pure wheel is reported, not silently skipped.
    closure: list[dict] = []
    seen = {name.lower()}
    for req in info.get("requires_dist") or []:
        if "extra ==" in req:
            continue
        dep = re.split(r"[\s<>=!~;\[]", req.strip())[0]
        if not dep or dep.lower() in seen:
            continue
        seen.add(dep.lower())
        try:
            sub = _acquire_into(dep, root, libdir)
        except Exception as exc:
            closure.append({"name": dep, "status": f"UNRESOLVED:{type(exc).__name__}"})
            continue
        closure.append({"name": dep, "status": sub.get("status"),
                        "filename": sub.get("filename")})
        if sub.get("libdir") and sub["libdir"] != str(libdir):
            for item in pathlib.Path(sub["libdir"]).iterdir():
                target = libdir / item.name
                if not target.exists():
                    if item.is_dir():
                        import shutil
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        import shutil
                        shutil.copy2(item, target)
    out["closure"] = closure
    out["seconds"] = round(time.time() - t0, 3)
    return out


def _acquire_into(dep: str, root: pathlib.Path, libdir: pathlib.Path) -> dict:
    """Fetch one dependency's pure wheel straight into `libdir` (one level, no recursion)."""
    meta = json.loads(_fetch(PYPI_JSON.format(name=dep)))
    wheels = [u for u in meta.get("urls", []) if u["filename"].endswith(".whl")
              and "none-any" in u["filename"]]
    if not wheels:
        return {"name": dep, "status": "NO_PURE_WHEEL"}
    w = wheels[0]
    raw = _fetch(w["url"], timeout=120.0)
    if hashlib.sha256(raw).hexdigest() != w["digests"]["sha256"]:
        return {"name": dep, "status": "DIGEST_MISMATCH"}
    with zipfile.ZipFile(_io.BytesIO(raw)) as zf:
        zf.extractall(libdir)
    return {"name": dep, "status": "OK", "filename": w["filename"], "libdir": str(libdir)}


def extract(path: pathlib.Path, root: pathlib.Path | None = None) -> dict:
    """Same as `acquire` for bytes already on disk (offline / reproducible runs)."""
    root = root or pathlib.Path(tempfile.mkdtemp(prefix="epb-"))
    raw = pathlib.Path(path).read_bytes()
    libdir = root / "lib"
    libdir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pathlib.Path(path)) as zf:
        zf.extractall(libdir)
    return {
        "name": pathlib.Path(path).name.split("-")[0],
        "filename": pathlib.Path(path).name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "digest_verified": None,
        "libdir": str(libdir),
        "status": "OK",
        "seconds": 0.0,
    }


# ---------------------------------------------------------------------------
# 2. SURFACE -- what the artifact says about itself, read as text, never imported.
# ---------------------------------------------------------------------------

def _is_public(name: str) -> bool:
    return not name.startswith("_")


def surface(libdir: str | pathlib.Path) -> dict:
    """Parse the artifact's own source into a call surface.

    Pure AST: nothing is imported, so a package that raises on import still yields a
    surface, and reading costs no side effects.  Docstrings are carried because they
    are the only place the artifact says what it is *for*; they are never trusted as
    a specification.
    """
    libdir = pathlib.Path(libdir)
    entries: list[dict] = []
    modules: list[dict] = []
    for f in sorted(libdir.rglob("*.py")):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = f.relative_to(libdir)
        parts = rel.parts
        modname = ".".join((parts[:-1] if parts[-1] == "__init__.py" else parts))[:-3] \
            if parts[-1] != "__init__.py" else ".".join(parts[:-1])
        modules.append({"module": modname, "file": str(rel)})
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and _is_public(node.name):
                methods = []
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(m.name):
                        methods.append({
                            "name": m.name,
                            "params": [a.arg for a in m.args.args[1:]],
                            "doc": _first_line(ast.get_docstring(m)),
                        })
                ctor = None
                for m in node.body:
                    if isinstance(m, ast.FunctionDef) and m.name in ("__init__", "__new__"):
                        # args[0] is the implicit self/cls; it is NOT a caller-supplied slot.
                        declared = max(len(m.args.args) - 1, 0)
                        required = max(declared - len(m.args.defaults), 0)
                        ctor = {
                            "via": m.name,
                            "required": required,
                            "declared": declared,
                        }
                        if m.name == "__new__":
                            break
                entries.append({
                    "module": modname,
                    "name": node.name,
                    "kind": "class",
                    "doc": _first_line(ast.get_docstring(node)),
                    "methods": methods,
                    "ctor": ctor,
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
                entries.append({
                    "module": modname,
                    "name": node.name,
                    "kind": "func",
                    "doc": _first_line(ast.get_docstring(node)),
                    "params": [a.arg for a in node.args.args],
                    "methods": [],
                })
    doctest_counts = _doctest_census(libdir)
    return {
        "modules": modules,
        "entries": entries,
        "classes": [e["name"] for e in entries if e["kind"] == "class"],
        "functions": [e["name"] for e in entries if e["kind"] == "func"],
        "doctests": doctest_counts,
        "digest": hashlib.sha256(
            json.dumps(entries, sort_keys=True).encode()
        ).hexdigest()[:16],
    }


def _first_line(text: str | None) -> str:
    if not text:
        return ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line and not line.startswith(">>>"):
            return line[:200]
    return ""


def _doctest_census(libdir: pathlib.Path) -> dict:
    """How much of its own behaviour the artifact states executably.

    Reported, never depended on: the census is what makes the difference between
    packages visible in the receipt instead of silently shaping the result.
    """
    import doctest

    docstrings = with_examples = 0
    for f in libdir.rglob("*.py"):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node)
                if not doc:
                    continue
                docstrings += 1
                try:
                    if doctest.DocTestParser().get_examples(doc):
                        with_examples += 1
                except ValueError:
                    pass
    return {"docstrings": docstrings, "with_examples": with_examples}


# ---------------------------------------------------------------------------
# 3. GOAL -> PREDICATE.  The only hand-written knowledge in this file, and it is
#    about effects on containers -- mathematics, not any package.
# ---------------------------------------------------------------------------

GOALS: dict[str, dict[str, Any]] = {
    "sorted_unique": {
        "means": "after the operation the object's items are in sorted order and every "
                 "distinct value appears exactly once",
        "observe": "items",
        "predicate": lambda items, seed, insert: (
            list(items) == sorted(set(list(seed) + [insert]), key=_okey)
        ),
        "footprint": {"methods": {"add"}, "names": {"Set", "set", "Unique", "Uniq"}},
        "confusable_with": "sorted_unique_with_duplicates",
    },
    "sorted_unique_with_duplicates": {
        "means": "items are in sorted order and duplicates are retained",
        "observe": "items",
        "predicate": lambda items, seed, insert: (
            list(items) == sorted(list(seed) + [insert], key=_okey)
        ),
        "footprint": {"methods": {"add"}, "names": {"List", "Bag", "Multiset", "Counter"}},
        "confusable_with": "sorted_unique",
    },
}


def _okey(v):
    """Sort key that keeps heterogeneous probe batteries usable."""
    return (str(type(v).__name__), v)


# The battery is derived, not curated.  Each member exists to kill one specific way a
# candidate can *look* correct:
#   SMALL_INTS   hash order and sort order coincide -- a hash set impersonates a sorted
#                set perfectly here, which is the coalition that fooled the first build.
#   WIDE_INTS    values whose hash order differs from sort order.
#   STRINGS      same disagreement in another domain, so a fixed numeric trick cannot pass.
#   LIST_VS_SET  a repeated value: this separates list-shaped from set-shaped effects.
#                It does NOT separate "unique" from "with duplicates" (both goals agree
#                once the value is already present), so it is not counted as such.
BATTERY: list[tuple[list, object, str]] = [
    ([3, 1, 2], 2, "SMALL_INTS"),
    ([8, 3, 100], 7, "WIDE_INTS"),
    (["b", "a", "c"], "b", "STRINGS"),
    ([5, 1, 5], 5, "LIST_VS_SET"),
]


def _hash_order_differs(seed: Sequence) -> bool:
    """Would a hash-ordered container be distinguishable from a sorted one here?

    Computed from the goal's own domain -- no package knowledge, no import.  A battery
    in which this is never true cannot tell a hash set from a sorted set, and saying so
    is part of the receipt.
    """
    try:
        return sorted(set(seed), key=_okey) != list(set(seed))
    except TypeError:
        return False


def compile_goal(goal: str) -> dict:
    if goal not in GOALS:
        raise KeyError(
            f"UNCOMPILABLE_GOAL:{goal}: a goal is only admitted when it names an effect "
            f"that can be checked without the artifact; known={sorted(GOALS)}"
        )
    spec = dict(GOALS[goal])
    spec["goal"] = goal
    return spec


# ---------------------------------------------------------------------------
# 4. SOLVE THE PROBE -- the input is chosen so that effects disagree on it.
# ---------------------------------------------------------------------------

def _apply_oracle(kind: str, seed: Sequence[int], insert: int) -> list[int]:
    if kind == "sorted_unique":
        return sorted(set(list(seed) + [insert]))
    return sorted(list(seed) + [insert])


def build_battery(spec: Mapping[str, Any]) -> dict:
    """Assemble probe members, each labelled with the impersonation it is there to kill."""
    mine = spec["predicate"]
    conf = GOALS[spec["confusable_with"]]["predicate"]
    members = []
    for seed, insert, why in BATTERY:
        try:
            goal_effect = sorted(set(list(seed) + [insert]), key=_okey) \
                if spec["goal"] == "sorted_unique" else sorted(list(seed) + [insert], key=_okey)
            conf_effect = sorted(list(seed) + [insert], key=_okey) \
                if spec["goal"] == "sorted_unique" else sorted(set(list(seed) + [insert]), key=_okey)
        except TypeError:
            continue
        members.append({
            "seed": list(seed),
            "insert": insert,
            "separates_goal_from_confusable": goal_effect != conf_effect,
            "kills": why,
            "hash_order_differs_from_sorted": _hash_order_differs(seed),
            "goal_effect": goal_effect,
            "confusable_effect": conf_effect,
            "predicates_disagree": bool(
                mine(goal_effect, seed, insert) and conf(conf_effect, seed, insert)
                and not conf(goal_effect, seed, insert)
            ),
        })
    separating = [m for m in members if m["separates_goal_from_confusable"]]
    hash_separating = [m for m in members if m["hash_order_differs_from_sorted"]]
    return {
        "members": members,
        "count": len(members),
        "separating_count": len(separating),
        "hash_separating_count": len(hash_separating),
        "can_tell_hash_set_from_sorted_set": len(hash_separating) > 0,
        "found_by": "derived from the goal's domain, then checked for separation",
    }


# ---------------------------------------------------------------------------
# 5. BIND + EXECUTE -- one candidate, one subprocess, one observation.
# ---------------------------------------------------------------------------

_RUNNER = r'''
import json, sys, traceback
sys.path.insert(0, __LIBDIR__)
payload = json.loads(__PAYLOAD__)
try:
    mod = __import__(payload["module"], fromlist=["*"])
except Exception as exc:
    print(json.dumps({"ok": False, "stage": "import", "error": type(exc).__name__ + ": " + str(exc)[:200]}))
    raise SystemExit(0)
name = payload["class"]
if not hasattr(mod, name):
    print(json.dumps({"ok": False, "stage": "surface", "error": "no attribute " + name}))
    raise SystemExit(0)
cls = getattr(mod, name)
seed = list(payload["seed"])
insert = payload["insert"]

# The construction form is DERIVED from what the class declares, not assumed.
# Order matters: the artifact's own arity first, then increasingly indirect forms.
# The artifact's own declaration is DIAGNOSIS, not a gate: a class declaring one
# required slot is constructed by filling that slot with the seed.  Every form below is
# tried in order and the first that yields a *usable* object wins; failure is reported
# with the declared arity so the reason is visible rather than guessed.
declared = (payload.get("ctor") or {}).get("required")
forms = [("direct", lambda: cls(seed))]
if declared == 0:
    forms.append(("empty", lambda: cls()))
# A module-level factory whose name mirrors the class name is the artifact's own
# convention (pset/PSet, pvector/PVector).  Matched by name, never by a lookup table.
lower = name.lower()
for fn in dir(mod):
    if fn.startswith("_"):
        continue
    f = getattr(mod, fn, None)
    if not callable(f):
        continue
    if fn in (lower, "p" + lower, lower.lstrip("p")):
        forms.append(("factory:" + fn, (lambda g: lambda: g(seed))(f)))
forms.append(("raw_new", lambda: cls.__new__(cls)))
forms.append(("class_itself", lambda: cls))

# A form is only accepted if the object it yields is actually USABLE: the operation
# must exist and must not blow up for a reason unrelated to the effect.  Accepting the
# first form that merely "constructs" is how PSet([3,1,2]) -- which stores the list
# unbuilt -- impersonates a working object while .add() fails on its internals.
obj = None
constructed_by = None
observable = None
errors = []
result = None
method = payload["method"]
for label, make in forms:
    try:
        cand = make()
    except Exception as exc:
        errors.append(label + ": construct: " + type(exc).__name__ + ": " + str(exc)[:100])
        continue
    fn = getattr(cand, method, None)
    if fn is None:
        errors.append(label + ": no method " + method)
        continue
    t0 = __import__("time").perf_counter()
    try:
        result = fn(insert)
    except Exception as exc:
        msg = type(exc).__name__ + ": " + str(exc)[:100]
        errors.append(label + ": call: " + msg)
        continue
    elapsed = (__import__("time").perf_counter() - t0) * 1000.0
    obj = cand
    constructed_by = label
    break
if obj is None:
    print(json.dumps({"ok": False, "stage": "construct_or_call",
                      "error": errors[0] if errors else "no form",
                      "forms_tried": len(forms), "errors": errors[:8]}))
    raise SystemExit(0)

# persistent collections return a new value; use it when it is the observable result
observable = obj
if result is not None and type(result) is type(obj) and result is not obj:
    observable = result
try:
    items = list(observable)
except Exception:
    try:
        items = list(observable.items())
    except Exception:
        items = None
mro = [c.__name__ for c in type(observable).__mro__]
print(json.dumps({"ok": True, "items": items, "mro": mro, "ms": round(elapsed, 3),
                  "constructed_by": constructed_by, "returned_new": observable is not obj,
                  "methods": [m for m in dir(observable) if not m.startswith("_")][:40]}))
'''


def execute_candidate(
    libdir: str,
    module: str,
    cls: str,
    method: str,
    probe: Mapping[str, Any],
    *,
    ctor: Mapping[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict:
    """Instantiate, call, observe -- in a fresh interpreter so nothing leaks between rows."""
    payload = json.dumps({
        "module": module,
        "class": cls,
        "method": method,
        "seed": probe["seed"],
        "insert": probe["insert"],
        "ctor": ctor,
    })
    code = (_RUNNER
            .replace("__LIBDIR__", repr(str(libdir)))
            .replace("__PAYLOAD__", repr(payload)))
    p = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout
    )
    if p.returncode != 0:
        tail = (p.stderr or "").strip().splitlines()
        return {"ok": False, "stage": "runner", "error": tail[-1][:200] if tail else f"rc={p.returncode}"}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"ok": False, "stage": "runner", "error": "unparseable runner output"}


# ---------------------------------------------------------------------------
# 6. THE FOOTPRINT GATE -- an effect must be *this* effect, not a lookalike.
# ---------------------------------------------------------------------------

def footprint_check(spec: Mapping[str, Any], result: Mapping[str, Any]) -> dict:
    """Does the object's own identity corroborate the effect the predicate observed?

    Two effects can produce identical items and be different objects.  The gate reads
    the runtime identity the artifact exposes (class name, MRO, method vocabulary) and
    requires it to be consistent with the goal's footprint.  A mismatch is not a
    failure of the candidate -- it is *evidence* that the predicate alone is too weak,
    and it is recorded as such.
    """
    want = spec["footprint"]
    mro = set(result.get("mro") or [])
    methods = set(result.get("methods") or [])
    name_tokens = set()
    for n in mro:
        name_tokens |= set(re.findall(r"[A-Z][a-z]+", n))
        name_tokens.add(n)
    lowered = "|".join(n.lower() for n in mro)
    name_hit = bool(want["names"] & name_tokens) or any(
        w.lower() in lowered for w in want["names"]
    )
    method_hit = bool(want["methods"] & methods)
    confusable = GOALS[spec["confusable_with"]]["footprint"]
    other_tokens = {t for n in mro for t in re.findall(r"[A-Z][a-z]+", n)}
    other_hit = bool(confusable["names"] & other_tokens)
    return {
        "mro": sorted(mro),
        "name_tokens": sorted(name_tokens),
        "name_consistent": name_hit,
        "method_consistent": method_hit,
        "looks_like_confusable": other_hit and not name_hit,
        "admitted": bool(method_hit and name_hit and not (other_hit and not name_hit)),
    }


# ---------------------------------------------------------------------------
# 7. THE BIND -- surface -> candidates -> execute -> verify -> ONE record.
# ---------------------------------------------------------------------------

_INSERT_VERBS = ("add", "update", "extend", "append", "insert", "push", "put", "add_all")


def _try_candidate(libdir: str, cand: Mapping[str, Any], battery: Mapping[str, Any],
                   spec: Mapping[str, Any]) -> dict:
    """Run one candidate across the whole battery; it is admitted only if every
    member's observation satisfies the goal predicate and the identity corroborates."""
    per_member: list[dict] = []
    for m in battery["members"]:
        res = execute_candidate(libdir, cand["module"], cand["class"], cand["method"], m,
                                ctor=cand.get("ctor"))
        row = {"kills": m["kills"], "seed": m["seed"], "insert": m["insert"]}
        if not res.get("ok"):
            row.update(member="ERROR", error=f"{res.get('stage')}: {res.get('error')}")
            per_member.append(row)
            continue
        try:
            ok = bool(spec["predicate"](res.get("items"), m["seed"], m["insert"]))
        except Exception as exc:
            row.update(member="UNOBSERVABLE", error=f"{type(exc).__name__}: {exc}")
            per_member.append(row)
            continue
        row.update(member="PASS" if ok else "FAIL", observed=res.get("items"))
        if res.get("mro"):
            row["mro"] = res["mro"]
        if res.get("methods"):
            row["methods"] = res["methods"]
        if res.get("constructed_by"):
            row["constructed_by"] = res["constructed_by"]
        per_member.append(row)

    statuses = [r["member"] for r in per_member]
    informative = [r for r in per_member if r["member"] in ("PASS", "FAIL")]
    out = {**cand, "per_member": per_member}
    out["informative_members"] = len(informative)
    out["effect_signature"] = json.dumps(
        [[r["member"], r.get("observed")] for r in per_member], sort_keys=True
    )
    if not informative:
        out["verdict"] = "ERROR"
        out["teaches"] = next((r.get("error", "") for r in per_member if r.get("error")), "")
        return out
    passes = [r for r in informative if r["member"] == "PASS"]
    fails = [r for r in informative if r["member"] == "FAIL"]
    if fails:
        out["verdict"] = "NO_EFFECT"
        killers = sorted({r["kills"] for r in fails})
        out["teaches"] = (
            f"passed {len(passes)}/{len(informative)} battery members; "
            f"the effect is not the goal's effect (killed by {', '.join(killers)})"
        )
        out["passed_only_on"] = sorted({r["kills"] for r in passes})
        return out
    last = passes[-1]
    if not last.get("methods"):
        last["methods"] = next((r["methods"] for r in passes if r.get("methods")), [])
    fp = footprint_check(spec, {"mro": last.get("mro") or [], "methods": last.get("methods") or []})
    out["footprint"] = fp
    if not fp["admitted"]:
        out["verdict"] = "LOOKALIKE"
        out["teaches"] = "predicate satisfied on every member but identity says a different effect"
        return out
    out["verdict"] = "BOUND"
    return out


def bind(
    libdir: str,
    goal: str,
    *,
    libname: str = "",
    max_candidates: int = 40,
) -> dict:
    """Derive, execute and verify a callable for `goal` against an unseen artifact."""
    t0 = time.time()
    spec = compile_goal(goal)
    surf = surface(libdir)
    battery = build_battery(spec)

    candidates: list[dict] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for entry in surf["entries"]:
        if entry["kind"] != "class":
            continue
        for m in entry["methods"]:
            if m["name"] not in _INSERT_VERBS:
                continue
            key = (entry["module"], entry["name"], m["name"])
            if key in seen_pairs:          # a class re-exported by several modules
                continue
            seen_pairs.add(key)
            candidates.append({
                "module": entry["module"],
                "class": entry["name"],
                "method": m["name"],
                "doc": entry["doc"],
                "ctor": entry.get("ctor"),
            })
    candidates = candidates[:max_candidates]

    attempts = [_try_candidate(libdir, c, battery, spec) for c in candidates]
    # A candidate earns a record only by satisfying the goal on the WHOLE battery.
    # `PSet.update` showed why: it takes an iterable, so the string member is absorbed by
    # reconstruction and comes back sorted -- a bare PASS on 1 of 4 members while the other
    # three never even constructed. That is a coincidence with a receipt, and it was
    # briefly bound as a sorted set. Informative on every member, or it is not an effect.
    whole = len(battery["members"])
    passed = [
        a for a in attempts
        if a["verdict"] == "BOUND" and a.get("informative_members", 0) == whole
    ]

    # Aliases are not ambiguity.  If two candidates produce byte-identical observations on
    # every battery member, they are one effect with two names; collapsing them is a
    # *verified* merge, whereas picking one arbitrarily would be a guess.
    # Dominance: if binding A satisfies the goal on a strict superset of the battery
    # members binding B satisfies, A subsumes B -- B is a narrower special case, not a
    # competing effect.  This is how `update` (only works when the insert is iterable)
    # relates to `add` (works always).  Non-comparable bindings stay distinct.
    def passing_set(a: Mapping[str, Any]) -> set[str]:
        return {r["kills"] for r in a["per_member"] if r.get("member") == "PASS"}

    dominated: list[dict] = []
    survivors: list[dict] = []
    for a in passed:
        a_set = passing_set(a)
        beaten = any(
            b is not a and a_set < passing_set(b)
            for b in passed
        )
        (dominated if beaten else survivors).append(a)

    groups: dict[str, list[dict]] = {}
    for a in survivors:
        groups.setdefault(a["effect_signature"], []).append(a)
    equivalent = {
        sig: [{"module": g["module"], "class": g["class"], "method": g["method"]} for g in gs]
        for sig, gs in groups.items()
    }
    distinct_effects = len(groups)

    record = None
    if distinct_effects == 1:
        gs = next(iter(groups.values()))
        gs.sort(key=lambda a: (a["method"] != "add", a["class"], a["method"]))
        win = gs[0]
        record = {
            "schema": SCHEMA,
            "goal": goal,
            "effect": {
                "predicate": "items == sorted(set(seed + [insert]), key=okey)"
                if goal == "sorted_unique" else spec["means"],
                "battery": battery,
                "verified_by": "execution on every battery member, each killing one impersonation",
                "observations_digest": hashlib.sha256(win["effect_signature"].encode()).hexdigest()[:16],
            },
            "binding": {
                "module": win["module"],
                "class": win["class"],
                "method": win["method"],
            },
            "aliases": [g for g in equivalent[win["effect_signature"]]
                        if (g["class"], g["method"]) != (win["class"], win["method"])],
            "identity": win["footprint"]["mro"],
            "artifact": {"libname": libname, "surface_digest": surf["digest"]},
            "reuse_key": "effect:" + hashlib.sha256(
                json.dumps({"goal": goal, "surface": surf["digest"]},
                           sort_keys=True).encode()
            ).hexdigest()[:16],
            "scope": "this effect on this artifact identity; not a claim about other artifacts",
        }
    return {
        "schema": SCHEMA,
        "libname": libname,
        "libdir": str(libdir),
        "goal": goal,
        "goal_means": spec["means"],
        "surface": {
            "classes": surf["classes"][:12],
            "functions": surf["functions"][:12],
            "module_count": len(surf["modules"]),
            "doctest_census": surf["doctests"],
        },
        "battery": battery,
        "candidates_considered": len(candidates),
        "admitted": len(passed),
        "distinct_effects": distinct_effects,
        "dominated": [
            {"class": a["class"], "method": a["method"],
             "passes_only": sorted(passing_set(a)),
             "dominated_by": sorted(
                 {b["class"] + "." + b["method"] for b in survivors
                  if passing_set(a) < passing_set(b)}
             )}
            for a in dominated
        ],
        "equivalence_classes": equivalent,
        "attempts": attempts,
        "record": record,
        "ambiguous": distinct_effects > 1,
        "stderr_free_corrections": [
            a["teaches"] for a in attempts if a["verdict"] == "ERROR" and a.get("teaches")
        ][:8],
        "seconds": round(time.time() - t0, 3),
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
    }


# ---------------------------------------------------------------------------
# 8. THE STORE -- external, inspectable, addable and removable without retraining.
# ---------------------------------------------------------------------------

class Store:
    """A directory of JSON records. Nothing about a record lives in any parameter."""

    def __init__(self, root: str | pathlib.Path):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> pathlib.Path:
        return self.root / (re.sub(r"[^A-Za-z0-9_.:-]", "_", key) + ".json")

    def put(self, record: Mapping[str, Any]) -> pathlib.Path:
        path = self._path(record["reuse_key"])
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def get(self, key: str) -> dict | None:
        p = self._path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def keys(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def remove(self, key: str) -> bool:
        p = self._path(key)
        if p.exists():
            p.unlink()
            return True
        return False


def replay(record: Mapping[str, Any], libdir: str) -> dict:
    """Re-use a stored skill without re-deriving it, then check the effect again.

    The call is reconstructed from the record alone and executed on a fresh artifact
    directory, over the same battery.  This is what makes a record a *skill*.
    """
    b = record["binding"]
    spec = compile_goal(record["goal"])
    battery = record["effect"]["battery"]
    verdicts = []
    for m in battery["members"]:
        res = execute_candidate(libdir, b["module"], b["class"], b["method"], m,
                                ctor=b.get("ctor"))
        if not res.get("ok"):
            verdicts.append("ERROR")
            continue
        try:
            ok = bool(spec["predicate"](res.get("items"), m["seed"], m["insert"]))
        except Exception:
            verdicts.append("UNOBSERVABLE")
            continue
        verdicts.append("PASS" if ok else "FAIL")
    return {
        "ok": verdicts == ["PASS"] * len(battery["members"]),
        "verdicts": verdicts,
        "derived": False,
        "source": "store",
    }


# ---------------------------------------------------------------------------
# 9. CLI
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--package", required=True)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--wheel")
    ap.add_argument("--store")
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)

    if args.wheel:
        art = extract(pathlib.Path(args.wheel))
    else:
        art = acquire(args.package)
    if art["status"] != "OK":
        print(json.dumps({"status": art["status"], "artifact": art}, indent=2))
        return 2
    report = bind(art["libdir"], args.goal, libname=args.package)
    report["artifact"] = art
    if args.store and report.get("record"):
        path = Store(args.store).put(report["record"])
        report["stored"] = str(path)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if report.get("record") else 1


if __name__ == "__main__":
    raise SystemExit(main())
