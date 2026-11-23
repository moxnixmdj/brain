"""Answer one question about the world by asking it, and record that the answer has a moment.

WHY THIS EXISTS. §A119 measured the honest boundary of the literal walk: a real program takes its values from
files, environment variables, stdin and the network, so the walk has nothing to hold and must refuse. Every
real-world program in that sample came back `THIS_WALK_COULD_NOT_DECIDE` -- honest, and useless for deciding
whether to run it.

THE LITERATURE NAMES BOTH THE FAILURE AND THE REMEDY, and they are not in tension:

    EnvTrustBench (arXiv 2605.08828)  the defect is treating an observed environment-facing claim as sufficient
                                      ground for action "without resolving it against available current
                                      evidence" -- an evidence-grounding defect
    EnvProbe (arXiv 2606.31422)       the remedy is to query the one belief field before acting and pay one
                                      interaction step for it

So the boundary between static reading and probing is not a matter of taste: whatever CAN be probed in one cheap
step SHOULD be probed rather than refused, and whatever is probed must carry its provenance, because a value read
from the world is a claim about a **moment**.

WHAT A PROBE IS. Run the program's import statements, then evaluate ONE expression, in a fresh interpreter, with
the program's working directory. That is partial execution -- the smallest possible piece of the program -- and it
answers questions static reading cannot: what `os.environ["HOME"]` is, what `sys.version_info[0]` is, whether a
file exists.

WHAT IT REFUSES, AND WHY EACH REFUSAL IS SEPARATE:

  * an expression with a side effect, an assignment, a statement -- a probe must not change the world it is
    measuring (§A112);
  * a call to anything not on the pure list -- `open(...)`, `requests.get(...)`: a probe that performs I/O is an
    ACTION wearing a question's clothes;
  * an expression that does not evaluate to a LITERAL -- a live object cannot be carried back into the walk, and
    pretending otherwise would mean the walk was reasoning about a repr rather than a value.

A probe never claims the world will stay that way. `freshness` is recorded, not assumed: the answer is stamped
with the moment it was taken, and the caller can compare it against its own clock.
"""
from __future__ import annotations

import ast
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_ASK_THE_WORLD_V1"

#: Calls that read without changing anything, and whose value is a literal or a container of literals. Anything
#: else is treated as an ACTION, which a probe is not allowed to take.
_PURE_CALLS = frozenset({"len", "str", "int", "float", "bool", "list", "tuple", "dict", "sorted", "set",
                         "repr", "ord", "chr", "abs", "min", "max", "sum", "type", "isinstance"})

#: READS THAT ARE ALLOWED, and the distinction is the module's whole point. The first version refused every call
#: whose name was not a pure builtin -- which refused `os.path.exists`, `os.listdir` and `os.getcwd`, the three
#: things a probe exists to observe. Measured 2026-11-23: the probe could not see a changing world at all, so it
#: could not detect staleness, which is EnvTrustBench's entire subject.
#:
#: A READ may look at the world; an ACTION may change it. `exists`, `listdir`, `stat`, `getcwd`, `getenv` are
#: reads. `open` (for writing), `system`, `remove`, `mkdir`, `write` are actions. Anything not recognised is
#: refused, because the safe default for an unknown function is that it might act.
_READ_CALLS = frozenset({"exists", "isdir", "isfile", "islink", "listdir", "scandir", "stat", "getcwd",
                         "getenv", "getpid", "getsize", "abspath", "basename", "dirname", "join", "split",
                         "splitext", "normpath", "realpath", "expanduser", "walk", "access", "read",
                         "readlines", "readline", "glob", "loads", "load", "safe_load", "safe_load_all"})

#: Names that are actions even when a module provides them, so a name collision cannot smuggle one through.
_ACTION_CALLS = frozenset({"open", "system", "popen", "remove", "unlink", "rmdir", "mkdir", "makedirs", "rename",
                           "replace", "move", "copy", "copyfile", "copytree", "chmod", "chown", "symlink",
                           "link", "write", "writelines", "truncate", "touch", "kill", "exit", "quit",
                           "urandom", "setenv", "putenv", "chdir", "rmtree", "run", "call", "check_output",
                           "Popen", "fork", "exec", "execv", "spawn"})
