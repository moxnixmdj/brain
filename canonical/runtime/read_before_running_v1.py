"""Tell a program what will kill it, before running it -- and let one experience change the next answer.

THE HYPOTHESIS THIS TESTS, in the owner's words: "the agent only needs to do something once ... and it
learns it permanently." Measured 2026-11-23, honestly, before this file existed:

    the same misspelling, repaired in three successive fresh worlds
    trial 1  probes=1
    trial 2  probes=1
    trial 3  probes=1

**The second occurrence was never cheaper than the first.** Nothing consulted anything. So the hypothesis was
not merely unproven in this repo -- it was FALSE of the loop that had just been built, and saying otherwise
would have been the kind of report this project exists to avoid.

WHERE THE COST ACTUALLY IS. A repair of one fault took FOUR executions of the program (one to fail, one inside
the environment repairer, one to observe again, one to confirm). `repair_v1.diagnose` is a pure regex parse and
costs nothing; the expense is DISCOVERING the fault by running the program and reading its traceback.

WHAT MAKES THAT REMOVABLE IS A PROPERTY OF THESE TWO FAULTS. A missing module and an undefined name are both
visible in the SOURCE before the program runs. CPython learns them by executing; they are not facts that
require execution. `look_before_v1` already argued the general principle -- *"a command is not opaque. It names
files that are sitting right there."* This applies it to a Python program: read it, and both faults are known
without paying for a run.

BUT PREDICTION IS NOT KNOWLEDGE, AND THE DIFFERENCE DECIDES THE WHOLE DESIGN. A static check that says
"`totl` is undefined" has told you a fact about THIS program. It has not told you anything that helps the next
program. That is why the two fault classes must be treated differently, and the difference is measured rather
than assumed -- `stated_precondition_v1.learn` on each:

    MODULE_NOT_FOUND:pyjokes      learned=True   predicate={'property':'present','test':'is_present'}
    NAME_NOT_DEFINED:totl         learned=False  why=CODE_NAMES_NO_DECIDABLE_PROPERTY

A missing module is a rule about the WORLD: "this interpreter does not have X". It transfers to every program
that will ever import X -- and it is decided by asking an inspectable external store (what is installed), never
by a trained parameter. §2's test holds literally: add the package and the rule stops firing; remove it and the
rule fires again; no weight changes.

An undefined name is NOT a rule. It is a fact about one program's symbol table. `totl` in one file says nothing
about `totl` in another. Storing it would be recording an action dressed as knowledge, which is exactly what
the owner warned against -- "saving his exact experience must be in a very sufficient way, not just saving the
exact experience in a dumb way."

So the module answers two questions and keeps them apart:

    predict(source)   what will fail, from the source alone          -- no memory, no execution
    absorb(failure)   what the world just taught, in a form that      -- one experience, written to the store
                      is a RULE and not a transcript

WHAT IS DELIBERATELY NOT HERE. No scheduler, no planner, no model, no table of programs. The prediction is an
`ast` walk; the memory is a JSON file a person can read and edit. Two mechanisms, both refusing precisely.
"""
from __future__ import annotations

import ast
import builtins
import importlib.util
import pathlib
import subprocess
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from canonical.runtime import stated_precondition_v1 as STATED

SCHEMA = "PROJECT_BRAIN_READ_BEFORE_RUNNING_V1"

#: Every name bound by a `from X import *` is unknowable statically. When a program uses one, an undefined
#: name cannot be distinguished from a star-imported one, and this module REFUSES rather than guessing.
#: Measured 2026-11-23: `from os.path import *` + `join(...)` was reported as an undefined name by a naive
#: walk -- a false accusation against a program that runs correctly. A predictor that accuses correct programs
#: is worse than none, because it would "repair" them.
_STAR_IMPORT = "STAR_IMPORT_MAKES_NAMES_UNKNOWABLE"


