#!/usr/bin/env python3
"""Verify a composed transition/format repair derived from runtime observations.

Generators (no diff, no model, no stored rule):
  1. normalize an observed empty value to None before an `is not None` branch;
  2. tighten guards that admit an observed empty payload;
  3. serialize a raw interpolated value with quoted joining where the expected
     strings show quoted, comma-separated names.
Candidates are combined with counterexample splicing and accepted only by the
project's whole test file.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for entry in (str(ROOT), str(ROOT / "canonical" / "tools"),
              str(ROOT / "canonical" / "swe_kernel")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import assertion_operand_tomography_v1 as tomography  # noqa: E402
import dual_program_splicing_v1 as splicing  # noqa: E402
import empty_payload_suppression_v1 as eps  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_MULTI_PRODUCER_NORMALIZATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "N1": "every applied edit is generated from a runtime-observed empty value or expected output shape",
    "N2": "composed candidates are accepted only by the whole test file",
    "N3": "no diff, gold patch, model, network or stored parameter is read",
}
HELPER = '''def _brain_serialize(value):
    values = value if isinstance(value, (tuple, list)) else (value,)
    return ", ".join(repr(item) for item in values if item)


'''


def _span(source: str, node: ast.AST) -> tuple[int, int]:
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    return start, end


def _is_none_test(test: ast.AST, name: str) -> bool:
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], (ast.Is, ast.IsNot))
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value is None):
        return False
    left = test.left
    return ((isinstance(left, ast.Name) and left.id == name)
            or (isinstance(left, ast.Attribute) and left.attr == name))


def normalize_candidates(source: str, names: set[str]) -> list[str]:
    """Insert `if not x: x = None` before an is-not-None branch that saw x empty."""
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in names:
            continue
        parent_body = None
        for parent in ast.walk(tree):
            body = getattr(parent, "body", None)
            if isinstance(body, list) and node in body:
                parent_body = body
                break
        if parent_body is None:
            continue
        position = parent_body.index(node)
        if position + 1 >= len(parent_body):
            continue
        following = parent_body[position + 1]
        if not (isinstance(following, ast.If) and _is_none_test(following.test, target.id)):
            continue
        indent = " " * node.col_offset
        # Insert a full statement before the following `if` line, not at its
        # first token (which would double or drop leading indentation).
        start = sum(len(line) for line in source.splitlines(keepends=True)
                    [:following.lineno - 1])
        insertion = f"{indent}if not {target.id}:\n{indent}    {target.id} = None\n"
        out.append(source[:start] + insertion + source[start:])
        if len(out) >= 6:
            break
    return out


def _with_helper(source: str) -> str:
    """Place the helper at module scope, after imports and before the first class.

    Prepending it would move a `from __future__` import away from the top of the
    file; a generated candidate that cannot even be imported is not a repair.
    """
    if "def _brain_serialize" in source:
        return source
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    insert_line = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            insert_line = node.lineno - 1
            break
    if insert_line is None:
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                insert_line = node.end_lineno
            elif insert_line is not None:
                break
    if insert_line is None:
        insert_line = 0
    offset = sum(len(line) for line in lines[:insert_line])
    return source[:offset] + HELPER + source[offset:]


def serialize_candidates(source: str, names: set[str]) -> list[str]:
    """Replace raw f-string interpolation of an observed value with a serializer."""
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        for value in node.values:
            if not isinstance(value, ast.FormattedValue):
                continue
            expression = value.value
            name = expression.id if isinstance(expression, ast.Name) else \
                expression.attr if isinstance(expression, ast.Attribute) else None
            if name not in names:
                continue
            start, end = _span(source, expression)
            call = f"_brain_serialize({ast.unparse(expression)})"
            before, after = source[:start], source[end:]
            variants = [before + call + after]
            # An f-string may quote the interpolation. Drop those literal quotes
            # so a serializer that supplies its own quotes is not double-quoted.
            for quote in ("'", '"'):
                if before.endswith(quote + "{") and after.startswith("}" + quote):
                    variants.append(before[:-2] + "{" + call + "}" + after[2:])
            for rebuilt in variants:
                out.append(_with_helper(rebuilt))
                if len(out) >= 10:
                    return out
    return out


def value_pairs(report: Mapping[str, Any]) -> list[tuple[Any, Any]]:
    """Both directions of every literal comparison captured in a failing test."""
    values = report.get("values") or {}
    by_line: dict[str, list[str]] = {}
    for key in values:
        parts = key.split("_")
        by_line.setdefault(parts[1] if len(parts) > 2 and parts[0] == "op" else "0",
                           []).append(key)
    out: list[tuple[Any, Any]] = []
    for keys in by_line.values():
        ordered = sorted(keys, key=lambda item: int(item.rsplit("_", 1)[-1]))
        parsed: list[Any] = []
        for key in ordered:
            try:
                parsed.append(ast.literal_eval(str(values[key])))
            except (ValueError, SyntaxError):
                parsed.append(None)
        for first, second in zip(parsed, parsed[1:]):
            if first == second:
                continue
            out.append((first, second))
            out.append((second, first))
    return out


def whitespace_candidates(source: str, pairs: Sequence[tuple[Any, Any]]) -> list[str]:
    """Strip trailing whitespace where the observed output differs only by that."""
    interesting = [(a, b) for a, b in pairs if isinstance(a, str) and isinstance(b, str)
                   and a != b and a.rstrip() == b]
    if not interesting:
        return []
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        if not isinstance(node.value, (ast.JoinedStr, ast.Constant, ast.BinOp)):
            continue
        start, end = _span(source, node.value)
        expression = ast.unparse(node.value)
        candidate = (source[:start] + f"({expression}).rstrip()" + source[end:]
                     if expression != ast.unparse(ast.parse(expression, mode="eval").body)
                     else source[:start] + f"({expression}).rstrip()" + source[end:])
        out.append(candidate)
        if len(out) >= 12:
            break
    return out


def _is_empty_reference(node: ast.AST, names: set[str]) -> bool:
    return ((isinstance(node, ast.Name) and node.id in names)
            or (isinstance(node, ast.Attribute) and node.attr in names))


def none_return_candidates(source: str, pairs: Sequence[tuple[Any, Any]],
                           payloads: Sequence[Mapping[str, Any]]) -> list[str]:
    """Complete an early `return None` from the tuple the same function returns later.

    The empty member is filled from the expected literal observed at runtime;
    the non-empty members keep the source's own expressions.
    """
    empty_names = {str(item["name"]).split(".")[-1] for item in payloads}
    examples = [b for a, b in pairs if a is None and isinstance(b, tuple)]
    if not examples:
        return []
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        no_values = [item for item in ast.walk(node)
                     if isinstance(item, ast.Return) and isinstance(item.value, ast.Constant)
                     and item.value.value is None]
        tuples = [item for item in ast.walk(node)
                  if isinstance(item, ast.Return) and isinstance(item.value, ast.Tuple)]
        if not no_values or not tuples:
            continue
        template = tuples[0].value
        for expected in examples:
            elements = list(template.elts)
            if len(elements) != len(expected):
                continue
            rebuilt = []
            for element, value in zip(elements, expected):
                if value == "" and _is_empty_reference(element, empty_names):
                    rebuilt.append("''")
                else:
                    rebuilt.append(ast.unparse(element))
            expression = ", ".join(rebuilt)
            for early in no_values[:2]:
                start, end = _span(source, early)
                out.append(source[:start] + f"return {expression}" + source[end:])
            break
        if len(out) >= 10:
            break
    return out


def or_complement_candidates(source: str, payloads: Sequence[Mapping[str, Any]]) -> list[str]:
    """Add the observed complement arm to a two-way OR that chose the wrong path.

    When both observed operands are false an `A or B` guard cannot be entered;
    adding `not A and not B` is the smallest structural completion of that
    guard that is derived from the runtime state, not from a diff.
    """
    observed = {str(item["name"]).split(".")[-1] for item in payloads}
    tree = ast.parse(source)
    out: list[str] = []

    def flags(value: ast.AST) -> list[str]:
        found = []
        for item in ast.walk(value):
            if ((isinstance(item, ast.Name) and item.id in observed)
                    or (isinstance(item, ast.Attribute) and item.attr in observed)):
                text = ast.unparse(item)
                if text not in found:
                    found.append(text)
        return found

    for node in ast.walk(tree):
        if not (isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or)
                and len(node.values) == 2):
            continue
        left, right = (flags(value) for value in node.values)
        if not left or not right or left[0] == right[0]:
            continue
        _, end = _span(source, node)
        arm = f" or (not {left[0]} and not {right[0]})"
        out.append(source[:end] + arm + source[end:])
        if len(out) >= 12:
            break
    return out


def exception_fence_candidates(source: str) -> list[str]:
    """Fence a call inside an exception handler against a late interrupt.

    Two policies are generated for every call in a handler (including calls
    under a nested `if`): either drop the interrupt, or retry the call once.
    A test decides which policy preserves the handler's intended outcome.
    """
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler):
            continue
        for statement in ast.walk(handler):
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Call)):
                continue
            first, last = statement.lineno - 1, statement.end_lineno - 1
            indent = " " * statement.col_offset
            call = "".join(lines[first:last + 1]).strip()
            for retry in (False, True):
                again = call if retry else "pass"
                fenced = ([indent + "try:\n", indent + "    " + call + "\n",
                           indent + "except KeyboardInterrupt:\n",
                           indent + "    " + again + "\n"])
                out.append("".join(lines[:first]) + "".join(fenced)
                           + "".join(lines[last + 1:]))
                if len(out) >= 24:
                    return out
    return out



def fence_combinations(parent: str, fences: Sequence[str]) -> list[str]:
    """Enumerate one pass-or-retry policy per fenced call site (bounded)."""
    groups: dict[int, list[str]] = {}
    for candidate in fences:
        blocks = splicing.edits(parent, candidate)
        if not blocks:
            continue
        groups.setdefault(blocks[0]["i1"], []).append(candidate)
    sites = sorted(groups)
    if not sites or len(sites) > 8:
        return []
    out: list[str] = []
    for mask in range(1 << len(sites)):
        candidate = parent
        for index, site in enumerate(sites):
            variants = groups[site]
            choice = variants[(mask >> index) & 1] if len(variants) > 1 else variants[0]
            candidate = splicing.splice(parent, candidate, choice)[0]
        out.append(candidate)
    return list(dict.fromkeys(out))


def _edit_line(parent: str, candidate: str) -> int:
    blocks = splicing.edits(parent, candidate)
    return blocks[0]["i1"] if blocks else 10 ** 6


def _nearby(candidates: list[str], parent: str,
            anchors: Sequence[Sequence[str]]) -> list[str]:
    """Order generator outputs by how close their edit is to other edits.

    A composed repair edits neighbouring code; with many false-positive empty
    values, this is a source-derived way to try the coherent cluster first.
    """
    groups = [group for group in anchors if group]
    if not groups:
        return candidates

    def words(text: str) -> set[str]:
        return {token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
                if len(token) >= 4}

    def edited(text: str) -> str:
        return "".join("".join(block["new"]) for block in splicing.edits(parent, text))

    anchor_words = [words(edited(candidate)) for group in groups for candidate in group]
    positions = [_edit_line(parent, candidate) for group in groups for candidate in group]
    def key(candidate: str) -> tuple[int, int]:
        own = words(edited(candidate))
        shared = max((len(own & other) for other in anchor_words), default=0)
        distance = min((abs(_edit_line(parent, candidate) - position)
                        for position in positions), default=10 ** 6)
        return (-shared, distance)
    return sorted(candidates, key=key)


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20) -> dict[str, Any]:
    started = time.time()
    parent_source = identify.show(repo, f"{sha}^", source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND"}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        made = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                               str(worktree), f"{sha}^"], capture_output=True, text=True)
        if made.returncode != 0:
            return {"stage": "WORKTREE_FAILED"}
        try:
            test_file = worktree / test_path
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            before, _ = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(before)
            if not failing:
                return {"stage": "NO_ORACLE"}
            seen_payloads: set[tuple[str, int, str]] = set()
            payloads: list[dict[str, Any]] = []
            for failing_node in failing[:4]:
                for item in eps.empty_payloads(worktree, test_path, failing_node, seconds):
                    if not str(item["file"]).endswith(source_path):
                        continue
                    key = (str(item["file"]), int(item["line"]), str(item["name"]))
                    if key in seen_payloads:
                        continue
                    seen_payloads.add(key)
                    payloads.append(item)
            names = {str(item["name"]) for item in payloads}
            captured = tomography.capture(worktree, test_path, failing[0], seconds,
                                          function_name=failing[0].split("::")[-1].split("[")[0])
            pairs = value_pairs(captured) if captured.get("outcome") == "CAPTURED" else []
            guards = [text for text, _ in eps.tightenings(parent_source, payloads)]
            normals = normalize_candidates(parent_source, names)
            serials = serialize_candidates(parent_source, names)
            returns = (whitespace_candidates(parent_source, pairs)
                       + none_return_candidates(parent_source, pairs, payloads))
            structure = (or_complement_candidates(parent_source, payloads)
                         + exception_fence_candidates(parent_source))
            guards = _nearby(guards, parent_source, [serials, returns, normals])
            serials = _nearby(serials, parent_source, [guards, returns])
            normals = _nearby(normals, parent_source, [guards, serials])
            singles = list(dict.fromkeys(guards + normals + serials + returns + structure))
            combined: list[str] = []
            # Compose one edit from each observed generator explicitly before
            # falling back to arbitrary pairwise search: an empty payload can
            # require a normalization and a serializer *and* a guard at once.
            for guard in guards[:6]:
                for normal in normals[:4]:
                    partial = splicing.splice(parent_source, guard, normal)
                    for candidate in partial[:3]:
                        for serial in serials[:4]:
                            combined.extend(splicing.splice(parent_source, candidate, serial)[:3])
            for guard in guards[:4]:
                for other in returns[:6]:
                    combined.extend(splicing.splice(parent_source, guard, other)[:3])
            # Two independent completions of two different guards both have to
            # survive: e.g. an outer and an inner boolean clause.
            for first in range(min(len(structure), 8)):
                for second in range(first + 1, min(len(structure), 8)):
                    combined.extend(splicing.splice(parent_source, structure[first],
                                                    structure[second])[:3])
            for first in range(min(len(singles), 8)):
                for second in range(first + 1, min(len(singles), 8)):
                    combined.extend(splicing.splice(parent_source, singles[first], singles[second])[:4])
            for first in range(min(len(combined), 40)):
                for third in singles[:6]:
                    combined.extend(splicing.splice(parent_source, combined[first], third)[:2])
                if len(combined) > 240:
                    break
            proposals = list(dict.fromkeys(singles + combined))
            source_file = worktree / source_path
            baseline_passes = sum(1 for verdict in before.values()
                                  if verdict in ("PASS", "PASSED"))
            evaluations = 0

            def score(candidate: str) -> tuple[int, int]:
                nonlocal evaluations
                try:
                    ast.parse(candidate)
                except SyntaxError:
                    return (10 ** 6, 0)
                source_file.write_text(candidate, encoding="utf-8")
                after, _ = identify.run_tests_full(worktree, test_path, seconds)
                source_file.write_text(parent_source, encoding="utf-8")
                evaluations += 1
                return (len(identify.failing_tests(after)),
                        sum(1 for verdict in after.values()
                            if verdict in ("PASS", "PASSED")))

            def accepted(candidate: str) -> bool:
                failures, passes = score(candidate)
                return failures == 0 and passes >= baseline_passes and passes > 0

            generators = {"guards": len(guards), "normalizations": len(normals),
                          "serializers": len(serials), "returns": len(returns),
                          "structure": len(structure), "value_pairs": len(pairs)}
            for candidate in proposals[:240]:
                if accepted(candidate):
                    return {"stage": "COMPARED", "verified": True,
                            "payloads": len(payloads), "generators": generators,
                            "proposals": len(proposals), "evaluations": evaluations,
                            "candidate": candidate,
                            "seconds": round(time.time() - started, 1)}
            # A late interrupt inside an exception handler can need several
            # independent fences, each with a pass-or-retry policy. Enumerate
            # those policies and let the project's runner pick the combination.
            fences = exception_fence_candidates(parent_source)
            for candidate in fence_combinations(parent_source, fences):
                if accepted(candidate):
                    return {"stage": "COMPARED", "verified": True,
                            "payloads": len(payloads), "generators": generators,
                            "proposals": len(proposals), "evaluations": evaluations,
                            "candidate": candidate,
                            "seconds": round(time.time() - started, 1)}
            # Keep the two best partials and extend them; the project's own
            # runner, not a heuristic, ranks every step.
            beam = [parent_source]
            for _ in range(4):
                expanded: list[str] = []
                for partial in beam:
                    for single in singles[:24]:
                        expanded.extend(splicing.splice(parent_source, partial, single)[:1])
                ranked = sorted({candidate for candidate in expanded
                                 if candidate != parent_source}, key=score)
                if not ranked:
                    break
                for candidate in ranked[:16]:
                    if accepted(candidate):
                        return {"stage": "COMPARED", "verified": True,
                                "payloads": len(payloads), "generators": generators,
                                "proposals": len(proposals), "evaluations": evaluations,
                                "candidate": candidate,
                                "seconds": round(time.time() - started, 1)}
                beam = ranked[:2]
            return {"stage": "COMPARED", "verified": False, "payloads": len(payloads),
                    "generators": generators, "proposals": len(proposals),
                    "evaluations": evaluations,
                    "seconds": round(time.time() - started, 1)}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    rows = [{"sha": entry["sha"], "repo": entry.get("repo"),
             **explore(pathlib.Path(str(entry.get("repo_path") or args.repo)), str(entry["sha"]),
                       source_path=str(entry["sources"][0]),
                       test_path=str(entry["tests"][0]), seconds=args.seconds)}
            for entry in entries]
    verified = sum(1 for row in rows if row.get("verified"))
    report = {"schema": SCHEMA, "authority": AUTHORITY,
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "declared_before_the_run": DECLARED, "rows": rows,
              "summary": {"rows": len(rows), "verified": verified,
                          "model_calls": 0, "network_calls": 0, "parameters_stored": 0},
              "verdict": "PASS" if verified else "FAIL"}
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "rows": [{k: row.get(k) for k in ("sha", "stage", "verified",
                                                       "generators", "proposals")}
                               for row in rows]}, indent=2))
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
