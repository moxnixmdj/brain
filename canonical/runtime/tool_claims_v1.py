"""Is a claim about a TOOL a fact about THIS machine? Answered by looking, not by the registry.

THE DEFECT THIS EXISTS FOR. 52 rows say `VERIFIED_BOUND_CAPABILITY` and declare no adapter file. They are
not broken adapters and they are not fabrications either: each one names an EXTERNAL tool -- a system
binary (`git`), a PyPI distribution (`tree_sitter`, `msgpack`), an npm package, an apt package -- and a
template that says how to call it. Measured 2026-11-23:

    declared source.type   rows   meaning
    --------------------   ----   --------------------------------------------------
    python_stdlib / runtime 19    `re`, `ast`, `tokenize` -- present in every Python
    apt / npm / pypi        33    a tool this machine may or may not have

So the honest question is not "can it run" but "is the tool it names actually here?", and that question
has a mechanical answer. `reachability_v2` could only say NO_ADAPTER_DECLARED for all 52, which is true
and useless: it lumps a stdlib function, an installed binary, and a package nobody ever installed into one
finding. This module separates them, because the next action is different in each case.

    PRESENT   the named tool is on this machine and its invocation is recorded
    ABSENT    the named tool is not here -- a CLAIM ABOUT A TOOL DRESSED AS A CAPABILITY OF THIS MACHINE

WHY ABSENT IS THE INTERESTING ANSWER, AND WHY IT IS NOT A BUG TO PATCH. A registry row that asserts
`structured.binary.encode.msgpack` while `msgpack` is not installed is exactly the knowledge-house defect
the mission forbids, moved one layer out: the machine believes it can do a thing because it once wrote
down that the thing exists. The repair is not to install 33 packages -- that is the opposite of
"the best part is no part", and it makes the machine's self-description depend on a network. The repair is
that the claim must be DERIVED FROM THE MACHINE, which is what `acquirable()` below reports: a package
manager is present, so the tool can be obtained, verified against the supplier's own digest, and promoted
to a claim only after it exists. `auto_pypi_library_acquisition` already does that for Python packages,
against official PyPI metadata. Nothing here duplicates it; this module only reports whether the door is
there and which door it is.

WHAT THIS FILE REFUSES TO DO:
  * It never runs an external tool to check it. `which` and `find_spec` are lookups; a lookup is not a
    smoke test, and pretending otherwise is how `status` fields became trusted.
  * It never reports a missing tool as "unreachable code". The code is fine; the tool is absent.
  * It never guesses a module's location. `python_stdlib` rows get `importlib.util.find_spec`, which is
    the interpreter's own answer.
"""

from __future__ import annotations

import importlib.util
import json
import re
import pathlib
import shutil
import sys
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_TOOL_CLAIMS_V1"

# Rows whose named tool lives in Python itself. Present on any interpreter that can import this module.
_STDLIB_TYPES = frozenset({"python_stdlib", "runtime", "brain_native_deterministic_composition",
                           "brain_owned_deterministic"})

# The package managers on this machine, in the order a claim should be resolved. A manager is only
# reported if it is executable: naming one that is not here would repeat the defect this file measures.
_MANAGERS = (("pypi", ("pip", "pip3")), ("npm", ("npm",)), ("apt", ("apt-get", "apt")))


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _load_registry() -> Mapping[str, Mapping[str, Any]]:
    from canonical.runtime import live_integrated_brain_v1 as brain
    return brain.load_verified_registry()


def _program_in_template(entry: Mapping[str, Any]) -> str | None:
    """The executable a row tells the machine to run, if it names one."""
    args = ((entry.get("action_template") or {}).get("args") or {})
    argv = args.get("argv")
    if isinstance(argv, (list, tuple)) and argv:
        head = str(argv[0])
        # A template may interpolate (`${input.program}`); that is not a name.
        return None if "${" in head else head
    return None


# A `module` FIELD THAT HOLDS A SENTENCE IS NOT A MODULE NAME.
#
# Measured 2026-11-23: 13 rows store PROSE in `module` -- "python stdlib ast/tokenize", "stdlib",
# "python stdlib ast/pytest + git", "finite_grid_program_inducer". A field that cannot be looked up is a
# description of a capability, and a description cannot be checked. These are the names a sentence like
# that actually contains; extracting them is reading the row, not guessing about the world.
_PROSE_NOISE = frozenset({"python", "stdlib", "std", "lib", "and", "or", "+", "/", "runtime",
                          "builtins", "builtin", "core", "the", "with", "using", "via", "native"})


def _names_in(prose: str) -> list[str]:
    """Every token in a `module` field that looks like something importable or runnable."""
    tokens = [t for t in re.split(r"[^A-Za-z0-9_.]+", str(prose or "")) if t]
    return [t for t in tokens if t.lower() not in _PROSE_NOISE and not t.isdigit()]


