"""Independent stdlib oracles for bounded coupled Python comparison repair.

No runtime repair module or adapter is imported here.  The oracle independently
reconstructs the declarative source, applies the emitted unified diffs, and
executes the candidate functions in a fresh namespace.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Mapping

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _text(instance: Mapping[str, Any], key: str) -> str:
    value = instance.get(key)
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("invalid identifier: " + key)
    return value


def _integer(instance: Mapping[str, Any], key: str) -> int:
    value = instance.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid integer: " + key)
    return value


def _left_source(instance: Mapping[str, Any]) -> str:
    return (
        f"def {_text(instance, 'left_function')}(value):\n"
        f"    return value < {_integer(instance, 'left_threshold')}\n"
    )


def _right_source(instance: Mapping[str, Any]) -> str:
    return (
        f"def {_text(instance, 'right_function')}(value):\n"
        f"    return value > {_integer(instance, 'right_threshold')}\n"
    )


def _apply_unified_diff(original: str, patch: str) -> str:
    """Apply a strict, stdlib-only unified diff without trusting the solver.

    The implementation validates every context/removal line and rejects malformed
    or path-changing patches.  It is intentionally independent of the repair
    kernel's patch construction.
    """
    if not isinstance(patch, str) or not patch.startswith("--- a/") or "\n+++ b/" not in patch:
        raise ValueError("invalid unified diff header")
    lines = patch.splitlines(keepends=True)
    original_lines = original.splitlines(keepends=True)
    emitted: list[str] = []
    source_index = 0
    line_index = 0
    saw_hunk = False
    while line_index < len(lines):
        line = lines[line_index]
        if line.startswith("--- ") or line.startswith("+++ "):
            line_index += 1
            continue
        match = _HUNK.match(line.rstrip("\n"))
        if match is None:
            if line.startswith("\\ No newline at end of file"):
                line_index += 1
                continue
            raise ValueError("missing hunk header")
        saw_hunk = True
        old_start = int(match.group(1))
        expected_index = max(0, old_start - 1)
        if expected_index < source_index or expected_index > len(original_lines):
            raise ValueError("invalid hunk offset")
        emitted.extend(original_lines[source_index:expected_index])
        source_index = expected_index
        line_index += 1
        while line_index < len(lines) and not lines[line_index].startswith("@@ "):
            row = lines[line_index]
            if row.startswith("\\ No newline at end of file"):
                line_index += 1
                continue
            if not row or row[0] not in {" ", "+", "-"}:
                raise ValueError("invalid hunk row")
            payload = row[1:]
            if row[0] == " ":
                if source_index >= len(original_lines) or original_lines[source_index] != payload:
                    raise ValueError("context mismatch")
                emitted.append(payload)
                source_index += 1
            elif row[0] == "-":
                if source_index >= len(original_lines) or original_lines[source_index] != payload:
                    raise ValueError("removal mismatch")
                source_index += 1
            else:
                emitted.append(payload)
            line_index += 1
    if not saw_hunk:
        raise ValueError("no hunk")
    emitted.extend(original_lines[source_index:])
    return "".join(emitted)


def _candidate_sources(instance: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, str]:
    left_module = _text(instance, "left_module")
    right_module = _text(instance, "right_module")
    originals = {
        left_module + ".py": _left_source(instance),
        right_module + ".py": _right_source(instance),
    }
    patches = output.get("patches")
    if not isinstance(patches, list) or len(patches) != 2:
        raise ValueError("expected exactly two patches")
    result = dict(originals)
    touched: set[str] = set()
    for row in patches:
        if not isinstance(row, Mapping):
            raise ValueError("patch not object")
        path = row.get("source_path")
        if not isinstance(path, str) or path not in originals or path in touched:
            raise ValueError("unexpected patch path")
        patch = row.get("unified_diff")
        candidate = _apply_unified_diff(originals[path], patch)
        if candidate == originals[path]:
            raise ValueError("patch leaves source unchanged")
        if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(ast.parse(candidate))):
            raise ValueError("candidate imports are outside this capability scope")
        result[path] = candidate
        touched.add(path)
    if touched != set(originals):
        raise ValueError("not every source was patched")
    return result


def _functions(instance: Mapping[str, Any], output: Mapping[str, Any]):
    sources = _candidate_sources(instance, output)
    namespaces: dict[str, dict[str, Any]] = {}
    for path, source in sources.items():
        namespace: dict[str, Any] = {"__builtins__": {}}
        exec(compile(source, path, "exec"), namespace, namespace)
        namespaces[path] = namespace
    left = namespaces[_text(instance, "left_module") + ".py"][_text(instance, "left_function")]
    right = namespaces[_text(instance, "right_module") + ".py"][_text(instance, "right_function")]
    if not callable(left) or not callable(right):
        raise ValueError("candidate functions missing")
    return left, right


def _envelope(output: Mapping[str, Any]) -> tuple[bool, str]:
    if output.get("pass") is not True:
        return False, "solver did not report a verified candidate"
    if output.get("route") != "COUPLED_PAIR":
        return False, "repair did not use coupled-pair route"
    if output.get("crossed_nonmonotonic_valley") is not True:
        return False, "repair did not establish nonmonotonic crossing"
    if output.get("source_restored") is not True:
        return False, "candidate search did not restore source"
    if output.get("model_dependency_count") != 0:
        return False, "model dependency reported"
    if output.get("external_capability_provider_count") != 0:
        return False, "external capability provider reported"
    if output.get("incremental_spend_usd") != 0:
        return False, "nonzero spend reported"
    if output.get("single_candidates_tested") != 2 or output.get("pair_candidates_tested") != 1:
        return False, "bounded search evidence differs"
    replays = output.get("verification_replays")
    if not isinstance(replays, list) or len(replays) != 2:
        return False, "two successful verification replays required"
    if any(not isinstance(row, Mapping) or row.get("returncode") != 0 or row.get("timed_out") is not False for row in replays):
        return False, "verification replay failed"
    return True, "candidate envelope is bounded, restored, and model-free"


def oracles():
    def analytic_closed_form(instance: Mapping[str, Any], output: Mapping[str, Any], solve: Any):
        ok, detail = _envelope(output)
        if not ok:
            return False, detail
        try:
            left, right = _functions(instance, output)
            left_threshold = _integer(instance, "left_threshold")
            right_threshold = _integer(instance, "right_threshold")
            for value in range(left_threshold - 8, left_threshold + 9):
                got = left(value)
                expected = value <= left_threshold
                if type(got) is not bool or got != expected:
                    return False, f"left({value})={got!r}, expected {expected}"
            for value in range(right_threshold - 8, right_threshold + 9):
                got = right(value)
                expected = value >= right_threshold
                if type(got) is not bool or got != expected:
                    return False, f"right({value})={got!r}, expected {expected}"
        except Exception as exc:
            return False, "candidate reconstruction failed: " + repr(exc)
        return True, "both repaired boundary predicates match independent closed forms"

    def boundary_metamorphic(instance: Mapping[str, Any], output: Mapping[str, Any], solve: Any):
        try:
            left, right = _functions(instance, output)
            left_threshold = _integer(instance, "left_threshold")
            right_threshold = _integer(instance, "right_threshold")
            # Membership in (-infinity, threshold] is downward closed; membership
            # in [threshold, infinity) is upward closed.  These relations are
            # independent of the adapter's search and of the closed-form oracle.
            for value in range(left_threshold - 10, left_threshold + 11):
                if left(value) and not left(value - 1):
                    return False, f"left downward closure violated at {value}"
                if not left(value) and left(value + 1):
                    return False, f"left complement upward closure violated at {value}"
            for value in range(right_threshold - 10, right_threshold + 11):
                if right(value) and not right(value + 1):
                    return False, f"right upward closure violated at {value}"
                if not right(value) and right(value - 1):
                    return False, f"right complement downward closure violated at {value}"
        except Exception as exc:
            return False, "candidate reconstruction failed: " + repr(exc)
        return True, "both repaired predicates satisfy their boundary monotonicity relations"

    def patch_and_provenance_properties(instance: Mapping[str, Any], output: Mapping[str, Any], solve: Any):
        ok, detail = _envelope(output)
        if not ok:
            return False, detail
        try:
            sources = _candidate_sources(instance, output)
        except Exception as exc:
            return False, "patch property failed: " + repr(exc)
        comparisons = []
        for source in sources.values():
            tree = ast.parse(source)
            comparisons.extend(node for node in ast.walk(tree) if isinstance(node, ast.Compare))
        if len(comparisons) != 2 or any(len(node.ops) != 1 for node in comparisons):
            return False, "candidate does not preserve one simple comparison per source"
        return True, "two independently applicable patches preserve the declared two-file shape"

    return [
        {"id": "ANALYTIC_CLOSED_FORM", "check": analytic_closed_form},
        {"id": "BOUNDARY_METAMORPHIC", "check": boundary_metamorphic},
        {"id": "PATCH_AND_PROVENANCE_PROPERTIES", "check": patch_and_provenance_properties},
    ]
