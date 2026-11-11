from __future__ import annotations

import unittest

from canonical.runtime.composition_resource_dependency_guard_v1 import (
    ResourceDependencyError,
    validate_resource_dependencies,
)


def finish():
    return {"type": "finish", "args": {"summary": "done"}}


def row(cycle, name, providers=None):
    return {
        "cycle": cycle,
        "capability_id": name,
        "requires": list((providers or {}).keys()),
        "provides": [name + ".done"],
        "result_fields": ["output_path"],
        "provider_bindings": providers or {},
        "requirement_bindings": {},
    }


class CompositionResourceDependencyGuardTests(unittest.TestCase):
    def test_same_path_without_dependency_is_rejected(self):
        actions = [
            {"type": "write_json_records", "args": {"output_path": "canonical/tmp/a.json", "fields": ["v"], "records": [{"v": "x"}]}},
            {"type": "read_file", "args": {"path": "canonical/tmp/a.json"}},
            finish(),
        ]
        contract = [row(0, "writer"), row(1, "reader")]
        with self.assertRaises(ResourceDependencyError):
            validate_resource_dependencies(actions, contract)

    def test_same_path_with_dependency_passes_this_layer(self):
        actions = [
            {"type": "write_json_records", "args": {"output_path": "canonical/tmp/a.json", "fields": ["v"], "records": [{"v": "x"}]}},
            {"type": "read_file", "args": {"path": "canonical/tmp/a.json"}},
            finish(),
        ]
        providers = {"writer.done": {"cycle": 0, "capability_id": "writer"}}
        out = validate_resource_dependencies(actions, [row(0, "writer"), row(1, "reader", providers)])
        self.assertEqual(out["row_count"], 2)
        self.assertIn("RESOURCE_CONTENT_HASH_AND_TYPE_BINDING", out["residuals"])
        self.assertFalse(out["no_bypass_credit"])

    def test_prefix_read_detects_prior_child_write(self):
        actions = [
            {"type": "write_json_records", "args": {"output_path": "canonical/tmp/a.json", "fields": ["v"], "records": [{"v": "x"}]}},
            {"type": "list_tree", "args": {"prefix": "canonical/tmp"}},
            finish(),
        ]
        with self.assertRaises(ResourceDependencyError):
            validate_resource_dependencies(actions, [row(0, "writer"), row(1, "lister")])

    def test_opaque_action_is_blocked(self):
        actions = [{"type": "search_text", "args": {"query": "needle"}}, finish()]
        with self.assertRaises(ResourceDependencyError):
            validate_resource_dependencies(actions, [row(0, "searcher")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
