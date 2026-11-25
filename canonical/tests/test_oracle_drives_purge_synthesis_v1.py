"""The whole blind chain: green suite -> oracle violation -> contract -> purge -> law accepts.

No test of the defect is used anywhere in this file's subject: the fixture's shipped suite registers a
plugin and never unregisters it. The only thing that says "this is wrong" is the name/effect law, and
the only thing that says "this is right" is the same law re-checked after the patch.
"""

from __future__ import annotations

import textwrap

from canonical.swe_kernel import metamorphic_oracle_v1 as mo
from canonical.swe_kernel import spec_contract_synthesis_v1 as scs
from canonical.swe_kernel.semantic_causal_engine_v1 import build_project_cpg

MODULE = textwrap.dedent(
    '''
    class Registry:
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
            return self._distinfo
    '''
)

SUITE = textwrap.dedent(
    """
    from pkg.registry import Registry


    class Plugin:
        pass


    def test_register_then_read():
        reg = Registry()
        p = Plugin()
        reg.register(p, name="p")
        reg._distinfo.append((p, "dist"))
        assert reg.get_plugins() == [p]
    """
)


def _repo(tmp_path):
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "registry.py").write_text(MODULE, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_registry.py").write_text(SUITE, encoding="utf-8")
    return root


def test_violation_becomes_a_contract_whose_purge_the_law_accepts(tmp_path):
    root = _repo(tmp_path)
    run = mo.violations_from_run(root, ["pkg.registry"], ["-q", "tests/"])
    assert run.get("exitstatus") == 0, "the shipped suite is green: that is the blind condition"
    hits = [v for v in run.violations if v["law"] == "remove_argument_vanishes"]
    assert hits, "the oracle must notice without being shown the failing test"

    cpg = build_project_cpg(root)
    # Every getter the law named is a candidate container; acceptance is judged against the *whole*
    # violation set, so a purge that silences one getter while another still leaks is rejected.
    getters = sorted({v["getter"] for v in hits})
    accepted = None
    for getter in getters:
        contract = scs.PostconditionContract(
            getter=getter, mutator="unregister", deleted_arg="plugin", node_id="Registry.unregister",
        )
        for tag, rel_path, blob in scs.state_consistency_candidates(root, cpg, contract, max_candidates=8):
            (root / rel_path).write_bytes(blob)
            after = mo.violations_from_run(root, ["pkg.registry"], ["-q", "tests/"])
            if not after.violations:
                accepted = tag
                break
        if accepted:
            break
    assert accepted is not None, "at least one synthesized purge must clear every violation"
    assert "purge self._distinfo" in accepted, "silencing one getter while another leaks is not a repair"
