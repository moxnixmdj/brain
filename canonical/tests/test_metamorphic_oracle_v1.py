"""The metamorphic oracle must manufacture a failing test without being shown one.

The point of these tests is the blind case: the module under test ships a *passing* suite that never
calls the broken mutator, exactly like `pluggy` before `50585e0`, where the only caller of
`unregister` was the hidden test. The oracle has to notice anyway, from the name/effect law alone.
"""

from __future__ import annotations

import textwrap

from canonical.swe_kernel import metamorphic_oracle_v1 as mo

BUGGY = textwrap.dedent(
    '''
    class Registry:
        """A registry whose unregister forgets to purge the distribution list."""

        def __init__(self):
            self._plugins = []
            self._distinfo = []

        def register(self, plugin, name=None):
            self._plugins.append(plugin)
            return name

        def unregister(self, plugin=None, name=None):
            self._plugins[:] = [p for p in self._plugins if p is not plugin]
            return None

        def get_plugins(self):
            return list(self._plugins)

        def list_plugin_distinfo(self):
            return list(self._distinfo)
    '''
)

FIXED = BUGGY.replace(
    "        self._plugins[:] = [p for p in self._plugins if p is not plugin]\n        return None",
    "        self._plugins[:] = [p for p in self._plugins if p is not plugin]\n"
    "        self._distinfo[:] = [e for e in self._distinfo if e[0] is not plugin]\n"
    "        return None",
)
assert FIXED != BUGGY, "the fixture must actually differ, or the silence test proves nothing"

# A green suite that registers a plugin but never unregisters it: the hidden-test situation.
SUITE = textwrap.dedent(
    """
    from pkg.registry import Registry


    class Plugin:
        pass


    def test_register_then_read():
        reg = Registry()
        p = Plugin()
        reg.register(p, name="p")
        assert reg.get_plugins() == [p]
        reg._distinfo.append((p, "dist"))
        assert reg.list_plugin_distinfo() == [(p, "dist")]
    """
)


def _repo(tmp_path, module_source: str):
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "registry.py").write_text(module_source, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_registry.py").write_text(SUITE, encoding="utf-8")
    return root


def test_oracle_fires_on_a_mutator_that_leaves_the_object_behind(tmp_path):
    root = _repo(tmp_path, BUGGY)
    run = mo.violations_from_run(root, ["pkg.registry"], ["-q", "tests/"])
    assert run.get("exitstatus") == 0, "the shipped suite passes; that is the whole difficulty"
    laws = {(v["where"], v["getter"]) for v in run.violations}
    assert ("Registry.unregister", "list_plugin_distinfo") in laws
    assert run.get("probes", 0) > 0, "the call must be manufactured, not observed"


def test_oracle_is_silent_once_the_mutator_purges(tmp_path):
    root = _repo(tmp_path, FIXED)
    run = mo.violations_from_run(root, ["pkg.registry"], ["-q", "tests/"])
    assert run.get("exitstatus") == 0
    assert run.violations == [], f"a correct mutator must not be accused: {run.violations}"


def test_vocabulary_classification_is_name_only():
    assert mo.classify_method("unregister") == "remove"
    assert mo.classify_method("remove_plugin") == "remove"
    assert mo.classify_method("register") == "add"
    assert mo.classify_method("get_plugins") is None
    assert mo.classify_method("__init__") is None
