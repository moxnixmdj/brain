#!/usr/bin/env python3
"""What can be OBSERVED about a piece of code, measured by running it, not by reading it.

WHY THIS EXISTS
---------------
Measured 2026-11-14 (record `ORACLE_ACTIVE_ON_NEW_PULL_REQUESTS_20261114_V1.json`): of 230 real
target/example pairs, the taught-edit organ altered 44 files, and only 11 of those could be observed
at all. The reason was not the organ and not the oracle: 19 of the 20 unobservable targets had **no
loadable function**. All 19 are class bodies:

```
9  ClassDef + Expr + ImportFrom
4  ClassDef + Import            3  Assign + ClassDef + Import + ImportFrom
```

So the single bottleneck, named and then measured, is REACH: a lesson is only checkable where there
is a surface that can be built from plain values and observed after it runs. Real code is mostly
classes, and this instrument had no way to see one.

WHAT THIS DOES
--------------
It answers, for one source text and nothing else: *which surfaces of this can I build, drive, and
compare?* Each surface is a `(kind, name, build, observe)` where `observe(receiver=None)` returns a
comparable value. Six kinds, in the order a reader would try them:

  FUNCTION       a top-level function, called with plain values
  METHOD         a method on a class that can be instantiated from plain values alone
  STATE          the instance state of such a class, after construction
  CLASS_ATTRIBUTE  an attribute read off the class itself (dataclass fields, constants)
  MODULE_BINDING  a module-level assignment
  IMPORT_SET     the names this module imports, and where from

OBSERVATION IS THE PATH, NOT THE VALUE
--------------------------------------
For anything callable the observation is the PATH taken -- line offsets relative to the function's
first line -- plus the exception class if it raised. This is the correction measured in the previous
round: `return 1` in a demonstration and `return 2` in a target are the same behaviour, and comparing
returned values reported every faithfully copied change as wrong.

For containers of objects the observation is the state signature. A value that still carries a memory
address after rendering is reported as UNOBSERVABLE, never as a difference.

WHY A DECLARATION SURFACE IS A SEPARATE THING
------------------------------------------------
Measured 2026-11-14, on the same 44 pairs: 19 of them are edits to files whose code cannot be
executed here at all, and when those files are made executable the edit still moves nothing --
because the change is *declarative*. `Optional[str]` becomes `str | None`; `List[str]` becomes
`list[str]`; `from typing import List` disappears. Python never evaluates a function's annotations at
call time, so no amount of calling, instantiating or driving can see it. An observer that only
watches execution is structurally blind to this class of change, and it is a large class.

So `SIGNATURE` reads annotations the way the source wrote them, and `comparable` labels it: a
difference on a declaration surface proves the *text* changed, not that any behaviour changed. The
two verdicts are never merged.

WHAT THIS IS NOT
----------------
Not a test generator, not an oracle, and not a claim that a reachable surface is a *semantically*
right one. It widens what can be asked; `settled_admission_v1` and the differential witness search
still decide. Zero model calls, zero network, $0.

Authority: NONE.
"""
from __future__ import annotations

import ast
import inspect
import sys
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_OBSERVABLE_SURFACE_V1"
AUTHORITY = "NONE"

# Plain values a surface can be built from. Deliberately small: a surface that needs anything else is
# not reachable by this instrument and is reported as such rather than guessed at.
PLAIN: tuple[Any, ...] = (0, 1, -1, 2, "", "a", "ABCDEFG", [], (), {}, None, True)

# Reuse the renderer that already refuses to compare memory addresses. Imported rather than copied so
# there is one implementation of "what is a comparable value" in the tree.
try:                                                        # pragma: no cover - import guard
    from canonical.swe_kernel.differential_witness_v1 import _render as _render_value
except Exception:                                            # noqa: BLE001 - a fallback that says so
    def _render_value(value: Any, budget: int = 4000) -> str:
        return f"<unrenderable {type(value).__name__}>"

_RENDER_FAILED = " at an address>"


# ---------------------------------------------------------------------------------- observation

def path_of(fn: Callable[..., Any], *args: Any) -> Any:
    """The line offsets the function executes, or the exception class and the offsets before it.

    Line offsets are relative to the function's first line, which is what makes them comparable
    between two files: the same guard on the same line of a copied function gives the same offsets.
    """
    offsets: list[int] = []
    first = getattr(getattr(fn, "__code__", None), "co_firstlineno", 0)

    def trace(frame, event, _arg):
        if frame.f_code is fn.__code__ and event == "line":
            offsets.append(frame.f_lineno - first)
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        fn(*args)
    except BaseException as error:                            # noqa: BLE001 - a raise is an answer
        return ("raise", type(error).__name__, tuple(offsets))
    finally:
        sys.settrace(previous)
    return tuple(offsets)


