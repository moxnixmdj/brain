#!/usr/bin/env python3
import copy
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"

spec = importlib.util.spec_from_file_location(
    "astra_runtime_content_bound_trace_test", RUNTIME_PATH
)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class ContentBoundControllerTraceTests(unittest.TestCase):
    def _record(self, cycle, previous, value):
        action = {"type": "finish", "args": {"summary": f"step-{cycle}"}}
        result = {"type": "finish", "summary": value}
        return runtime._controller_trace_record(cycle, action, result, previous)

    def test_valid_chain_survives_prefix_validation(self):
        r0 = self._record(
            0, runtime._CONTROLLER_TRACE_GENESIS_SHA256, "alpha"
        )
        r1 = self._record(1, r0["record_sha256"], "beta")
        valid, rewound = runtime._validated_checkpoint_prefix(
            [r0, r1], require_content_bound_trace=True
        )
        self.assertEqual(valid, [r0, r1])
        self.assertIsNone(rewound)

    def test_result_mutation_invalidates_bound_record(self):
        r0 = self._record(
            0, runtime._CONTROLLER_TRACE_GENESIS_SHA256, "alpha"
        )
        mutated = copy.deepcopy(r0)
        mutated["result"]["summary"] = "tampered"
        valid, rewound = runtime._validated_checkpoint_prefix(
            [mutated], require_content_bound_trace=True
        )
        self.assertEqual(valid, [])
        self.assertEqual(rewound, 0)

    def test_record_reordering_invalidates_chain(self):
        r0 = self._record(
            0, runtime._CONTROLLER_TRACE_GENESIS_SHA256, "alpha"
        )
        r1 = self._record(1, r0["record_sha256"], "beta")
        valid, rewound = runtime._validated_checkpoint_prefix(
            [r1, r0], require_content_bound_trace=True
        )
        self.assertEqual(valid, [])
        self.assertEqual(rewound, 0)

    def test_legacy_unbound_trace_remains_valid_when_not_required(self):
        legacy = [{
            "cycle": 0,
            "plan": {"type": "finish", "args": {"summary": "legacy"}},
            "result": {"type": "finish", "summary": "legacy"},
        }]
        valid, rewound = runtime._validated_checkpoint_prefix(
            legacy, require_content_bound_trace=False
        )
        self.assertEqual(valid, legacy)
        self.assertIsNone(rewound)


if __name__ == "__main__":
    unittest.main(verbosity=2)
