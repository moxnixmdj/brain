from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
LEARNING = ROOT / "canonical/runtime/autonomous_verified_self_improvement_v1.py"
DRIVER = ROOT / "canonical/runtime/r3_improvement_queue_driver_v1.py"

EXPECTED_DURABLE_QUEUE_KINDS = {
    "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
    "COLLECT_MATCHING_VERIFIED_EPISODE",
    "EXPAND_SUCCESS_VERIFICATION_FRONTIER",
    "REPAIR_FAILURE_CLASS",
    "REVERIFY_QUARANTINED_SKILL",
    "SEEK_VERIFIED_SCOPE_GENERALIZATION",
    "VERIFY_EPISODE",
    "VERIFY_SKILL_CANDIDATE",
}


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _string_constants(tree: ast.AST) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                out[target.id] = value.value
    return out


def _resolve_string(node: ast.AST, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _enqueued_kinds(path: Path) -> set[str]:
    tree = _tree(path)
    constants = _string_constants(tree)
    out: set[str] = set()
    unresolved: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (
            fn.attr if isinstance(fn, ast.Attribute) else None
        )
        if name != "_enqueue_improvement":
            continue
        kind_kw = next((kw for kw in node.keywords if kw.arg == "kind"), None)
        if kind_kw is None:
            unresolved.append(f"line {getattr(node, 'lineno', '?')}: missing kind")
            continue
        value = _resolve_string(kind_kw.value, constants)
        if value is None:
            unresolved.append(
                f"line {getattr(node, 'lineno', '?')}: non-static kind expression"
            )
            continue
        out.add(value)
    if unresolved:
        raise AssertionError("Unresolved durable queue producers: " + "; ".join(unresolved))
    return out


def _consumed_kinds(path: Path) -> set[str]:
    tree = _tree(path)
    constants = _string_constants(tree)
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            not isinstance(test, ast.Compare)
            or len(test.ops) != 1
            or not isinstance(test.ops[0], ast.Eq)
            or len(test.comparators) != 1
            or not isinstance(test.left, ast.Name)
            or test.left.id != "kind"
        ):
            continue
        value = _resolve_string(test.comparators[0], constants)
        if value is not None:
            out.add(value)
    return out


class R3QueueKindTotalityTests(unittest.TestCase):
    def test_every_durable_queue_kind_has_an_explicit_driver_disposition(self):
        produced = _enqueued_kinds(LEARNING) | _enqueued_kinds(DRIVER)
        consumed = _consumed_kinds(DRIVER)

        self.assertEqual(
            produced,
            EXPECTED_DURABLE_QUEUE_KINDS,
            f"durable producer set changed; update the totality contract deliberately: {sorted(produced)}",
        )
        self.assertEqual(
            consumed,
            EXPECTED_DURABLE_QUEUE_KINDS,
            f"driver disposition set changed; every durable kind must remain explicit: {sorted(consumed)}",
        )
        self.assertEqual(produced, consumed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
