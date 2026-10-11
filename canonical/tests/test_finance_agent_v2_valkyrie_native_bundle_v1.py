from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "canonical" / "integrations" / "brain_fabv2_native_v1"

COPIES = {
    "canonical/runtime/finance_agent_v2_brain_native_llm_v1.py":
        ROOT / "canonical" / "runtime" / "finance_agent_v2_brain_native_llm_v1.py",
    "canonical/runtime/finance_quantitative_dependency_v1.py":
        ROOT / "canonical" / "runtime" / "finance_quantitative_dependency_v1.py",
    "canonical/runtime/finance_quantitative_question_contract_v1.py":
        ROOT / "canonical" / "runtime" / "finance_quantitative_question_contract_v1.py",
    "canonical/runtime/finance_metric_xbrl_registry_v1.py":
        ROOT / "canonical" / "runtime" / "finance_metric_xbrl_registry_v1.py",
    "canonical/runtime/finance_agent_v2_zero_spend_adapter_v1.py":
        ROOT / "canonical" / "runtime" / "finance_agent_v2_zero_spend_adapter_v1.py",
    "canonical/runtime/zero_spend_provider_guard_v1.py":
        ROOT / "canonical" / "runtime" / "zero_spend_provider_guard_v1.py",
}


class BundleTests(unittest.TestCase):
    def test_vendored_runtime_is_byte_identical_to_canonical(self):
        for rel, source in COPIES.items():
            bundled = BUNDLE / rel
            self.assertEqual(
                bundled.read_bytes(),
                source.read_bytes(),
                rel,
            )

    def test_contract_has_no_model_dependency(self):
        text = (BUNDLE / "contract.yaml").read_text()
        self.assertNotIn("{model}", text)
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("ANTHROPIC_API_KEY", text)
        self.assertIn("vals_format/config.json", text)
        self.assertIn("vals_format/result.json", text)

    def test_setup_pins_first_party_finance_agent(self):
        text = (BUNDLE / "setup.sh").read_text()
        self.assertIn("502aab6fdaa3fb9294905c7453f89882baa8d39b", text)
        self.assertIn("22c012241a430975266fb7f8d2fe7af8e9f1b8d4", text)
        self.assertIn("19b85ce4e110e39f410c52b2efa0e33f651fa6d1", text)

    def test_wrapper_requires_zero_spend_snapshots_and_native_llm(self):
        text = (BUNDLE / "run_agent.py").read_text()
        self.assertIn("BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON_REQUIRED", text)
        self.assertIn("llm=create_vals_llm()", text)
        self.assertIn("install_before_get_agent(", text)
        self.assertNotIn("CUSTOM_ENDPOINT", text)
        self.assertNotIn("get_registry_model", text)

    def test_wrapper_fail_closes_without_snapshots(self):
        path = BUNDLE / "run_agent.py"
        spec = importlib.util.spec_from_file_location("brain_fabv2_native_run", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = os.environ.pop("BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON", None)
        try:
            with self.assertRaises(Exception) as ctx:
                module._load_snapshots()
            self.assertIn(
                "BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON_REQUIRED",
                str(ctx.exception),
            )
        finally:
            if old is not None:
                os.environ["BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON"] = old

    def test_strict_outcome_rejects_provider_errors(self):
        path = BUNDLE / "run_agent.py"
        spec = importlib.util.spec_from_file_location("brain_fabv2_native_run2", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(Exception):
            module._strict_zero_spend_outcome(
                "tavily", "tavily:1", None, RuntimeError("network")
            )
        safe = module._strict_zero_spend_outcome(
            "tavily", "tavily:2", {"results": []}, None
        )
        self.assertEqual(safe["observed_cost_usd"], 0)
        self.assertFalse(safe["paid_charge_observed"])


if __name__ == "__main__":
    unittest.main()