def _imported_modules(tree: ast.AST) -> list[dict[str, Any]]:
    """Top-level module names the program imports, with the line the import is on."""
    found: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append({"module": alias.name.split(".")[0], "line": node.lineno,
                              "statement": "import %s" % alias.name})
        elif isinstance(node, ast.ImportFrom):
            if node.level:      # a relative import needs the package context, which a bare file does not have
                continue
            if node.module:
                found.append({"module": node.module.split(".")[0], "line": node.lineno,
                              "statement": "from %s import ..." % node.module})
        elif isinstance(node, ast.Call):
            # `importlib.import_module("x")` and `__import__("x")` name a module without an import statement.
            # Reading them is a string literal away, and missing them would mean the prediction is silently
            # incomplete -- the failure mode that lets a broken program through.
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute) and func.attr == "import_module":
                name = func.attr
            elif isinstance(func, ast.Name) and func.id in ("__import__", "import_module"):
                name = func.id
            if name and node.args:
                literal = node.args[0]
                if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                    found.append({"module": literal.value.split(".")[0], "line": node.lineno,
                                  "statement": "%s(%r)" % (name, literal.value)})
    return found


def _bound_names(tree: ast.AST) -> set[str]:
    """Every name the program binds anywhere, plus every builtin: the universe a loaded name may come from.

    A function-scoped binding counts, because the alternative -- scoping correctly -- would report names inside
    functions that a simpler walk considers undefined. Over-counting bindings makes this check QUIETER, which is
    the right direction: a missed prediction costs one execution, a false accusation costs trust.
    """
    bound: set[str] = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    bound.add(alias.asname or alias.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
        elif isinstance(node, ast.comprehension):
            for part in ast.walk(node.target):
                if isinstance(part, ast.Name):
                    bound.add(part.id)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for part in ast.walk(node.optional_vars):
                if isinstance(part, ast.Name):
                    bound.add(part.id)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, ast.MatchAs) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            bound.add(node.rest)
    return bound


def _has_star_import(tree: ast.AST) -> bool:
    return any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
               for node in ast.walk(tree))


def predict_names(source: str) -> dict[str, Any]:
    """Names loaded but never bound anywhere the program can see.

    A MISS IS CHEAPER THAN A FALSE ACCUSATION, deliberately. Where the walk cannot decide -- a star import, a
    name injected by `exec`, a `__getattr__` on a module object -- it says so instead of listing a name as
    undefined.
    """
    try:
        tree = ast.parse(str(source))
    except SyntaxError as broken:
        # A program that does not parse has a fault the traceback states exactly, and this is not it.
        return {"schema": SCHEMA, "kind": "names", "predictable": False,
                "why": "SYNTAX_ERROR", "detail": str(broken)[:200]}
    if _has_star_import(tree):
        return {"schema": SCHEMA, "kind": "names", "predictable": False, "why": _STAR_IMPORT}
    bound = _bound_names(tree)
    loaded: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in bound:
            loaded.setdefault(node.id, node.lineno)
    return {"schema": SCHEMA, "kind": "names", "predictable": True,
            "undefined": sorted(loaded), "lines": loaded,
            "will_fail": bool(loaded)}


def _installed(name: str, *, interpreter: str | None = None) -> bool:
    """Is this module importable by the interpreter that will RUN the program? An inspectable fact, not a
    parameter.

    §2's test in its most literal form: `pip install X` makes the rule stop firing, `pip uninstall X` makes it
    fire again, and nothing in any weight changed. This is the knowledge store the mission allows, and it is
    the interpreter's own answer rather than this project's opinion of the world.

    `interpreter` is not a nicety. Measured 2026-11-23: a prediction made in the harness's process said a
    module was present, while the program was going to run under an interpreter where it was absent. Asking the
    wrong interpreter is the same class of error as §A110's guard watching the wrong tree -- the answer is
    confident and about the wrong thing.
    """
    if interpreter:
        try:
            probe = subprocess.run([interpreter, "-c", "import " + name],
                                   capture_output=True, timeout=120)
            return probe.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def local_modules(world: str | pathlib.Path | None) -> set[str]:
    """Module names a `.py` file in this directory would provide.

    WITHOUT THIS THE PREDICTION ACCUSES CORRECT PROGRAMS. Measured 2026-11-23: a program in a directory with
    `alpha_mod.py` beside it was reported as importing a MISSING module, because `find_spec` only knows what is
    installed. The program imports fine. A predictor that says "this will fail" about a program that works is
    worse than no predictor, because the "repair" it triggers changes something that was never broken.
    """
    if world is None:
        return set()
    base = pathlib.Path(world)
    if not base.is_dir():
        return set()
    found: set[str] = set()
    for entry in base.iterdir():
        if entry.is_file() and entry.suffix == ".py" and entry.stem != "__init__":
            found.add(entry.stem)
        elif entry.is_dir() and (entry / "__init__.py").is_file():
            found.add(entry.name)
    return found


