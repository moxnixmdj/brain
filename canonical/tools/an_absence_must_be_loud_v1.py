#!/usr/bin/env python3
"""An absence must be loud: a missing dependency may never look like a passing engine.

WHY THIS EXISTS
---------------
Two measured failures made this necessary, both in this repository.

1. `semantic_causal_engine_v1.py` imports z3 behind a try/except and sets `z3 = None` on
   failure. `z3_verify_uir_safety` then returns `{"checked": False}` instead of raising.
   A caller that reads only `safe` sees a normal answer. The engine has no idea anything
   is wrong, and neither does anyone reading its output.

2. The same engine's localiser returns `OPEN__NO_CAUSAL_SITES_IN_CPG` when tree-sitter
   is not installed. That string is indistinguishable from a true statement about the
   code -- "I looked and there were no sites" -- when it actually means "I could not
   look at all".

Both were found by re-running a claim that had already been published as 9/13, and both
were indistinguishable from an honest negative until the dependency was installed and
the number did not move. That is the failure mode this file exists to prevent: an
optional dependency that is absent must produce a *distinct, loud* state, never the
state a successful run also produces.

WHAT IS MEASURED
----------------
For each declared optional capability, the preflight answers three questions and keeps
them separate:

  available   can the module be imported at all
  exercised   does it produce a real answer on a known-answer probe
  silent      would the owning module have reported this same output if the dependency
              were missing (the dangerous case)

`CRITICAL` capabilities are the ones whose absence changes a *result* rather than a
*performance*. Those must not be optional in any run whose output will be quoted.

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Parameters stored: 0.
"""
from __future__ import annotations

import dataclasses
import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
from typing import Any, Callable, Sequence

SCHEMA = "BRAIN_AN_ABSENCE_MUST_BE_LOUD_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
MODEL_CALLS = 0
PARAMETERS_STORED = 0


@dataclasses.dataclass(frozen=True)
class Capability:
    """One optional dependency and the probe that can tell presence from absence."""

    name: str
    module: str
    why: str
    probe: str
    critical: bool = True


@dataclasses.dataclass(frozen=True)
class PreflightRow:
    name: str
    module: str
    available: bool
    exercised: bool | None
    probe_output: str
    silent_failure_signature: str
    critical: bool
    why: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @property
    def state(self) -> str:
        if self.available and self.exercised is True:
            return "PRESENT_AND_EXERCISED"
        if self.available and self.exercised is False:
            return "PRESENT_BUT_BROKEN"
        if self.available and self.exercised is None:
            return "PRESENT_UNEXERCISED"
        return "ABSENT"


def _run_probe(probe: str, timeout: int = 120) -> tuple[bool, str]:
    """Run a probe in a FRESH interpreter.

    A fresh process matters: a probe run in this one can pass on a module some earlier
    import already put into `sys.modules`, which is exactly how a missing dependency
    comes to look present.
    """
    try:
        done = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    out = (done.stdout + done.stderr).strip()
    return done.returncode == 0, out[-400:]


# --------------------------------------------------------------------------------------
# The capabilities this repository actually depends on, each with the probe that can
# distinguish "working" from "absent". The probes are known-answer: they must produce a
# specific value, not merely import.
# --------------------------------------------------------------------------------------

CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        name="z3_smt_solver",
        module="z3",
        why=(
            "semantic_causal_engine_v1 gates its safety proof on z3 and returns "
            "checked=False when it is missing. A caller reading only `safe` cannot tell."
        ),
        probe=(
            "import z3\n"
            "x = z3.Int('x')\n"
            "s = z3.Solver()\n"
            "s.add(x > 3)\n"
            "assert s.check() == z3.sat, s.check()\n"
            "print('z3-sat-known-answer-ok')\n"
        ),
        critical=True,
    ),
    Capability(
        name="tree_sitter_runtime",
        module="tree_sitter",
        why=(
            "the CPG localiser reports OPEN__NO_CAUSAL_SITES_IN_CPG when it cannot parse, "
            "which is the same output a genuinely site-free project produces."
        ),
        probe=(
            "import tree_sitter, tree_sitter_python\n"
            "from tree_sitter import Language, Parser\n"
            "p = Parser(Language(tree_sitter_python.language()))\n"
            "tree = p.parse(b'def f():\\n    return 1\\n')\n"
            "assert tree.root_node.has_error is False, 'parse error'\n"
            "print('tree-sitter-python-parse-ok')\n"
        ),
        critical=True,
    ),
    Capability(
        name="tree_sitter_c",
        module="tree_sitter_c",
        why="the C/C++ half of the polyglot CPG silently yields no sites without it.",
        probe=(
            "import tree_sitter_c\n"
            "from tree_sitter import Language, Parser\n"
            "p = Parser(Language(tree_sitter_c.language()))\n"
            "t = p.parse(b'int main(){return 0;}\\n')\n"
            "assert t.root_node.has_error is False\n"
            "print('tree-sitter-c-parse-ok')\n"
        ),
        critical=False,
    ),
    Capability(
        name="c_compiler_with_sanitizers",
        module="gcc",
        why=(
            "the memory-safety walls (cJSON) are verified by ASan/UBSan; without a compiler "
            "the wall is ungraded, not passed."
        ),
        probe=(
            "import subprocess, tempfile, pathlib, os\n"
            "d = tempfile.mkdtemp()\n"
            "src = pathlib.Path(d) / 'a.c'\n"
            "src.write_text('#include <stdlib.h>\\nint main(){char*p=malloc(2);p[5]=1;free(p);return 0;}\\n')\n"
            "b = pathlib.Path(d) / 'a.out'\n"
            "c = subprocess.run(['gcc','-fsanitize=address',str(src),'-o',str(b)],capture_output=True)\n"
            "assert c.returncode == 0, c.stderr[-200:]\n"
            "r = subprocess.run([str(b)],capture_output=True)\n"
            "assert r.returncode != 0, 'ASan did not catch a deliberate overflow'\n"
            "print('asan-known-answer-ok')\n"
        ),
        critical=False,
    ),
)


SILENT_SIGNATURES = {
    "z3_smt_solver": "checked=False from z3_verify_uir_safety",
    "tree_sitter_runtime": "OPEN__NO_CAUSAL_SITES_IN_CPG",
    "tree_sitter_c": "OPEN__NO_CAUSAL_SITES_IN_CPG (C/C++ only)",
    "c_compiler_with_sanitizers": "UNGRADED memory-safety wall",
}


def preflight(capabilities: Sequence[Capability] = CAPABILITIES) -> dict[str, Any]:
    """Measure every declared capability. Absence is reported as absence, never as zero."""
    rows: list[PreflightRow] = []
    for cap in capabilities:
        available = importlib.util.find_spec(cap.module) is not None
        if cap.module in ("gcc",):
            available = shutil.which("gcc") is not None
        exercised, out = (None, "")
        if available:
            exercised, out = _run_probe(cap.probe)
        rows.append(
            PreflightRow(
                name=cap.name,
                module=cap.module,
                available=available,
                exercised=exercised,
                probe_output=out,
                silent_failure_signature=SILENT_SIGNATURES.get(cap.name, ""),
                critical=cap.critical,
                why=cap.why,
            )
        )

    missing_critical = [r.name for r in rows if r.critical and r.state != "PRESENT_AND_EXERCISED"]
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "runtime_model_calls": MODEL_CALLS,
        "parameters_stored": PARAMETERS_STORED,
        "rows": [r.as_dict() for r in rows],
        "states": {r.name: r.state for r in rows},
        "refusal": (
            "REFUSED__CRITICAL_DEPENDENCY_ABSENT" if missing_critical else "OK__ALL_CRITICAL_PRESENT"
        ),
        "missing_critical": missing_critical,
        "rule": (
            "A run whose output will be quoted must refuse to produce a number when a "
            "critical capability is not PRESENT_AND_EXERCISED. The point is not that the "
            "dependency is required; it is that its absence must not be reported in the "
            "same words as a successful search."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    result = preflight()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["refusal"].startswith("OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
