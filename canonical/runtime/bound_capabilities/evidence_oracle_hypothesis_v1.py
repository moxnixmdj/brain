#!/usr/bin/env python3
"""Evidence oracle — property-based postcondition check, confined.

Third oracle family beside CrossHair (symbolic, Z3) and the concrete
13-sample oracle: Hypothesis generates and shrinks counterexamples.  Zero
model, $0.

What was wrong before this version, each measured on a direct call:

  * the property was hard-coded as ``result >= 0`` whatever the docstring
    said -- ``post: _ == x + 1`` over ``return abs(x)`` reported 50 checks
    and no violation although ``x = 0`` violates it;
  * without Hypothesis it claimed 13 checks and no violations for a
    contract that fails, without running anything;
  * the supplied source was ``exec``'d in the host process, so a program
    that wrote outside the repository did so, and ``verified`` was True.

Now the docstring postconditions are parsed exactly as the sibling
concrete oracle parses them (``post: <expr>`` with ``_``/``result`` bound
to the return value and the parameters bound by name), the check runs in
a separate process confined by ``confine_v1`` (user+mount namespace,
chroot onto an empty scratch directory, no network, rlimits), and the
verdict is read back from that process.  Where confinement is unavailable
the oracle says so and does not verify, unless the caller passes
``allow_unconfined`` and accepts that the source ran with the caller's
own authority.

Absence of a counterexample is never proof: ``proves_absence`` is False.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_HYPOTHESIS_V1"
CAPABILITY_ID = "evidence.oracle.hypothesis_property.v1"
PROVIDES = ["evidence.hypothesis.property_violation", "evidence.property_test.verified"]
REQUIRES: list[str] = ["python.source.file.available"]

REPO = pathlib.Path(__file__).resolve().parents[3]

_RAN = frozenset({"CONTRACT_VIOLATION_FOUND", "NO_COUNTEREXAMPLE_FOUND",
                  "NO_COUNTEREXAMPLE_IN_SAMPLE"})

# Runs in the child.  Prints exactly one JSON line at the end; anything the
# source itself prints is before it and ignored.
_PROGRAM = r'''
import inspect, json, re, sys
SRC = __SOURCE__
MAX_EXAMPLES = __MAX_EXAMPLES__
SAMPLE = (-8, -3, -1, 0, 1, 2, 3, 5, 7, 11, 16, 100, -100)
SAFE = {"abs": abs, "min": min, "max": max, "len": len, "sum": sum,
        "int": int, "float": float, "bool": bool}
POST_RE = re.compile(r"^\s*(?:-\s*)?post(?:condition)?\s*:\s*(.+)$", re.I)
out = {"status": "", "checked": 0, "violations": [], "posts": [],
       "hypothesis_available": False, "function": None, "arity": 0}

def emit():
    sys.stdout.write("\n" + json.dumps(out, sort_keys=True) + "\n")
    sys.stdout.flush()
    sys.exit(0)

ns = {"__name__": "__oracle_instance__"}
try:
    exec(compile(SRC, "<oracle_instance>", "exec"), ns)
except BaseException as exc:
    out["status"] = "SOURCE_DOES_NOT_EXECUTE:" + type(exc).__name__
    emit()
fn = ns.get("f")
if not callable(fn):
    defined = [v for v in ns.values() if inspect.isfunction(v)
               and getattr(v.__code__, "co_filename", "") == "<oracle_instance>"]
    fn = defined[0] if len(defined) == 1 else None
if fn is None:
    out["status"] = "NO_FUNCTION_FOUND"
    emit()
out["function"] = fn.__name__
try:
    params = [p.name for p in inspect.signature(fn).parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
except (TypeError, ValueError):
    params = ["x"]
out["arity"] = len(params)
posts = [m.group(1).strip() for m in
         (POST_RE.match(line) for line in (fn.__doc__ or "").splitlines()) if m]
out["posts"] = posts
if not posts:
    out["status"] = "NO_POSTCONDITION_PARSED"
    emit()

def check(values):
    env = dict(SAFE)
    env.update(dict(zip(params, values)))
    env.setdefault("x", values[0] if values else None)
    try:
        result = fn(*values)
    except Exception as exc:
        return {"input": list(values), "reason": "raised " + type(exc).__name__}
    env.update({"_": result, "__return__": result, "result": result})
    for post in posts:
        try:
            ok = bool(eval(post, {"__builtins__": {}}, env))
        except Exception as exc:
            return {"input": list(values), "post": post,
                    "reason": "unevaluable: " + type(exc).__name__}
        if not ok:
            return {"input": list(values), "post": post, "returned": repr(result)}
    return None

try:
    from hypothesis import given, settings, strategies as st, HealthCheck
    out["hypothesis_available"] = True
except Exception:
    given = None

if given is not None and params:
    seen = []
    class Violation(AssertionError):
        pass
    @settings(max_examples=MAX_EXAMPLES, database=None, derandomize=True,
              deadline=None, suppress_health_check=list(HealthCheck))
    @given(st.tuples(*[st.integers(min_value=-1000, max_value=1000) for _ in params]))
    def prop(values):
        seen.append(1)
        bad = check(values)
        if bad is not None:
            out["violations"][:] = [bad]   # the last call is the shrunk minimum
            raise Violation(json.dumps(bad))
    try:
        prop()
    except Violation:
        pass
    except BaseException as exc:
        out["status"] = "ORACLE_RUN_FAILED:" + type(exc).__name__
        emit()
    out["checked"] = len(seen)
    out["status"] = "CONTRACT_VIOLATION_FOUND" if out["violations"] else "NO_COUNTEREXAMPLE_FOUND"
    emit()

# Hypothesis absent: the sibling concrete sample, really executed.
for v in SAMPLE:
    values = tuple([v] * len(params))
    out["checked"] += 1
    bad = check(values)
    if bad is not None:
        out["violations"].append(bad)
out["status"] = "CONTRACT_VIOLATION_FOUND" if out["violations"] else "NO_COUNTEREXAMPLE_IN_SAMPLE"
emit()
'''


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_hypothesis_oracle.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _confinement():
    try:
        from canonical.runtime import confine_v1 as C
        return C if C.available() else None
    except Exception:
        return None


def _hypothesis_site() -> tuple[str, ...]:
    """The site directory Hypothesis is installed in, so the confined child
    can import it when it lives outside /usr.  Read-only inside; nothing
    else of the host becomes visible."""
    try:
        import importlib.util
        spec = importlib.util.find_spec("hypothesis")
        origin = getattr(spec, "origin", None) if spec else None
        if not origin:
            return ()
        site = pathlib.Path(origin).resolve().parent.parent
        return (str(site),) if site.is_dir() else ()
    except Exception:
        return ()


def _parse_child(stdout: str) -> dict[str, Any] | None:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if isinstance(data, dict) and "status" in data:
                return data
    return None


def _run_child(program: str, scratch: pathlib.Path, timeout: int,
               allow_unconfined: bool) -> tuple[dict[str, Any] | None, bool, str]:
    """(child verdict or None, confined?, failure detail)."""
    confine = _confinement()
    if confine is not None:
        r = confine.run(program, str(scratch), timeout=timeout, ro_binds=_hypothesis_site())
        if r.get("verdict") == "OK":
            return _parse_child(r.get("output") or ""), True, ""
        return None, True, "CONFINED_RUN_" + str(r.get("verdict")) + ":" + str(r.get("output") or "")[-300:]
    if not allow_unconfined:
        return None, False, "CONFINEMENT_UNAVAILABLE"
    script = scratch / "oracle_program.py"
    script.write_text(program, encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(script)], cwd=str(scratch), timeout=timeout,
                           capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return None, False, "UNCONFINED_RUN_TIMEOUT"
    if r.returncode != 0:
        return None, False, "UNCONFINED_RUN_FAILED:" + (r.stderr or "")[-300:]
    return _parse_child(r.stdout), False, ""


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    source = args.get("source")
    if source is None and args.get("source_path"):
        sp = (repo / str(args["source_path"])).resolve()
        if sp == repo or repo not in sp.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        source = sp.read_text(encoding="utf-8")
    if not source:
        source = "def f(x):\n    \"\"\"post: _ >= 0\"\"\"\n    return abs(x)\n"
    max_examples = max(1, min(int(args.get("max_examples") or 50), 10000))
    timeout = max(5, min(int(args.get("timeout_s") or 60), 600))
    allow_unconfined = bool(args.get("allow_unconfined"))
    program = (_PROGRAM.replace("__SOURCE__", repr(str(source)))
               .replace("__MAX_EXAMPLES__", str(max_examples)))

    # The child's only writable place is an empty scratch directory, never
    # the repository the caller handed over.
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=".hypothesis_oracle_", dir=str(output.parent)))
    try:
        child, confined, detail = _run_child(program, scratch, timeout, allow_unconfined)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if child is None:
        child = {"status": detail or "ORACLE_RUN_FAILED", "checked": 0, "violations": [],
                 "posts": [], "hypothesis_available": False, "function": None, "arity": 0}
    status = str(child.get("status") or "ORACLE_RUN_FAILED")
    violations = list(child.get("violations") or [])
    checked = int(child.get("checked") or 0)
    ran = status in _RAN and checked > 0
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_excerpt": source[:500],
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "status": status,
        "function": child.get("function"),
        "posts": list(child.get("posts") or []),
        "hypothesis_available": bool(child.get("hypothesis_available")),
        "checked": checked,
        "violations": violations,
        "confined": bool(confined),
        "max_examples": max_examples,
        "proves_absence": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": bool(ran),
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "evidence_oracle_hypothesis_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "status": status,
        "checked": checked,
        "violations": violations,
        "violation_count": len(violations),
        "hypothesis_available": artifact["hypothesis_available"],
        "confined": artifact["confined"],
        "proves_absence": False,
        "verified": bool(ran),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
