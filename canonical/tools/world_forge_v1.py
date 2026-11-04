#!/usr/bin/env python3
"""Build the world a capability needs, by reading what it says when the world is wrong.

The finding this file acts on
-----------------------------
Log 12 measured a world of 462 mechanical instances and got **zero** usable structure out of it.
The reason was in the verdict list, not in the model: 270 of 462 worlds ended in CRASHED, and 127
of those were `FileNotFoundError` on a path my fixture invented, 23 were a JSON file I wrote as
garbage on purpose. Most of that world was measuring my own fixture, not the capability. A world
that is mostly noise about the person who built it cannot teach anything.

But 29 of those crashes were the adapter **naming the world it wanted**:

    RuntimeError: SACCR_INPUT_SHAPE_REJECTED:need {"trades": [non-empty]}
    ValueError:    RELEVANCE_INPUT_NOT_JSON:JSONDecodeError
    FileNotFoundError: [Errno 2] No such file or directory: '<path it actually wanted>'

That is a specification, written in the failure. So the world does not have to be guessed and it
does not have to be enumerated by a person: start with the smallest world, run, read the refusal,
change one thing, run again. The gap between "this capability cannot be driven" and "this
capability reached a verdict" is closed by the capability itself.

The operators are generic on purpose
------------------------------------
`_operators` keys on exception classes and on the shape of the message, never on a capability id.
A repair that knows the capability's name is a person's work wearing a machine's clothes, and it
would not transfer to the next 63 capabilities.

What is not repairable, and is reported as such
-----------------------------------------------
`ModuleNotFoundError` for a package this machine does not have (PIL, sympy, pypdf) cannot be fixed
without installing something, and installing something is spending, which this repository forbids
in a credited path. Those are counted as unreachable, with the package named, and they are the
majority of what remains.

Usage::

    python -m canonical.tools.world_forge_v1              # measure
    python -m canonical.tools.world_forge_v1 --write      # write the artifact
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools.capability_world_v1 import (                      # noqa: E402
    ADAPTERS, declared_inputs, reaches_unsafe, registry)

SCHEMA = "PROJECT_BRAIN_WORLD_FORGE_V1"
ARTIFACT = ROOT / "canonical/verification/WORLD_FORGE_V1.json"
TIMEOUT_S = 25
SENTINEL = "@@FORGE@@ "
MAX_ROUNDS = 6
DECLARED = ("CLAIM_CHECKED", "CLAIM_FALSE", "CLAIM_FIELD_ABSENT", "REFUSED_NAMED")
# A refusal is a good outcome for a capability and a dead end for a claim about what it returns.
# The two goals are different and are measured separately: "it spoke" versus "it did the thing".
OUTPUT = ("CLAIM_CHECKED", "CLAIM_FALSE", "CLAIM_FIELD_ABSENT")

A_REAL_MODULE = ('def add(a, b):\n    """Add two numbers."""\n    return a + b\n\n\n'
                 'def main():\n    return add(1, 2)\n')


# --------------------------------------------------------------------------- the recipe
def blank_recipe(entry: dict) -> dict:
    """The smallest world that can be built from the declaration alone."""
    values, files = {}, {}
    for key, name in declared_inputs(entry):
        if name.endswith("_root") or name in ("worktree_path", "source_root"):
            values[key] = "@ROOT@"
        elif name.endswith("_s") or name == "timeout":
            values[key] = "5"
        elif "json" in name:
            rel = name if name.endswith(".json") else f"{name}.json"
            values[key] = rel
            files[rel] = '{"records": [], "items": []}\n'
        elif "path" in name:
            rel = f"{name}.txt"
            values[key] = rel
            files[rel] = "x\n"
        elif name == "goal":
            values[key] = "bundle the files in the repository"
        else:
            values[key] = "x"
    return {"values": values, "files": files, "dirs": [], "db": [], "rounds": []}


def _value_for(key: str, recipe: dict, root: Path) -> Any:
    value = recipe["values"].get(key)
    if value == "@ROOT@":
        return str(root)
    return value


# --------------------------------------------------------------------------- the worker
def _worker(capability_id: str, module: str, out_dir: str, recipe_json: str,
            module_root: str | None = None) -> int:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    recipe = json.loads(recipe_json)
    entry = registry()[capability_id]
    for rel in recipe.get("dirs") or []:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel, content in (recipe.get("files") or {}).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for rel in recipe.get("db") or []:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, value TEXT)")
        connection.commit()
        connection.close()

    args = {key: _value_for(key, recipe, root) for key, _ in declared_inputs(entry)}
    result: dict[str, Any] = {"capability": capability_id}
    try:
        import importlib.util
        # Import from the world being driven, when one was named. An adapter resolves its own
        # paths from __file__, so importing it from the repository while handing it a temporary
        # root means it edits the repository and reports success about a directory nobody
        # looked at. Measured 2026-11-04 on the copy-sandbox for subprocess capabilities.
        base = Path(module_root) if module_root else ROOT
        path = base / "canonical/runtime/bound_capabilities" / f"{module}.py"
        spec = importlib.util.spec_from_file_location(f"_forge_{module}", path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        try:
            returned = loaded.run(args, root)
        except SystemExit as exc:
            # An adapter that prints its refusal and exits is refusing, not crashing my harness.
            # Measured 2026-11-04: SystemExit killed the worker before it could report, and six
            # capabilities were recorded as NO_OUTPUT -- the harness's problem described as the
            # capability's silence.
            result.update(verdict="REFUSED_NAMED",
                          detail=f"REFUSAL_EXIT:{exc.code if exc.code is not None else 0}")
            print(SENTINEL + json.dumps(result))
            return 0
        if not isinstance(returned, dict):
            result.update(verdict="NON_DICT", detail=type(returned).__name__,
                          returned_keys=[])
        else:
            result["returned_keys"] = sorted(str(k) for k in returned)
            expect = (entry.get("action_template") or {}).get("expect") or {}
            field, want = expect.get("field"), expect.get("value")
            if field and field in returned:
                result.update(verdict="CLAIM_CHECKED" if returned[field] == want else "CLAIM_FALSE",
                              detail=f"{field}={returned[field]!r} want {want!r}")
            else:
                result.update(verdict="CLAIM_FIELD_ABSENT",
                              detail=f"no {field!r}; keys={sorted(returned)[:6]}")
    except Exception as exc:                                        # noqa: BLE001
        message = str(exc)
        named = bool(message) and bool(re.fullmatch(r"[A-Z0-9_:. \-]+", message))
        result.update(verdict="REFUSED_NAMED" if named else "CRASHED",
                      detail=f"{type(exc).__name__}: {message[:200]}")
    # Prefixed, because an adapter is free to print JSON and even to exit early. Measured
    # 2026-11-04: one adapter printed {"error": ...} and called sys.exit(), so the last line of
    # stdout was the ADAPTER's json and the forge read it as its own verdict. A result that
    # cannot be told apart from the world's chatter is not a result.
    print(SENTINEL + json.dumps(result))
    return 0


def run_once(capability_id: str, module: str, recipe: dict,
             world: Path | None = None) -> dict:
    directory = str(world) if world is not None else tempfile.mkdtemp(prefix="forge_")
    world_root = Path(directory)
    cleanup = world is None
    module_root = str(world_root) if world is not None else None
    try:
        command = [sys.executable, str(Path(__file__).resolve()), "--worker",
                   capability_id, module, directory, json.dumps(recipe)]
        if module_root:
            command.append(module_root)
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=TIMEOUT_S,
            cwd=module_root or str(ROOT))
        lines = [l for l in (done.stdout or "").splitlines() if l.startswith(SENTINEL)]
        if not lines:
            return {"capability": capability_id, "verdict": "NO_OUTPUT",
                    "detail": (done.stderr or done.stdout or "")[-200:], "root": str(world_root)}
        parsed = json.loads(lines[-1][len(SENTINEL):])
        if str(parsed.get("detail") or "").startswith("REFUSAL_EXIT"):
            # The adapter said why, on stderr, before exiting. That reason is the world
            # specification; dropping it leaves the forge reading its own placeholder.
            import re as _re
            for haystack in (str(parsed.get("detail") or ""), done.stderr or ""):
                match = _re.search(r'"reason"\s*:\s*"([^"]{0,120})"', haystack)
                if match:
                    parsed["detail"] = f"RuntimeError: {match.group(1)}"
                    break
        parsed["root"] = str(world_root)
        return parsed
    except subprocess.TimeoutExpired:
        return {"capability": capability_id, "verdict": "TIMEOUT", "detail": f"{TIMEOUT_S}s",
                "root": str(world_root)}
    finally:
        if cleanup:
            shutil.rmtree(directory, ignore_errors=True)


# --------------------------------------------------------------------------- repair
def _primary_json(recipe: dict) -> str | None:
    for rel in recipe["files"]:
        if rel.endswith(".json"):
            return rel
    return None


def _json_spec_from(message: str) -> Any:
    """The world an adapter asked for, if it wrote one down.

    `SACCR_INPUT_SHAPE_REJECTED:need {"trades": [non-empty]}` and friends. Anything after
    `need` that parses as JSON is a specification, not prose."""
    for marker in ("need ", "requires ", "expected "):
        if marker in message:
            tail = message.split(marker, 1)[1].strip()
            for candidate in (tail, tail[tail.find("{"):tail.rfind("}") + 1] if "{" in tail else ""):
                if not candidate:
                    continue
                # `[non-empty]` is a statement about the shape, not JSON. Read it as one.
                relaxed = candidate.replace("[non-empty]", '["x"]').replace("[non_empty]", '["x"]')
                relaxed = re.sub(r"\[([A-Za-z_][A-Za-z0-9_ -]*)\]", '["x"]', relaxed)
                try:
                    return json.loads(relaxed)
                except ValueError:
                    continue
    return None


def _fill(template: Any) -> Any:
    """Turn a stated shape into a concrete value: non-empty means one element, not zero."""
    if isinstance(template, dict):
        return {k: _fill(v) for k, v in template.items()}
    if isinstance(template, list):
        return [_fill(item) for item in template[:1]] if template else ["x"]
    if isinstance(template, str):
        return "x"
    return template


def operators(capability_id: str, module: str, recipe: dict, failure: dict,
              root: Path | None = None) -> tuple[dict, str]:
    """One repair, chosen from the failure. Returns (new recipe, operator name).

    No branch here knows a capability's name. Each one keys on an exception class or on a shape
    the adapter itself declared.
    """
    detail = failure.get("detail") or ""
    kind = detail.split(":", 1)[0].strip()
    message = detail.split(":", 1)[1].strip() if ":" in detail else detail
    new = json.loads(json.dumps(recipe))

    if kind == "ModuleNotFoundError":
        return new, "UNREPAIRABLE_MISSING_PACKAGE"

    if kind == "FileNotFoundError":
        match = re.search(r"'([^']+)'", message)
        if not match:
            return new, "UNREPAIRABLE_UNPARSED"
        wanted = match.group(1)
        # Relative to the WORLD root first. Measured 2026-11-04: resolving only against the
        # repository marked a path inside the temporary world as unreachable, so a repair was
        # refused for the one reason it could not be.
        relative = None
        for base in ([root] if root else []) + [ROOT]:
            try:
                relative = str(Path(wanted).resolve().relative_to(Path(base).resolve()))
                break
            except (ValueError, OSError):
                continue
        if relative is None or relative.startswith(".."):
            # The adapter looked somewhere the world does not exist. That is a capability
            # ignoring the root it was handed, which is a finding, not a fixture problem.
            return new, "UNREPAIRABLE_ADAPTER_ESCAPES_ROOT"
        # a path the adapter wants to READ must exist; a path it wants to WRITE must not
        if Path(wanted).suffix in (".db", ".sqlite", ".sqlite3"):
            if relative not in new["db"]:
                new["db"].append(relative)
            return new, "CREATE_DATABASE"
        if Path(wanted).suffix:
            new["files"][relative] = new["files"].get(relative, "x\n")
            return new, "CREATE_FILE"
        new["dirs"].append(relative)
        return new, "CREATE_DIRECTORY"

    if "JSON" in detail.upper() and ("DECODE" in detail.upper() or "NOT_JSON" in detail.upper()
                                     or "NOT_VALID_JSON" in detail.upper()):
        # The capability read a file as JSON. It does not matter which one: make the world JSON.
        if not new["files"]:
            return new, "UNREPAIRABLE_NO_FILE_INPUT"
        for rel in list(new["files"]):
            if rel.endswith((".json", ".txt", "")):
                new["files"][rel] = "{}"
        return new, "MAKE_THE_WORLD_JSON"

    if "PATH_INVALID" in detail.upper() or "TEST_PATH_INVALID" in detail.upper():
        # It wants a python file at a path that exists. Give it the smallest one that parses.
        for rel in list(new["files"]):
            if rel.endswith(".txt"):
                new["files"][rel] = "def test_nothing():\n    assert True\n"
        return new, "WRITE_A_PARSEABLE_PYTHON_FILE"

    spec = _json_spec_from(detail)
    if spec is not None:
        target = _primary_json(new)
        if target is None:
            return new, "UNREPAIRABLE_NO_JSON_INPUT"
        new["files"][target] = json.dumps(_fill(spec))
        return new, "BUILD_THE_SHAPE_IT_NAMED"

    if kind == "KeyError":
        match = re.search(r"'([^']+)'", message)
        target = _primary_json(new)
        if match and target:
            try:
                current = json.loads(new["files"][target])
            except ValueError:
                current = {}
            if isinstance(current, dict):
                current[match.group(1)] = "x"
                new["files"][target] = json.dumps(current)
                return new, "ADD_THE_KEY_IT_ASKED_FOR"

    if "_MUST_BE_PY" in detail.upper():
        # A named argument must point at Python. Find the argument whose name shares the token,
        # give it a .py path, and put a parseable module there.
        word = re.sub(r"_MUST_BE_PY$", "", detail.split(":")[-1].strip().upper()).lower()
        for key in list(new["values"]):
            if word and word in str(key).lower():
                value = f"{word}.py"
                new["values"][key] = value
                new["files"][value] = A_REAL_MODULE
                return new, "MAKE_THE_ARGUMENT_PYTHON"
        new["values"]["module"] = "module.py"
        new["files"]["module.py"] = A_REAL_MODULE
        return new, "MAKE_THE_ARGUMENT_PYTHON"

    if detail.upper().endswith("_NOT_DIRECTORY") or detail.upper().endswith("_NOT_A_DIRECTORY"):
        word = re.sub(r"_NOT_A?_?DIRECTORY$", "", detail.split(":")[-1].strip().upper()).lower()
        for key in list(new["values"]):
            if word and word in str(key).lower():
                value = f"{word}_dir"
                new["values"][key] = value
                new["dirs"].append(value)
                return new, "MAKE_THE_ARGUMENT_A_DIRECTORY"
        return new, "UNREPAIRABLE_NOT_UNDERSTOOD"

    if "PATH_MISSING" in detail.upper() or "NOT_A_FILE" in detail.upper():
        match = re.search(r":([^:\s]+)$", detail)
        if not match:
            return new, "UNREPAIRABLE_NOT_UNDERSTOOD"
        wanted = match.group(1).strip()
        if wanted in (".", "", "/"):
            return new, "UNREPAIRABLE_NOT_UNDERSTOOD"
        if "." in wanted.split("/")[-1]:
            new["files"][wanted] = (A_REAL_MODULE if wanted.endswith(".py") else "x\n")
            return new, "CREATE_THE_FILE_IT_NAMED"
        new["dirs"].append(wanted)
        return new, "CREATE_THE_DIRECTORY_IT_NAMED"

    if "OUTPUT_ALREADY_EXISTS" in detail.upper():
        # It refuses rather than overwriting, which is correct behaviour. Give it a world with
        # the output absent. Nothing is deleted from the real repository: `new` describes a
        # temporary world and only names files inside it.
        for key, value in list(new["values"].items()):
            if "output" in str(key) and isinstance(value, str) and value != "@ROOT@":
                new["files"].pop(value, None)
                new["db"] = [d for d in new["db"] if d != value]
        return new, "CLEAR_THE_OUTPUT"

    if detail.upper().endswith(("_EMPTY", "_EMPTY_PATH")) or "NO_SUPPORTED_SOURCE_FILES" in detail.upper():
        # "There is nothing here to work on." The world needs code in it, not an empty file.
        if not new["files"]:
            return new, "UNREPAIRABLE_NO_FILE_INPUT"
        for rel in list(new["files"]):
            if rel.endswith(".py"):
                new["files"][rel] = A_REAL_MODULE
        if not any(rel.endswith(".py") for rel in new["files"]):
            new["files"]["module.py"] = A_REAL_MODULE
        return new, "PUT_CODE_IN_THE_WORLD"

    if detail.upper().endswith("_MISSING") or detail.upper().endswith("_NOT_FOUND"):
        token = re.sub(r"[^A-Za-z0-9]+", "_", detail.split(":")[-1].strip()).strip("_").lower()
        token = re.sub(r"_(missing|not_found|required)$", "", token)
        if not token:
            return new, "UNREPAIRABLE_NOT_UNDERSTOOD"
        new["files"][f"{token}.json"] = "{}"
        return new, "CREATE_THE_NAMED_SIDECAR"

    if detail.upper().endswith("_REQUIRED"):
        # "This input is required and what you gave me is not it." The token names the thing;
        # find the declared input that names it too, and fill it with a document containing it.
        token = detail.split(":")[-1].strip()
        word = re.sub(r"_(INPUT_)?REQUIRED$", "", token).lower()
        for key in list(new["values"]):
            if word and word in str(key).lower():
                current = new["values"][key]
                if isinstance(current, str) and current.endswith(".json"):
                    new["files"][current] = json.dumps({word: ["x"]})
                    return new, "FILL_THE_REQUIRED_INPUT"
                if isinstance(current, str) and current.endswith((".txt", ".py")):
                    new["files"][current] = (A_REAL_MODULE if current.endswith(".py")
                                             else f"{word}\n")
                    return new, "FILL_THE_REQUIRED_INPUT"
                new["values"][key] = [word]
                return new, "FILL_THE_REQUIRED_INPUT"
        return new, "UNREPAIRABLE_NOT_UNDERSTOOD"

    if detail.upper().endswith("_INVALID") or detail.upper().endswith("_REJECTED")             or detail.upper().endswith("_UNRESOLVED"):
        # Something it read is the wrong shape. Prefer the file whose name matches the token.
        token = re.sub(r"[^a-z0-9]+", "", detail.split(":")[-1].upper().split("_")[0].lower()) \
            if False else detail.split(":")[-1].strip().split("_")[0].lower()
        for rel in list(new["files"]):
            if token and token in rel.lower():
                new["files"][rel] = A_REAL_MODULE if rel.endswith(".py") else "{}"
                return new, "RESHAPE_THE_THING_IT_REJECTED"
        for rel in list(new["files"]):
            new["files"][rel] = A_REAL_MODULE if rel.endswith(".py") else "{}"
        return new, "RESHAPE_ALL_INPUTS"

    if kind == "DatabaseError":
        # It opened something as a database and it was not one. If the declaration names a
        # database file, use it; otherwise make the first file it was given a real database.
        # Measured 2026-11-04: without the fallback this said "not understood" for a world in
        # which every input was plainly a path.
        candidates = [v for v in new["values"].values() if isinstance(v, str)]
        rel = next((v for v in candidates if v.endswith((".db", ".sqlite", ".sqlite3"))), None)
        rel = rel or next((v for v in candidates if v not in ("@ROOT@", "5")), None)
        if rel:
            new["files"].pop(rel, None)
            if rel not in new["db"]:
                new["db"].append(rel)
            return new, "CREATE_DATABASE"

    return new, "UNREPAIRABLE_NOT_UNDERSTOOD"


def forge(capability_id: str, module: str, goal: str = "DECLARED",
          world: Path | None = None) -> dict:
    """Run, read the refusal, repair, repeat -- until it reaches a verdict or stops changing."""
    recipe = blank_recipe(registry()[capability_id])
    trail: list[dict] = []
    seen: set[str] = set()
    for round_no in range(MAX_ROUNDS):
        outcome = run_once(capability_id, module, recipe, world)
        trail.append({"round": round_no, "verdict": outcome["verdict"],
                      "detail": (outcome.get("detail") or "")[:160]})
        wanted = OUTPUT if goal == "OUTPUT" else DECLARED
        if outcome["verdict"] in wanted:
            return {"capability": capability_id, "reached": True, "verdict": outcome["verdict"],
                    "rounds": round_no, "trail": trail, "goal": goal,
                    "returned_keys": outcome.get("returned_keys") or []}
        recipe, op = operators(capability_id, module, recipe, outcome, outcome.get("root"))
        trail[-1]["operator"] = op
        if op.startswith("UNREPAIRABLE"):
            return {"capability": capability_id, "reached": False, "verdict": outcome["verdict"],
                    "rounds": round_no, "stopped_by": op, "trail": trail}
        signature = json.dumps({k: recipe[k] for k in ("files", "dirs", "db")}, sort_keys=True)
        if signature in seen:
            return {"capability": capability_id, "reached": False, "verdict": outcome["verdict"],
                    "rounds": round_no, "stopped_by": "LOOP_NO_PROGRESS", "trail": trail}
        seen.add(signature)
    last = trail[-1]
    return {"capability": capability_id, "reached": False, "verdict": last["verdict"],
            "rounds": MAX_ROUNDS, "stopped_by": "ROUNDS_EXHAUSTED", "trail": trail,
            "goal": goal}


# --------------------------------------------------------------------------- measurement
def measure(write: bool = False) -> dict:
    caps = registry()
    before_doc = json.loads((ROOT / "canonical/verification/CAPABILITY_WORLD_V1.json")
                            .read_text(encoding="utf-8"))
    before = {}
    for row in before_doc["rows"]:
        if row.get("variant") == "MINIMAL":
            before[row["capability"]] = row["verdict"]

    attempted = []
    for capability_id, entry in sorted(caps.items()):
        module = entry.get("adapter_module") or ""
        path = ADAPTERS / f"{module}.py"
        if not path.is_file():
            continue
        # Measured 2026-11-04: nineteen capabilities were never attempted because they declare
        # no inputs. Nothing is missing from a world that supplies nothing -- they can be run
        # with an empty argument set, and 98 declared claims were going unsettled for free.
        if reaches_unsafe(path.read_text(encoding="utf-8")):
            continue
        attempted.append((capability_id, module))

    results = [forge(capability_id, module) for capability_id, module in attempted]
    was_declared = sum(1 for r in results if before.get(r["capability"]) in DECLARED)
    now_declared = sum(1 for r in results if r["reached"])
    gained = [r for r in results if r["reached"] and before.get(r["capability"]) not in DECLARED]

    operators_used: dict[str, int] = {}
    for r in results:
        for step in r.get("trail") or []:
            op = step.get("operator")
            if op:
                operators_used[op] = operators_used.get(op, 0) + 1

    stopped: dict[str, int] = {}
    for r in results:
        if not r["reached"]:
            stopped[r.get("stopped_by") or "unknown"] = stopped.get(r.get("stopped_by") or "unknown", 0) + 1

    doc = {
        "schema": SCHEMA,
        "question": "Can the system build a world a capability can actually run in, by reading "
                    "what the capability says when the world is wrong?",
        "attempted": len(results),
        "before": {
            "reached_a_declared_verdict": was_declared,
            "crashing_or_silent": len(results) - was_declared,
        },
        "after": {
            "reached_a_declared_verdict": now_declared,
            "crashing_or_silent": len(results) - now_declared,
        },
        "gained": len(gained),
        "gained_capabilities": sorted(r["capability"] for r in gained),
        "rounds_to_verdict": sorted(r["rounds"] for r in results if r["reached"]),
        "operators": operators_used,
        "stopped_by": stopped,
        "unreachable": sorted(
            {r["trail"][-1]["detail"].split("'")[1] for r in results
             if (r.get("stopped_by") == "UNREPAIRABLE_MISSING_PACKAGE"
                 and "'" in (r["trail"][-1].get("detail") or ""))}),
        "rows": results,
        "non_claims": [
            "BUILDING_A_RUNNABLE_WORLD_IS_NOT_BUILDING_A_MEANINGFUL_ONE",
            "A_REFUSAL_NAMED_IS_A_GOOD_OUTCOME_NOT_A_FIXED_CAPABILITY",
            "OPERATORS_ARE_GENERIC_NO_BRANCH_KNOWS_A_CAPABILITY_NAME",
            "MISSING_PACKAGES_ARE_UNREPAIRABLE_WITHOUT_SPEND",
        ],
        "authority": "NO_CAPABILITY_CREDIT_WORLD_CONSTRUCTION_MEASUREMENT_ONLY",
    }
    if write:
        ARTIFACT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs="+", metavar="ARG",
                    help="CAPABILITY MODULE DIR RECIPE [MODULE_ROOT]")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.worker:
        return _worker(*args.worker)
    doc = measure(write=args.write)
    print(f"attempted {doc['attempted']} capabilities that declare inputs and can be sandboxed")
    print(f"  before: {doc['before']['reached_a_declared_verdict']} reached a declared verdict")
    print(f"  after:  {doc['after']['reached_a_declared_verdict']} reached a declared verdict")
    print(f"  gained: {doc['gained']}  {doc['gained_capabilities'][:6]}")
    print(f"  operators used: {doc['operators']}")
    print(f"  stopped by: {doc['stopped_by']}")
    print(f"  missing packages: {doc['unreachable']}")
    if args.write:
        print(f"  wrote {ARTIFACT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
