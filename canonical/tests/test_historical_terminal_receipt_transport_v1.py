from __future__ import annotations

import copy
import unittest
from pathlib import Path

from canonical.runtime.historical_terminal_receipt_transport_v1 import (
    CONFIG_PATH,
    ROOT,
    _load,
    evaluate,
)


class HistoricalTerminalReceiptTransportTests(unittest.TestCase):
    def fixtures(self):
        config = _load(CONFIG_PATH)
        wave = _load(ROOT / config["terminal_wave"]["path"])
        verification = _load(ROOT / config["current_binding_verification"]["path"])
        bindings = {}
        current = {}
        historical = {}
        for route in config["routes"]:
            path = route["binding_path"]
            bindings[path] = _load(ROOT / path)
            current[path] = route["expected_binding_blob_sha"]
            historical[path] = route["expected_binding_blob_sha"]
        return config, wave, verification, bindings, current, historical

    def test_exact_identity_transports_without_acceptance_overclaim(self):
        args = self.fixtures()
        out = evaluate(*args)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["transported_route_count"], 3)
        self.assertEqual(out["acceptance_predicates_closed"], 0)
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["execution_authority"])
        for row in out["routes"]:
            self.assertTrue(row["transported_terminal_evidence"])
            self.assertFalse(row["acceptance_predicate_closed"])
            self.assertFalse(row["full_scope_noninferiority_proved"])
            self.assertFalse(row["fresh_terminal_replay_required"])

    def test_historical_binding_drift_fails_closed(self):
        config, wave, verification, bindings, current, historical = self.fixtures()
        historical = copy.deepcopy(historical)
        path = config["routes"][0]["binding_path"]
        historical[path] = "0" * 40
        out = evaluate(config, wave, verification, bindings, current, historical)
        self.assertFalse(out["pass"])
        self.assertTrue(any("HISTORICAL_BINDING_BLOB_MISMATCH" in e for e in out["errors"]))

    def test_replay_guard_mutation_fails_closed(self):
        config, wave, verification, bindings, current, historical = self.fixtures()
        wave = copy.deepcopy(wave)
        wave["result_guards"]["no_tuning_replay"] = False
        out = evaluate(config, wave, verification, bindings, current, historical)
        self.assertFalse(out["pass"])
        self.assertIn("TUNING_REPLAY_NOT_FAIL_CLOSED", out["errors"])

    def test_delegation_scope_caveat_is_load_bearing(self):
        config, wave, verification, bindings, current, historical = self.fixtures()
        bindings = copy.deepcopy(bindings)
        path = config["routes"][0]["binding_path"]
        bindings[path]["source_pool"]["terminal_scope_claim"] = "EXHAUSTIVE"
        out = evaluate(config, wave, verification, bindings, current, historical)
        self.assertFalse(out["pass"])
        self.assertTrue(any("REQUIRED_SCOPE_CAVEAT_MISSING" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