def _distribution_from_id(cid: str) -> str:
    """`auto.npm.msgpack-msgpack` -> `msgpack-msgpack`; `auto.pypi.bson-modern` -> `bson-modern`.

    The id is the only place some of these rows record what they claim to be about, so it is read rather
    than invented. This is not a guess about the world: it is the row's own name.
    """
    parts = str(cid).split(".")
    return "-".join(parts[2:]) if len(parts) > 2 else ""


def _project_module(name: str, root: pathlib.Path) -> str | None:
    """Is this name a MODULE OF THIS PROJECT? Then its claim is about our own code, not a tool.

    Measured 2026-11-23: `software.synthesis.grid_induction.v1` declares
    `module: "finite_grid_program_inducer"` and `canonical/runtime/finite_grid_program_inducer_v1.py`
    exists. The row was counted as an absent external tool for an entire audit. A name that resolves to a
    file in this tree is the project's own code wearing a tool's clothes, and it must be looked for in the
    tree BEFORE any package manager is consulted.
    """
    candidates = [name, name + "_v1", name + "_v1".replace("_v1", "")]
    for stem in candidates:
        for path in (root / "canonical" / "runtime").glob("%s.py" % stem):
            return str(path.relative_to(root))
        for path in (root / "canonical" / "runtime" / "bound_capabilities").glob("%s*.py" % stem):
            return str(path.relative_to(root))
    return None


# A WHEEL THAT WAS BUILT FOR A DIFFERENT PYTHON CANNOT BE INSTALLED HERE, AND ITS DIGEST CANNOT FIX THAT.
#
# Measured 2026-11-23: `auto.pypi.msgpack` pins
#   msgpack-1.2.2-cp312-cp312-manylinux2014_x86_64...whl
# with its sha256. This machine runs cp311. The row is a TRUE fact about a 3.12 machine, recorded as a
# capability of this one -- the knowledge-house defect in its purest form: a specific, hash-verified,
# entirely unusable memory. `pip` will refuse the file, so no amount of diligence turns it into a run.
_WHEEL_TAG = re.compile(r"-(cp\d{2,3}|py\d(?:\d|\.py\d?))-")


def _wheel_fits_this_interpreter(wheel_filename: str) -> tuple[bool, str]:
    """Does a wheel's platform/ABI tag match the interpreter running this check?"""
    name = str(wheel_filename or "")
    if not name.endswith(".whl"):
        return True, "not a wheel; nothing to match"
    match = _WHEEL_TAG.search(name)
    if not match:
        return True, "no interpreter tag found"
    tag = match.group(1)
    here = "cp%d%d" % sys.version_info[:2]
    if tag.startswith("py3") or tag.startswith("py2.py3"):
        return True, "pure-python wheel (%s) runs on %s" % (tag, here)
    if tag.startswith("cp"):
        return (tag == here), "wheel is %s, this interpreter is %s" % (tag, here)
    return True, "tag %s not matched here" % tag


