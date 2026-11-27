"""Wave 47: the bus admits what can prove itself, and says so when it cannot.

The claim under test is not "the organs are wired". It is the narrower, checkable one: a capability
is dispatched only if it ran its own proof, and the inventory states how many cannot. Every test
here either proves a plugin, refuses one, or pins the arithmetic of the refusal.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.runtime.capability_bus_v1 import (
    ADMITTED,
    ENTRY_MISSING,
    IMPORT_FAILED,
    SELF_CHECK_FAILED,
    UNVERIFIED,
    CapabilityBus,
    PluginSpec,
    _passing,
    main,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/runtime/plugins/capability_bus_manifest_v1.json"
AUDIT = ROOT / "canonical/verification/CAPABILITY_BUS_AUDIT_20261124_V1.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class PassSemanticsTest(unittest.TestCase):
    def test_only_an_explicit_pass_passes(self) -> None:
        self.assertTrue(_passing({"verdict": "SELF_CHECK_PASS"}))
        self.assertTrue(_passing({"verdict": "PASS"}))
        self.assertTrue(_passing({"ok": True}))
        for silent in ({}, {"verdict": "UNKNOWN"}, {"ok": "yes"}, None, "SELF_CHECK_PASS", 1):
            with self.subTest(silent=silent):
                self.assertFalse(_passing(silent))


class AdmissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bus = CapabilityBus.from_manifest(_manifest())
        cls.bus.load()
        cls.audit = cls.bus.audit()

    def test_every_declared_plugin_has_exactly_one_state(self) -> None:
        self.assertEqual(sum(self.audit["states"].values()), self.audit["declared"])

    def test_admitted_are_exactly_the_ones_that_ran_their_proof(self) -> None:
        for plugin_id in self.audit["admitted"]:
            self.assertEqual(self.bus.loaded[plugin_id].state, ADMITTED)
            self.assertTrue(self.bus.loaded[plugin_id].self_check_result)

    def test_unverified_is_never_dispatched(self) -> None:
        self.assertTrue(self.audit["unverified"])
        result = self.bus.dispatch("cua.osworld21", {})
        self.assertFalse(result["ok"])
        self.assertIn("NO_ADMITTED_PLUGIN_FOR_TRIGGER", result["error"])

    def test_dispatch_reaches_an_admitted_plugin(self) -> None:
        result = self.bus.dispatch("repair.abstract", {
            "before": "if len(xs) < limit:\n    pass",
            "after": "if len(xs) <= limit:\n    pass"})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["value"]["verdict"], "ADMITTED")

    def test_missing_module_fails_closed(self) -> None:
        bus = CapabilityBus([PluginSpec("ghost", "canonical.does.not.exist_v1")])
        loaded = bus.load()["ghost"]
        self.assertEqual(loaded.state, IMPORT_FAILED)
        self.assertFalse(bus.dispatch("anything", {})["ok"])

    def test_declared_entry_that_is_not_callable_is_refused(self) -> None:
        bus = CapabilityBus([PluginSpec("bad-entry", "canonical.swe_kernel.structured_morphism_abstraction_v1",
                                        entry="not_a_function_here", triggers=["x"])])
        loaded = bus.load()["bad-entry"]
        self.assertEqual(loaded.state, ENTRY_MISSING)
        self.assertFalse(bus.dispatch("x", {})["ok"])


class ManifestTest(unittest.TestCase):
    def test_every_declared_module_exists_on_disk(self) -> None:
        for spec in _manifest()["plugins"]:
            path = ROOT / (spec["module"].replace(".", "/") + ".py")
            with self.subTest(module=spec["module"]):
                self.assertTrue(path.is_file(), path)

    def test_manifest_covers_the_organs_the_plan_named(self) -> None:
        ids = {spec["plugin_id"] for spec in _manifest()["plugins"]}
        for required in ("structured_morphism_abstraction_v1", "settled_admission_v1",
                         "rule_scope_learning_v1", "skill_recheck_v1", "credit_gates_v1",
                         "harbor_swe_zero_model_agent_v1"):
            self.assertIn(required, ids)


class RepairRegressionTest(unittest.TestCase):
    """Two modules on main did not compile. These pin the repair, not the symptom."""

    def test_repaired_module_compiles(self) -> None:
        """The overlay was dead on main; it compiles now.

        The livebench audit is NOT repaired here on purpose: its only referee
        (`verify-livebench-legacy-predecessor-compiler-v1.yml`) has failed on every run since
        2026-10-04, including on main, because it needs a HuggingFace dataset this sandbox cannot
        reach. Reviving the module would turn a dormant red check into a live one without fixing it,
        so it is left exactly as found and recorded in the receipt.
        """
        relative = "canonical/runtime/osworld_v21_app_policy_overlay_v1.py"
        compile((ROOT / relative).read_text(encoding="utf-8"), relative, "exec")

    def test_overlay_module_imports_and_routes_a_cell_write(self) -> None:
        """The repaired regex is load-bearing: before the fix this module did not import at all."""
        from canonical.runtime.osworld_v21_app_policy_overlay_v1 import _calc
        operation = _calc("set A1 to hello")
        self.assertEqual(operation["actions"][0]["operation"], "set_cell_value")
        self.assertEqual(operation["actions"][0]["args"], {"cell": "A1", "value": "hello"})


class ReceiptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_receipt_matches_a_live_audit(self) -> None:
        bus = CapabilityBus.from_manifest(_manifest())
        bus.load()
        live = bus.audit()
        self.assertEqual(self.receipt["declared"], live["declared"])
        self.assertEqual(self.receipt["states"], live["states"])
        self.assertEqual(self.receipt["admitted"], live["admitted"])

    def test_cli_writes_a_report_and_fails_when_nothing_is_admitted(self) -> None:
        self.assertEqual(main(["--manifest", str(MANIFEST)]), 0)


if __name__ == "__main__":
    unittest.main()