def predict_imports(source: str, *, installed: Iterable[str] | None = None,
                    world: str | pathlib.Path | None = None,
                    interpreter: str | None = None,
                 probe: bool = True) -> dict[str, Any]:
    """Imports the interpreter would refuse.

    `installed` lets a caller supply the answer instead of asking this process -- the same discipline
    `is_satisfied` uses with `universe`, and for the same reason: the world is asked, not cached.

    `world` is the directory the program will RUN in, and it changes the answer. A module satisfied by a file
    sitting beside the program is not missing; it is LOCAL, and what it does when imported cannot be known from
    the importing file at all. That third bucket is the honest one and it is where a learned rule earns its
    place -- a static reader can see that `beta_mod.py` exists, and cannot see that it raises on import.
    """
    try:
        tree = ast.parse(str(source))
    except SyntaxError as broken:
        return {"schema": SCHEMA, "kind": "imports", "predictable": False,
                "why": "SYNTAX_ERROR", "detail": str(broken)[:200]}
    imports = _imported_modules(tree)
    local = local_modules(world)
    if installed is not None:
        known = {str(item).lower() for item in installed}
        missing = [item for item in imports if item["module"].lower() not in known
                   and item["module"] not in local]
    else:
        missing = [item for item in imports
                   if item["module"] not in local
                   and not _installed(item["module"], interpreter=interpreter)]
    # a module provided by a neighbouring file: present, and unknowable
    nearby = [item for item in imports if item["module"] in local]
    return {"schema": SCHEMA, "kind": "imports", "predictable": True,
            "imports": imports, "missing": missing, "local": nearby,
            "will_fail": bool(missing),
            # TRUE when at least one import cannot be judged from this file alone
            "unknowable": bool(nearby)}


def predict(source: str, *, installed: Iterable[str] | None = None,
            world: str | pathlib.Path | None = None,
            interpreter: str | None = None) -> dict[str, Any]:
    """Everything that can be known about how this program will fail, without running it.

    `interpreter` is the python that will run it, when that is not the one asking. Omitting it means the
    prediction is about THIS process, which is only the same question when they are the same interpreter.
    """
    imports = predict_imports(source, installed=installed, world=world, interpreter=interpreter)
    names = predict_names(source)
    faults = []
    for item in imports.get("missing") or []:
        faults.append({"class": "missing_python_module", "module": item["module"],
                       "line": item["line"], "detected_by": "import_statement"})
    for name in names.get("undefined") or []:
        faults.append({"class": "undefined_name", "name": name,
                       "line": (names.get("lines") or {}).get(name), "detected_by": "ast"})
    return {"schema": SCHEMA, "faults": faults, "will_fail": bool(faults),
            "imports_predictable": imports.get("predictable"),
            "names_predictable": names.get("predictable"),
            "unknowable_imports": [item["module"] for item in imports.get("local") or []],
            "refusals": [r for r in (imports.get("why"), names.get("why")) if r]}


def _close_candidates(name: str, bound: Iterable[str], *, limit: int = 3) -> list[str]:
    """Names in the program close to the undefined one -- CPython's own suggestion, derived not looked up.

    CPython prints `Did you mean: 'total'?` using `difflib.get_close_matches`. This does the same arithmetic on
    the program's own symbol table: no list of correct names, no model, nothing but strings that are already in
    the file.
    """
    import difflib

    pool = [str(item) for item in bound if not str(item).startswith("__")]
    return difflib.get_close_matches(str(name), pool, n=limit, cutoff=0.7)


def absorb(failure: str, *, at: str = "", store: pathlib.Path | None = None) -> dict[str, Any]:
    """What ONE failure taught, kept ONLY when it is a rule rather than a fact about one program.

    The refusal is the important half. An undefined name is absorbed as `learned=False` and says why: it is a
    fact about this file's symbol table, and the next file will have a different one. Recording it would inflate
    a transcript and call it knowledge.
    """
    return STATED.learn(failure, at=at, store=store)


