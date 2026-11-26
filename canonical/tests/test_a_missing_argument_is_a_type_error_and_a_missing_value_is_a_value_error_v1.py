"""Which exception an `assert` becomes is decided by the AST, not by the test.

The `static_assert_validation` law names the site but not the edit: an `assert` in a public function has to
become a raise, and the family is a real choice. It is not free, and it is not a guess:

- the condition tests a **live parameter** — the caller did not supply a required input — `TypeError`;
- the condition tests a **local**, or a parameter that was rebound above the assert — the call was well
  formed and its value is wrong — `ValueError`.

Measured on pluggy `8051a4d^1`, whose two asserts sit three lines apart and must not be typed the same way:

    if name is None:
        assert plugin is not None, "one of name or plugin needs to be specified"   # parameter -> TypeError
        name = self.get_name(plugin)
        assert name is not None, "plugin is not registered"                        # rebound -> ValueError

`name` is *also* a parameter of `unregister`, so a name-only rule typed both `TypeError`. Rebinding order is
what separates them, and nothing about the test was consulted to decide it.
"""

from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import law_repair_synthesis_v1 as synthesis

SOURCE = '''\
class Manager:
    def unregister(self, plugin=None, name=None):
        if name is None:
            assert plugin is not None, "one of name or plugin needs to be specified"
            name = self.get_name(plugin)
            assert name is not None, "plugin is not registered"
        return name
'''


def _patched(tmp_path: pathlib.Path, sites):
    (tmp_path / "manager.py").write_text(SOURCE)
    candidates = synthesis.assert_to_raise_candidates(tmp_path, sites)
    assert candidates, "no candidate produced"
    _tag, blobs = candidates[0]
    return next(iter(blobs.values())).decode()


def test_a_parameter_assert_becomes_a_type_error(tmp_path):
    patched = _patched(tmp_path, [("unregister", 4)])
    assert 'raise TypeError("one of name or plugin needs to be specified")' in patched


def test_a_rebound_name_becomes_a_value_error(tmp_path):
    patched = _patched(tmp_path, [("unregister", 6)])
    assert 'raise ValueError("plugin is not registered")' in patched


def test_no_assert_survives_at_a_named_site(tmp_path):
    patched = _patched(tmp_path, [("unregister", 4), ("unregister", 6)])
    tree = ast.parse(patched)
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    assert "raise TypeError" in patched and "raise ValueError" in patched


def test_the_guard_keeps_the_original_condition(tmp_path):
    patched = _patched(tmp_path, [("unregister", 4)])
    assert "if not (plugin is not None):" in patched


def test_a_function_without_asserts_yields_nothing(tmp_path):
    (tmp_path / "manager.py").write_text("def f(x):\n    return x\n")
    assert synthesis.assert_to_raise_candidates(tmp_path) == []


def test_only_the_named_function_is_edited(tmp_path):
    (tmp_path / "manager.py").write_text(
        "def other(x):\n"
        "    assert x is not None, \"other\"\n"
        "    return x\n"
        "def named(x):\n"
        "    return x\n")
    assert synthesis.assert_to_raise_candidates(tmp_path, [("named", 5)]) == []