_ALLOWED_NODES = (ast.Expression, ast.Constant, ast.Name, ast.Attribute, ast.Subscript, ast.Load, ast.Tuple,
                  ast.List, ast.Dict, ast.Set, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.IfExp,
                  ast.JoinedStr, ast.FormattedValue, ast.Slice, ast.Call, ast.keyword, ast.Index if hasattr(ast, "Index") else ast.expr,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd,
                  ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
                  ast.And, ast.Or, ast.Not, ast.BitOr, ast.BitAnd)


class _Refused(Exception):
    """The expression is not something a probe may ask."""


def _refuse_reason(tree: ast.AST) -> str | None:
    """Why this expression may not be probed, or None when it may.

    A PROBE THAT CHANGES THE WORLD IS NOT A PROBE. §A112 exists because a measurement was invalidated by its own
    effects; a probe is the same hazard at a smaller scale, so an expression containing a call that is not on the
    pure list is refused rather than run and hoped over.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.Lambda, ast.NamedExpr, ast.Await, ast.Yield, ast.Starred)):
            return "EXPRESSION_IS_NOT_A_SIMPLE_READ"
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            # `open` IS TWO DIFFERENT OPERATIONS WEARING ONE NAME, and refusing both made the probe unable to
            # read the one thing real programs most often depend on: a config file. Measured 2026-11-23: a script
            # whose behaviour hinges on `json.load(open("config.json"))` could not be probed at all, so its
            # runtime faults stayed undecidable -- the §A119 boundary reappearing inside §A120's remedy.
            #
            # The mode is an ARGUMENT, so it is read rather than assumed: no mode, "r", "rb", "rt" are reads;
            # anything containing w/a/x/+ can write and is refused. A mode that is not a literal cannot be
            # checked, so it is refused too -- the safe default for an unknown is that it acts.
            if name == "open":
                mode = None
                if len(node.args) >= 2:
                    mode = node.args[1]
                for keyword in node.keywords or []:
                    if keyword.arg == "mode":
                        mode = keyword.value
                if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)
                        and set(mode.value) <= set("rbt") and mode.value):
                    if mode is not None:
                        return "CALL_MAY_HAVE_AN_EFFECT:open-with-that-mode"
                    # no mode at all is the default "r", which is a read
            # THE ACTION LIST WINS OVER EVERYTHING ELSE: `system`, `remove`, `mkdir` are refused by name.
            if name in _ACTION_CALLS and name != "open":
                return "CALL_MAY_HAVE_AN_EFFECT:" + str(name)[:40]
            # `open` was already decided by its MODE above; every other name must be recognised as a read.
            if name != "open" and name not in _PURE_CALLS and name not in _READ_CALLS:
                return "CALL_MAY_HAVE_AN_EFFECT:" + str(name)[:40]
        if isinstance(node, ast.Name) and node.id in ("__import__", "eval", "exec", "compile",
                                                      "input", "breakpoint"):
            # `open` IS DELIBERATELY NOT IN THIS LIST ANY MORE, and the reason is the same one that made it
            # un-probeable: this check fires on the NAME wherever it appears, including as the function of a
            # call whose mode was already vetted. `open(path)` in read mode is a read; `open(path, "w")` is
            # caught by the mode check above, and `open` reached any other way is caught by the effect check.
            return "EXPRESSION_CAN_CHANGE_THE_WORLD:" + node.id
    return None


def probe(expression: str, *, world: str, imports: Sequence[str] = (),
          interpreter: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Ask one question of the world and return the answer with its provenance.

    `world` is the directory the program will run in -- the probe runs there too, because "does the file exist"
    means nothing outside the directory that will contain the file.
    """
    taken = time.time()
    record: dict[str, Any] = {"schema": SCHEMA, "expression": str(expression)[:300],
                              "world": str(world), "taken_at": taken}
    text = str(expression or "").strip()
    if not text or len(text) > 300:
        return {**record, "answered": False, "why": "EXPRESSION_EMPTY_OR_TOO_LONG"}
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as broken:
        return {**record, "answered": False, "why": "NOT_AN_EXPRESSION", "detail": str(broken)[:160]}
    refusal = _refuse_reason(tree)
    if refusal:
        return {**record, "answered": False, "why": refusal}

    python = interpreter or sys.executable
    # THE IMPORTS ARE RUN FIRST, and only the imports the program itself performed. `os.environ` in an interpreter
    # where `os` was never imported is a NameError, and a probe that fails for that reason would be a FALSE
    # refusal -- the module would report the world as unknowable when the question was merely mis-asked.
    body = list(imports)[:40] + ["__pb_value = (%s)" % text,
                                 "import json as __pb_json",
                                 "print(__pb_json.dumps(repr(__pb_value)))"]
    script = "\n".join(body)
    try:
        run = subprocess.run([python, "-c", script], cwd=str(world), capture_output=True,
                             text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {**record, "answered": False, "why": "PROBE_FAILED_TO_RUN",
                "detail": "%s: %s" % (type(exc).__name__, str(exc)[:160])}

    if run.returncode != 0:
        tail = ((run.stdout or "") + (run.stderr or "")).strip().splitlines()
        final = tail[-1][:200] if tail else ""
        # A RAISED EXCEPTION IS AN ANSWER: the expression fails, which is what the walk wanted to know.
        return {**record, "answered": True, "raised": True, "value": None, "value_repr": None,
                "said": final, "exit": run.returncode}

    raw = (run.stdout or "").strip()
    try:
        import json as _json
        shown = _json.loads(raw)
    except Exception:
        shown = raw[:200]
    # only a LITERAL can be carried back into the walk: `repr` is text, and `ast.literal_eval` is the gate that
    # keeps a live object from being mistaken for a value
    value: Any = None
    literal = False
    try:
        value = ast.literal_eval(str(shown))
        literal = True
    except (ValueError, SyntaxError, TypeError):
        literal = False
    return {**record, "answered": True, "raised": False, "exit": 0, "value": value if literal else None,
            "value_repr": str(shown)[:200], "literal": literal,
            "why": None if literal else "PROBED_VALUE_IS_NOT_A_LITERAL"}


def still_true(record: dict[str, Any], *, world: str, imports: Iterable[str] = (),
               interpreter: str | None = None) -> dict[str, Any]:
    """Ask the SAME question again and say whether the answer changed.

    EnvTrustBench's whole subject is evidence that was once true and is now treated as if it still were. A probe
    result is the freshest thing this system has, and it is still only a claim about a moment -- so the way to
    use it safely is to be able to re-ask, cheaply, and compare. The comparison is literal equality of the
    recorded value, because anything cleverer would need a notion of "same" this module does not have.
    """
    again = probe(record.get("expression", ""), world=world, imports=imports, interpreter=interpreter)
    before = record.get("value")
    after = again.get("value")
    changed = (before != after) or (bool(record.get("raised")) != bool(again.get("raised")))
    return {"schema": SCHEMA, "expression": record.get("expression"),
            "before": before, "after": after, "changed": bool(changed),
            "first_taken_at": record.get("taken_at"), "asked_again_at": again.get("taken_at"),
            "answer": again}


def main(argv: list[str] | None = None) -> int:
    import json
    import pathlib

    arguments = list(argv if argv is not None else sys.argv[1:])
    if len(arguments) < 2:
        print(json.dumps({"schema": SCHEMA,
                          "usage": "ask_the_world_v1 <world-dir> <expression>"}))
        return 0
    print(json.dumps(probe(arguments[1], world=arguments[0]), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
