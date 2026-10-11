from __future__ import annotations

import unittest

from canonical.runtime.pure_projection_consumer_guard_v1 import (
    PureProjectionConsumerError,
    evaluate_pure_consumer,
    verify_source,
)


GOOD = """
def helper(x):
    if x > 7:
        return x - 1
    return x

def evaluate(projection):
    proved = projection["sources"][0]["projection"]["/authority/proved"]
    open_count = projection["sources"][0]["projection"]["/authority/open"]
    return {
        "still_valid": helper(proved) == 7 and open_count == 12,
        "count": len(projection["sources"]),
    }
"""


class PureProjectionConsumerGuardTests(unittest.TestCase):
    def projection(self):
        return {
            "sources": [
                {
                    "projection": {
                        "/authority/proved": 8,
                        "/authority/open": 12,
                    }
                }
            ]
        }

    def assert_rejected(self, source, marker):
        with self.assertRaises(PureProjectionConsumerError) as ctx:
            verify_source(source)
        self.assertIn(marker, str(ctx.exception))

    def test_valid_consumer_executes_from_projection_only(self):
        out = evaluate_pure_consumer(
            source=GOOD,
            projection=self.projection(),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["consumer_result"]["still_valid"])
        self.assertEqual(out["consumer_result"]["count"], 1)
        self.assertFalse(out["ambient_repository_access_available"])
        self.assertFalse(out["filesystem_access_available"])
        self.assertFalse(out["network_access_available"])
        self.assertFalse(out["process_access_available"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_import_is_rejected(self):
        self.assert_rejected(
            "import os\ndef evaluate(projection):\n    return {}\n",
            "MODULE_BODY_MUST_CONTAIN_ONLY_FUNCTIONS",
        )

    def test_open_is_rejected_as_unknown_global(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    x = open('/tmp/x')\n"
            "    return {'x': x}\n",
            "UNKNOWN_GLOBAL_NAME:evaluate:open",
        )

    def test_attribute_access_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return {'x': projection.get('x')}\n",
            "AST_NODE_FORBIDDEN:evaluate:Attribute",
        )

    def test_globals_introspection_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return {'x': globals()}\n",
            "CALL_TARGET_FORBIDDEN:evaluate:globals",
        )

    def test_dunder_name_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return {'x': __builtins__}\n",
            "DUNDER_NAME_FORBIDDEN:evaluate:__builtins__",
        )

    def test_for_loop_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    total = 0\n"
            "    for x in projection['xs']:\n"
            "        total = total + x\n"
            "    return {'total': total}\n",
            "AST_NODE_FORBIDDEN:evaluate:For",
        )

    def test_comprehension_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return {'x': [v for v in projection['xs']]}\n",
            "AST_NODE_FORBIDDEN:evaluate:ListComp",
        )

    def test_recursive_local_call_graph_is_rejected(self):
        self.assert_rejected(
            "def f(x):\n"
            "    return f(x)\n"
            "def evaluate(projection):\n"
            "    return {'x': f(1)}\n",
            "LOCAL_CALL_GRAPH_CYCLE:f",
        )

    def test_subscript_mutation_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    projection['x'] = 1\n"
            "    return {'x': 1}\n",
            "ASSIGN_TARGET_MUST_BE_LOCAL_NAME",
        )

    def test_dynamic_call_target_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return projection['fn']()\n",
            "CALL_TARGET_MUST_BE_NAME:evaluate",
        )

    def test_unknown_global_is_rejected(self):
        self.assert_rejected(
            "def evaluate(projection):\n"
            "    return {'x': secret}\n",
            "UNKNOWN_GLOBAL_NAME:evaluate:secret",
        )

    def test_non_mapping_result_fails_closed(self):
        out = evaluate_pure_consumer(
            source="def evaluate(projection):\n    return 1\n",
            projection=self.projection(),
        )
        self.assertFalse(out["pass"])
        self.assertIn("CONSUMER_RESULT_MUST_BE_MAPPING", out["error"])

    def test_non_json_result_fails_closed(self):
        out = evaluate_pure_consumer(
            source=(
                "def evaluate(projection):\n"
                "    return {'x': set([1, 2])}\n"
            ),
            projection=self.projection(),
        )
        self.assertFalse(out["pass"])
        self.assertIn("TypeError", out["error"])

    def test_projection_is_json_re_materialized(self):
        class Evil(dict):
            @property
            def leak(self):
                raise AssertionError("must not be observable")

        projection = Evil(self.projection())
        out = evaluate_pure_consumer(source=GOOD, projection=projection)
        self.assertTrue(out["pass"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