def _manager_for(kind: str) -> str | None:
    for name, candidates in _MANAGERS:
        if name != kind:
            continue
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def claim(cid: str, entry: Mapping[str, Any]) -> dict[str, Any]:
    """One row, one finding: what it names, whether that is here, and what would make it real."""
    source = entry.get("source") or {}
    kind = str(source.get("type") or "")
    module = str(source.get("module") or "").strip()
    program = _program_in_template(entry)
    out: dict[str, Any] = {"capability_id": cid, "declared_type": kind,
                           "declared_module": module or None, "declared_program": program}

    if kind in _STDLIB_TYPES:
        # The interpreter's own answer, for every name the field actually contains.
        names = _names_in(module) or ([program] if program else [])
        resolved: dict[str, bool] = {}
        for name in names:
            # A NAME IS PRESENT IF IT CAN BE IMPORTED *OR* RUN *OR* FOUND IN THIS TREE. `git` in the
            # field `"python stdlib ast/pytest + git"` is a binary, and an import check alone called it
            # missing on a machine that has git.
            local = _project_module(name, _root())
            if local:
                resolved[name] = True
                out.setdefault("resolved_in_this_tree", {})[name] = local
                continue
            try:
                ok = importlib.util.find_spec(name.split(".")[0]) is not None
            except (ImportError, ValueError, ModuleNotFoundError):
                ok = False
            resolved[name] = ok or bool(shutil.which(name))
        out.update({"names_read_from_the_field": names,
                    "evidence": {n: ("find_spec ok" if ok else "find_spec found nothing")
                                 for n, ok in resolved.items()}})
        if not names:
            out.update({"state": "NO_NAME_IN_THE_ROW",
                        "why": "THE_ROW_NAMES_NO_MODULE_AT_ALL_SO_NOTHING_CAN_BE_LOOKED_UP"})
        elif all(resolved.values()):
            out.update({"state": "PRESENT", "why": None})
        elif any(resolved.values()):
            out.update({"state": "PARTLY_PRESENT",
                        "why": "SOME_NAMES_IN_THE_FIELD_ARE_NOT_IMPORTABLE_HERE",
                        "missing": sorted(n for n, ok in resolved.items() if not ok)})
        else:
            out.update({"state": "STDLIB_NAME_UNRESOLVED",
                        "why": "NONE_OF_THE_NAMES_IT_DECLARES_IS_IMPORTABLE_HERE"})
        return out

    if kind == "system_tool" or program:
        name = program or module
        found = shutil.which(name) if name else None
        out.update({"state": "PRESENT" if found else "ABSENT",
                    "evidence": ("which %r -> %s" % (name, found)) if found else ("which %r -> nothing" % name)})
        if not found:
            out["why"] = "THE_TOOL_IT_NAMES_IS_NOT_INSTALLED_HERE"
            # ONE SHAPE. A door is `{kind: manager_path}`; returning a bare path for system tools and a
            # dict for pypi made every consumer special-case the producer's mood.
            _apt = _manager_for("apt")
            out["acquirable"] = {"apt": _apt} if _apt else None
        return out

    if kind == "pypi":
        name = module or _distribution_from_id(cid)
        try:
            here = bool(name) and importlib.util.find_spec(name.split(".")[0].replace("-", "_")) is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            here = False
        wheel = str(source.get("wheel_filename") or "")
        fits, wheel_detail = _wheel_fits_this_interpreter(wheel) if wheel else (True, "")
        out["declared_wheel"] = wheel or None
        if wheel:
            out["wheel_fits_this_interpreter"] = fits
            out["wheel_detail"] = wheel_detail
        out.update({"state": "PRESENT" if here else ("WHEEL_FOR_ANOTHER_PYTHON" if not fits else "ABSENT"),
                    "evidence": "importlib.util.find_spec(%r)" % name})
        if not here and not fits:
            out["why"] = "THE_WHEEL_IT_PINS_WAS_BUILT_FOR_A_DIFFERENT_INTERPRETER"
        elif not here:
            out["why"] = "THE_DISTRIBUTION_IT_NAMES_IS_NOT_INSTALLED_HERE"
            out["acquirable"] = ({kind: _manager_for("pypi"),
                                  "verifies": "auto_pypi_library_acquisition verifies the wheel against "
                                              "official PyPI metadata before it is used"}
                                 if _manager_for("pypi") else None)
        return out

    if kind in ("npm", "apt"):
        name = module or _distribution_from_id(cid)
        manager = _manager_for(kind)
        out.update({"state": "ABSENT" if name or manager else "NOT_A_TOOL",
                    "evidence": "no local registry to consult for %s; manager %s" % (kind, manager or "absent")})
        out["why"] = "THE_PACKAGE_IT_NAMES_IS_NOT_INSTALLED_HERE"
        out["acquirable"] = {kind: manager} if manager else None
        return out

    out.update({"state": "NOT_A_TOOL", "why": "UNRECOGNISED_DECLARED_TYPE:%s" % kind})
    return out


def tool_claims(reg: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Every `VERIFIED_BOUND_CAPABILITY` row with no adapter, resolved against this machine."""
    reg = reg if reg is not None else _load_registry()
    findings: dict[str, Any] = {}
    for cid, entry in sorted(reg.items()):
        if not isinstance(entry, Mapping) or str(entry.get("status")) != "VERIFIED_BOUND_CAPABILITY":
            continue
        source = entry.get("source") or {}
        if source.get("adapter_path") or source.get("path"):
            continue
        findings[cid] = claim(cid, entry)
    counts: dict[str, int] = {}
    for found in findings.values():
        counts[found["state"]] = counts.get(found["state"], 0) + 1
    return {"schema": SCHEMA, "claims": len(findings), "counts": counts, "rows": findings,
            "note": ("ABSENT is a claim about a tool, not a property of the machine. It becomes PRESENT "
                     "only after the tool exists here and its digest was checked against the supplier's.")}


def main() -> None:
    report = tool_claims()
    print(json.dumps({"claims": report["claims"], "counts": report["counts"]}, indent=1))
    for cid, found in sorted(report["rows"].items()):
        print("  %-46s %-22s %s" % (cid[:46], found["state"], found.get("declared_module") or
                                    found.get("declared_program") or ""))


if __name__ == "__main__":
    main()