def state_of(receiver: Any) -> str:
    """A comparable signature of an object's own state, or UNOBSERVABLE when addresses survive."""
    try:
        attributes = dict(vars(receiver))
    except TypeError:
        return "UNOBSERVABLE: no __dict__"
    pieces = []
    for name in sorted(attributes):
        rendered = _render_value(attributes[name])
        if _RENDER_FAILED in rendered or "0x" in rendered:
            pieces.append(f"{name}=UNOBSERVABLE")
        else:
            pieces.append(f"{name}={rendered}")
    return "{" + ", ".join(pieces) + "}"


def _arity(fn: Callable[..., Any]) -> int:
    try:
        return len([p for p in inspect.signature(fn).parameters.values()
                    if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    except (TypeError, ValueError):
        return 0


def _fill(arity: int, value: Any) -> tuple[Any, ...]:
    """One interesting value for the first parameter, a plain one for the rest."""
    return (value,) + tuple(PLAIN[: max(0, arity - 1)])


# ------------------------------------------------------------------------------------ the surfaces

def _top_level(tree: ast.Module) -> dict[str, Any]:
    functions: dict[str, ast.AST] = {}
    classes: dict[str, ast.ClassDef] = {}
    bindings: list[str] = []
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node
        elif isinstance(node, ast.ClassDef):
            classes[node.name] = node
        elif isinstance(node, ast.Assign):
            bindings += [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            bindings.append(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(node))
    return {"functions": functions, "classes": classes,
            "bindings": bindings, "imports": imports}


def _exec(source: str) -> tuple[dict[str, Any] | None, str]:
    namespace: dict[str, Any] = {"__name__": "_observable_surface"}
    try:
        exec(compile(source, "<observable>", "exec"), namespace)     # noqa: S102
    except BaseException as error:                                    # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"
    return namespace, ""


EXTRACTABLE = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def base_symbol(base: ast.AST, imported: Sequence[ast.AST]) -> bool:
    """Is this base name one of the symbols the module's own imports bind?"""
    if not isinstance(base, ast.Name):
        return False
    for statement in imported:
        for alias in getattr(statement, "names", []):
            bound = (alias.asname or alias.name).split(".")[0]
            if bound == base.id:
                return True
    return False


def _resolves(statement: ast.AST) -> bool:
    """Does this import resolve on this machine? Lenient extraction keeps only the ones that do."""
    line = ast.unparse(statement)
    try:
        exec(compile(line, "<import-check>", "exec"), {})       # noqa: S102 - an import probe
    except BaseException:                                       # noqa: BLE001
        return False
    return True


def extract(source: str, name: str, strict: bool = True) -> str:
    """See below. `strict` False additionally allows symbols the module itself imports.

    The two settings answer two different questions and must never be confused:

      strict=True   the definition's own behaviour is intact. A base from an import is refused,
                    because the base's behaviour is part of the class and the extracted module does
                    not have it. Use this when a difference must MEAN something.
      strict=False  the definition's TEXT can be executed, with the module's own imports available
                    to the names it mentions. Use this to find WHERE a change is visible. A
                    difference found this way says "the text differs here"; it does not say the code
                    behaves differently, because the imports may not resolve in the real project.

    """
    """One top-level definition, moved into its own module, with the module's imports and constants.

    Measured 2026-11-14: a visited slice of the real world is mostly files that cannot be imported
    here at all -- 29 of the 41 unvisitable files in the held-out corpus name a third-party module
    (`pandas`, `boto3`, `jax`), 7 use relative imports, 5 read an attribute at import time. The
    CHANGE inside such a file is still a class body, and a class body is exactly what this instrument
    was built for. Moving it into its own module -- keeping the imports and constants the module
    bound -- makes it buildable and driveable, and it is honest as long as three things hold:

      * the class's bases are builtins, or nothing: otherwise the base's behaviour is missing;
      * no body statement binds a NAME (a class variable read by a method) from an import;
      * the caller is told, in `extracted`, that this is what happened.

    A definition this cannot do that for is reported unreachable, never patched with a stub.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    preamble = []
    imported: list[ast.AST] = []
    wanted = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # `preamble` is what is KEPT; `imported` is everything the module originally bound, and
            # it is what `base_symbol` must read. Measured: dropping an unresolved import from the
            # preamble also made the base names it bound invisible, so every subclass of `ABC` was
            # refused twice over.
            imported.append(node)
            if strict or _resolves(node):
                preamble.append(ast.unparse(node))
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            preamble.append(ast.unparse(node))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            preamble.append(ast.unparse(node))
        # The definition branch has to be tested on its own: `FunctionDef` is not a statement kind
        # the branches above match, but a chain that ends in `elif` only reaches this one when every
        # earlier test was FALSE, which is not what the intent was -- measured, extraction returned
        # the empty string for every function in a file and the file was reported unvisitable.
        if isinstance(node, EXTRACTABLE) and getattr(node, "name", None) == name:
            wanted = node
    if wanted is None:
        return ""
    if isinstance(wanted, EXTRACTABLE[0]):
        for base in wanted.bases:
            # A base from an import (`ABC`, `Enum`, a project class) carries behaviour this module no
            # longer has, and a base this module does not define is missing too. Only `object` (or
            # nothing) leaves the class's own behaviour intact. Measured: `class FormatConverter(ABC)`
            # with `ABC` from `abc` must be refused, not given a stub -- a stub would be a different
            # class and every observation of it would be a fabrication.
            rendered = ast.unparse(base)
            if rendered != "object" and not (not strict and base_symbol(base, imported)):
                return ""
    return "\n".join(preamble + [ast.unparse(wanted)]) + "\n"


def surfaces(source: str, _try_extraction: bool = True, strict: bool = True) -> dict[str, Any]:
    """Every surface of `source` that can be built and observed, with the reason for each one not.

    The result is deterministic and JSON-shaped. `unreachable` is as important as `surfaces`: it is
    the list of things this instrument is admitting it cannot see, so a later "no difference found"
    can be read as "no difference on these surfaces" rather than "equivalent".
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return {"schema": SCHEMA, "authority": AUTHORITY, "ok": False,
                "detail": f"UNPARSEABLE: {error}", "surfaces": [], "unreachable": []}
    parts = _top_level(tree)
    namespace, why = _exec(source)
    found: list[dict[str, Any]] = []
    unreachable: list[dict[str, str]] = []

    extracted = ""
    if namespace is None and not _try_extraction:
        return {"schema": SCHEMA, "authority": AUTHORITY, "ok": False,
                "detail": f"WILL_NOT_EXECUTE: {why}", "surfaces": [],
                "unreachable": [], "extracted": ""}
    if namespace is None:
        # The module will not execute as a whole. Try every top-level class and function on its own,
        # with the module's imports and constants, and say so in the answer.
        saved = why
        found = []
        unreachable = []
        tried = 0
        for node in tree.body:
            if not isinstance(node, EXTRACTABLE):
                continue
            tried += 1
            part = extract(source, node.name, strict=strict)
            if not part:
                unreachable.append({"kind": "EXTRACTED", "name": node.name,
                                    "why": "its base class or its body comes from an import"})
                continue
            # A bare literal in a preamble must not be left where a constant belongs; and a partial
            # answer must never try to extract again -- measured, that recursed 965 deep.
            partial = surfaces(part, _try_extraction=False, strict=strict)
            if not partial["ok"]:
                unreachable.append({"kind": "EXTRACTED", "name": node.name,
                                    "why": partial["detail"][:120]})
                continue
            found.extend(partial["surfaces"])
            extracted += ("; " if extracted else "") + node.name
        if not found:
            return {"schema": SCHEMA, "authority": AUTHORITY, "ok": False,
                    "detail": f"WILL_NOT_EXECUTE: {saved}", "surfaces": [],
                    "unreachable": unreachable, "extracted": ""}
        return {"schema": SCHEMA, "authority": AUTHORITY, "ok": True,
                "detail": f"PARTIAL: the module did not import ({saved}), "
                          f"{tried} top-level definition(s) were each moved to their own module",
                "surfaces": found, "unreachable": unreachable, "extracted": extracted}

    # IMPORT_SET: the cheapest observable there is, and it catches the class of change that only
    # moves a name from one module to another.
    if parts["imports"]:
        found.append({"kind": "IMPORT_SET", "name": "imports",
                      "observe": tuple(parts["imports"])})

    for name in parts["bindings"]:
        if name not in namespace:
            unreachable.append({"kind": "MODULE_BINDING", "name": name,
                                "why": "the assignment did not happen at import time"})
            continue
        found.append({"kind": "MODULE_BINDING", "name": name,
                      "observe": _render_value(namespace[name])})

    for name in parts["functions"]:
        fn = namespace.get(name)
        if not callable(fn):
            unreachable.append({"kind": "FUNCTION", "name": name, "why": "not callable"})
            continue
        arity = _arity(fn)
        if arity == 0:
            found.append({"kind": "FUNCTION", "name": name, "observe": path_of(fn)})
            continue
        if arity > 3:
            unreachable.append({"kind": "FUNCTION", "name": name,
                                "why": f"takes {arity} parameters; this instrument drives up to 3"})
            continue
        found.append({"kind": "FUNCTION", "name": name,
                      "observe": {f"{value!r}": path_of(fn, *_fill(arity, value))
                                  for value in PLAIN}})

    for name, node in parts["classes"].items():
        cls = namespace.get(name)
        if not isinstance(cls, type):
            unreachable.append({"kind": "CLASS", "name": name, "why": "not a class after exec"})
            continue
        # STATE and METHOD need a receiver. One that cannot be built from plain values is the exact
        # shape of the 19 unobservable targets measured last round, so it is reported as such.
        receiver, receiver_why = _build(cls)
        if receiver is None:
            unreachable.append({"kind": "CLASS", "name": name, "why": receiver_why})
        else:
            found.append({"kind": "STATE", "name": name, "observe": state_of(receiver)})
            for method in sorted(vars(cls)):
                if method.startswith("__") and method not in ("__call__", "__len__", "__iter__",
                                                              "__eq__", "__hash__", "__str__"):
                    continue
                fn = getattr(receiver, method, None)
                if not callable(fn):
                    continue
                arity = _arity(fn)
                if arity == 0:
                    found.append({"kind": "METHOD", "name": f"{name}.{method}",
                                  "observe": path_of(fn)})
                elif arity <= 2:
                    found.append({"kind": "METHOD", "name": f"{name}.{method}",
                                  "observe": {f"{value!r}": path_of(fn, *_fill(arity, value))
                                              for value in PLAIN}})
                else:
                    unreachable.append({"kind": "METHOD", "name": f"{name}.{method}",
                                        "why": f"takes {arity} parameters"})
        # CLASS_ATTRIBUTE: readable without a receiver, which is what makes dataclasses observable.
        for attribute in sorted(vars(cls)):
            if attribute.startswith("__"):
                continue
            value = getattr(cls, attribute, None)
            if callable(value) or isinstance(value, (classmethod, staticmethod, property)):
                continue
            found.append({"kind": "CLASS_ATTRIBUTE", "name": f"{name}.{attribute}",
                          "observe": _render_value(value)})

    return {"schema": SCHEMA, "authority": AUTHORITY, "ok": True, "detail": "",
            "surfaces": found, "unreachable": unreachable, "extracted": extracted}


def _annotation_text(node: ast.AST | None) -> str:
    """The annotation as the source wrote it. `Optional[str]` and `str | None` are different here on
    purpose: two spellings of one meaning is exactly the change that has to be learnable."""
    if node is None:
        return ""
    try:
        text = ast.unparse(node)
    except Exception:                                          # noqa: BLE001
        return "<unprintable>"
    # `typing.Optional[X]` and `Optional[X]` are the same spelling of the same thing; normalise the
    # import prefix only, never the form.
    return text.replace("typing.", "")


def _signature_of(node: ast.AST, prefix: str = "") -> str:
    arguments = node.args
    parts = []
    for argument in list(arguments.posonlyargs) + list(arguments.args):
        parts.append(argument.arg + (f":{_annotation_text(argument.annotation)}"
                                     if argument.annotation else ""))
    if arguments.vararg:
        parts.append("*" + arguments.vararg.arg)
    elif arguments.kwonlyargs:
        parts.append("*")
    for argument in arguments.kwonlyargs:
        parts.append(argument.arg + (f":{_annotation_text(argument.annotation)}"
                                     if argument.annotation else ""))
    if arguments.kwarg:
        parts.append("**" + arguments.kwarg.arg)
    returns = _annotation_text(node.returns)
    return f"{prefix}({', '.join(parts)})" + (f" -> {returns}" if returns else "")


def declarations(source: str) -> dict[str, Any]:
    """Every function and method's signature, as written, plus every class-level annotated field.

    This is the surface that sees a change no execution can see. It never runs the code, so it works
    on files that will not import at all -- which is most of the corpus.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    found: dict[str, Any] = {}

    def take(node: ast.AST, prefix: str) -> None:
        for child in getattr(node, "body", []):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[f"SIGNATURE:{prefix}{child.name}"] = _signature_of(child)
                # A function body can declare too (`x: int = 0` in a local scope). Walk in, so those
                # are seen as declarations rather than silently dropped.
                take(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.ClassDef):
                take(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.AnnAssign):
                target = child.target
                label = (target.id if isinstance(target, ast.Name)
                         else ast.unparse(target) if isinstance(target, ast.Attribute) else "")
                if label:
                    found[f"DECLARED_FIELD:{prefix}{label}"] = _annotation_text(child.annotation)

    take(tree, "")
    return found


def _build(cls: type) -> tuple[Any | None, str]:
    """An instance built from plain values alone, or the reason there is none."""
    try:
        if cls.__init__ is object.__init__:
            return cls(), ""
    except BaseException as error:                            # noqa: BLE001
        return None, f"the default constructor raised {type(error).__name__}"
    try:
        arity = _arity(cls)
    except Exception:                                          # noqa: BLE001
        return None, "the constructor's signature cannot be read"
    if arity == 0:
        try:
            return cls(), ""
        except BaseException as error:                         # noqa: BLE001
            return None, f"the constructor raised {type(error).__name__}"
    if arity > 3:
        return None, f"the constructor takes {arity} parameters; this instrument drives up to 3"
    seen: set[str] = set()
    for value in PLAIN:
        args = _fill(arity, value)
        try:
            return cls(*args), ""
        except BaseException as error:                         # noqa: BLE001
            seen.add(type(error).__name__)
    return None, f"the constructor rejected every plain-value argument set ({', '.join(sorted(seen))})"


def observe(source: str, strict: bool = True) -> dict[str, Any]:
    """`surfaces` flattened to `{key: value}`, which is the form a comparison needs.

    `strict=True` only reports observations whose meaning is intact (see `extract`). `strict=False`
    also reports what can be read from a definition moved out of a module that will not import, which
    is how a change in a `pandas`-bound class can be LOCATED. A difference under `strict=False` is
    evidence about text and must never be quoted as evidence about behaviour.
    """
    result = surfaces(source, strict=strict)
    flat: dict[str, Any] = dict(declarations(source))
    for surface in result["surfaces"]:
        flat[f"{surface['kind']}:{surface['name']}"] = surface["observe"]
    return {"schema": SCHEMA, "authority": AUTHORITY, "ok": result["ok"],
            "detail": result["detail"], "observed": flat,
            "surface_count": len(flat),
            "declared": sum(1 for k in flat if k.startswith(("SIGNATURE:", "DECLARED_FIELD:"))),
            "ran": sum(1 for k in flat if not k.startswith(("SIGNATURE:", "DECLARED_FIELD:"))),
            "extracted": result.get("extracted", ""),
            "strict": strict, "unreachable": result["unreachable"]}


def comparable(one: Mapping[str, Any], other: Mapping[str, Any]) -> dict[str, Any]:
    """Which observations differ, and which are unobservable on either side (never a difference)."""
    keys = sorted(set(one["observed"]) | set(other["observed"]))
    differing, unobservable = [], []
    behaviour, declaration = 0, 0
    for key in keys:
        left, right = one["observed"].get(key), other["observed"].get(key)
        if "UNOBSERVABLE" in str(left) or "UNOBSERVABLE" in str(right):
            unobservable.append(key)
        elif left != right:
            is_declaration = key.startswith(("SIGNATURE:", "DECLARED_FIELD:"))
            if is_declaration:
                declaration += 1
            else:
                behaviour += 1
            differing.append({"key": key, "surface": "declaration" if is_declaration
                              else "behaviour",
                              "before": str(left)[:200], "after": str(right)[:200]})
    return {"schema": SCHEMA, "authority": AUTHORITY, "differing": differing,
            "behaviour_differences": behaviour, "declaration_differences": declaration,
            "unobservable": unobservable, "compared": len(keys),
            "reached_before": one.get("surface_count", 0),
            "reached_after": other.get("surface_count", 0)}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    import pathlib

    parser = argparse.ArgumentParser(description="What can be observed about a file, by running it.")
    parser.add_argument("--before", type=pathlib.Path, required=True)
    parser.add_argument("--after", type=pathlib.Path, required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--lenient", action="store_true",
                        help="also locate changes in definitions moved out of a module that will "
                             "not import; a difference found this way is NOT behavioural evidence")
    args = parser.parse_args(argv)
    report = comparable(observe(args.before.read_text(), strict=not args.lenient),
                        observe(args.after.read_text(), strict=not args.lenient))
    text = json.dumps(report, indent=1)
    if args.json:
        args.json.write_text(text + "\n")
        print("written ->", args.json)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
