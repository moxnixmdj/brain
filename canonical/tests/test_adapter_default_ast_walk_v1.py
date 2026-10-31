"""Differential checks against the original full-tree default detector."""
import ast
import pathlib

import pytest

from canonical.runtime import declared_input_derivation_v1 as derivation


def reference(source, path):
    tree = ast.parse(source)
    found = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "args"):
            continue
        key = node.args[0]
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        guarded = len(node.args) >= 2
        for parent in ast.walk(tree):
            if isinstance(parent, ast.BoolOp) and isinstance(parent.op, ast.Or) and node in parent.values:
                guarded = True
            if isinstance(parent, ast.If) and node in ast.walk(parent.test):
                guarded = True
        if (guarded and key.value in derivation._CONFIGURATION_SLOTS
                and not any(word in key.value.lower() for word in ("output", "result", "report"))):
            found.setdefault(key.value, f"{path}:{node.lineno}")
    return found


@pytest.mark.parametrize("body", [
    "value = args.get('timeout_s', 10)",
    "value = args.get('timeout_s') or 10",
    "if args.get('strict'):\n    value = 1",
    "if args.get('seed') == 7 and args.get('verbose'):\n    value = 1",
    "if True:\n    value = args.get('strict')",  # a body is not its condition
    "value = int(args.get('timeout_s')) or 10",  # not a direct OR operand
    "value = args.get('timeout_s') and 10",  # AND proves no default
    "if args.get('output_path'):\n    value = 1",  # output is never a config knob
    "value = other.get('timeout_s', 10)",
    "value = args.get('strict') if True else False",  # IfExp is not If
])
def test_parent_walk_preserves_exact_default_evidence(body, tmp_path):
    source = "def run(args, other):\n" + "\n".join("    " + line for line in body.splitlines()) + "\n"
    adapter = tmp_path / "adapter.py"
    adapter.write_text(source)
    entry = {"source": {"adapter_path": "adapter.py"}}
    actual = derivation.adapter_defaulted_keys(entry, tmp_path)
    assert actual == reference(source, "adapter.py")


def test_real_repair_adapters_match_original_detector():
    root = pathlib.Path(__file__).resolve().parents[2]
    for name in ("python_repair_measured_acceptance_controller_v1.py",
                 "python_iterative_software_repair_loop_v1.py",
                 "python_provenance_guided_coupled_repair_v1.py"):
        rel = "canonical/runtime/bound_capabilities/" + name
        source = (root / rel).read_text()
        actual = derivation.adapter_defaulted_keys({"source": {"adapter_path": rel}}, root)
        assert actual == reference(source, rel)