def probe_importable(module: str, *, world: str | pathlib.Path,
                     interpreter: str | None = None, timeout: int = 120) -> dict[str, Any]:
    """Import `module` ALONE, in the program's directory, with the program's interpreter, and report what happened.

    WHY THIS IS THE RIGHT QUESTION AND NOT A WORKAROUND. A module sitting beside the program might import
    cleanly or might raise; the importing file cannot tell. §A113 stored that as `unknowable`, which is honest
    and useless on its own. But the question "does this module import?" is DECIDABLE in one cheap probe that
    imports the module and nothing else -- measured 2026-11-23: a healthy `beta.py` returned 0, a raising
    `alpha.py` returned 1, neither of which required running the program that imports them.

    So the division of labour is exact:
        the learned RULE says this class of fault is worth asking about   (one experience, any program)
        this PROBE decides the answer for the program in front of you     (a fact, not a guess)
    Neither the rule nor the probe ever claims a specific module is broken; the probe observes.
    """
    base = pathlib.Path(world)
    python = interpreter or sys.executable
    try:
        run = subprocess.run([python, "-c", "import " + module], cwd=str(base),
                             capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"module": module, "importable": None, "why": "%s: %s" % (type(exc).__name__, str(exc)[:160])}
    if run.returncode == 0:
        return {"module": module, "importable": True, "exit": 0}
    tail = ((run.stdout or "") + (run.stderr or "")).strip().splitlines()
    return {"module": module, "importable": False, "exit": run.returncode,
            "said": tail[-1][:200] if tail else "",
            "traceback": ((run.stdout or "") + (run.stderr or "")).strip()[-600:]}


def apply_memory(source: str, *, store: pathlib.Path | None = None,
                 world: str | pathlib.Path | None = None,
                 interpreter: str | None = None,
                 probe: bool = True) -> dict[str, Any]:
    """Which of this program's predicted faults are ALREADY KNOWN, and what the known rule says to do.

    This is where one experience changes the next program. The prediction comes from the source; the rule comes
    from the store; the two are matched by the code the failure states, not by program name. A rule learned from
    program A is offered to program B, which is the entire point of storing a condition instead of an action.
    """
    seen = predict(source, world=world, interpreter=interpreter)
    known: dict[str, Any] = STATED.conditions(store)
    matched = []
    # A LOCAL MODULE IS NOT A PREDICTED FAULT AND IT IS THE CASE MEMORY IS FOR: the reader cannot tell whether
    # `beta_mod.py` imports cleanly, so the only thing that can answer is what a previous run of a DIFFERENT
    # program already established about importing neighbouring modules. Offering it here is what makes the
    # second program cheaper than the first -- and it is offered as a RULE (a property of importability), never
    # as "module beta_mod is broken".
    for module in seen.get("unknowable_imports") or []:
        rule = known.get("module_not_importable")
        if not rule:
            continue
        # THE RULE SAYS ASK; THE PROBE ANSWERS. Without a world to probe in there is nothing to ask, and the
        # entry stays `unknowable` rather than becoming an accusation -- measured 2026-11-23, the first version
        # of this block reported a HEALTHY neighbouring module as a fault, which is the cry-wolf error the
        # module's own docstring warns about.
        observed = probe_importable(module, world=world, interpreter=interpreter) if (probe and world) else None
        if observed is not None and observed.get("importable") is True:
            # asked and answered: this module is fine, so there is no fault and nothing to record
            continue
        matched.append({"fault": {"class": ("module_fails_to_import" if observed and observed.get("importable") is False
                                           else "module_may_fail_to_import"),
                                  "module": module,
                                  "detected_by": ("learned_rule+probe" if observed is not None
                                                  else "learned_rule")},
                        "code": "MODULE_NOT_IMPORTABLE",
                        "rule": rule.get("predicate"), "seen_at": rule.get("seen_at"),
                        "values_seen": rule.get("values"),
                        "observed": observed,
                        "act": STATED.acts_for(rule.get("predicate") or {}, module)})
    for fault in seen.get("faults") or []:
        code = "MODULE_NOT_FOUND" if fault["class"] == "missing_python_module" else "NAME_NOT_DEFINED"
        rule = known.get(code.lower())
        if rule:
            matched.append({"fault": fault, "code": code,
                            "rule": rule.get("predicate"), "seen_at": rule.get("seen_at"),
                            "values_seen": rule.get("values"),
                            "act": STATED.acts_for(rule.get("predicate") or {}, fault.get("module")
                                                   or fault.get("name") or "")})
    return {"schema": SCHEMA, "predicted": seen, "rules_matched": matched,
            "known_faults": [m["fault"] for m in matched],
            "unknown_faults": [f for f in seen.get("faults") or [] if f not in [m["fault"] for m in matched]]}
