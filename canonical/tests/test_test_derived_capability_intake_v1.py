from __future__ import annotations

import pathlib
import unittest

from canonical.runtime import test_derived_capability_intake_v1 as intake
from canonical.runtime.live_brain_route_admission_v1 import (
    _ROOT_PARAM_NAMES,
    LocalExecutionFailure,
    _invoke_entrypoint,
    run_adapter_locally,
)

EXAMPLE = "aa_briefcase_internal_only_certification_gate_v3"


def _payload() -> dict:
    from canonical.tests import test_aa_briefcase_internal_only_certification_gate_v3 as t

    x = t.base()
    x["score_trace_substitution_route"]["candidate_literal_floor_ge_1822"] = t.floor_proof(1822.0)
    return x


class InvokeEntrypointTests(unittest.TestCase):
    def test_kernel_adapter_convention_args_then_root(self):
        seen = {}

        def run(args, root):
            seen.update(args=args, root=root)
            return {"ok": True}

        out = _invoke_entrypoint(run, {"a": 1}, "/the/root")
        self.assertEqual(out, {"ok": True})
        self.assertEqual(seen, {"args": {"a": 1}, "root": "/the/root"})

    def test_single_payload_entrypoint(self):
        def evaluate(payload):
            return {"got": payload}

        self.assertEqual(_invoke_entrypoint(evaluate, {"x": 2}, "/r"), {"got": {"x": 2}})

    def test_root_only_entrypoint_receives_root_not_payload(self):
        def verify(repo_root):
            return {"root": str(repo_root)}

        self.assertEqual(_invoke_entrypoint(verify, {}, "/r"), {"root": "/r"})

    def test_payload_then_root_entrypoint(self):
        def evaluate(payload, repo_root):
            return {"p": payload, "r": str(repo_root)}

        self.assertEqual(_invoke_entrypoint(evaluate, {"k": 1}, "/r"), {"p": {"k": 1}, "r": "/r"})

    def test_zero_arg_entrypoint(self):
        def manifest():
            return {"manifest": True}

        self.assertEqual(_invoke_entrypoint(manifest, {}, "/r"), {"manifest": True})

    def test_optional_extra_parameter_keeps_its_default(self):
        def evaluate(payload, strict=True):
            return {"strict": strict, "payload": payload}

        self.assertEqual(_invoke_entrypoint(evaluate, {"q": 1}, "/r"), {"strict": True, "payload": {"q": 1}})

    def test_two_payload_parameters_fail_closed(self):
        def verify(problem, result):
            return {}

        with self.assertRaisesRegex(LocalExecutionFailure, "SIGNATURE_UNSUPPORTED"):
            _invoke_entrypoint(verify, {"a": 1}, "/r")

    def test_payload_into_root_only_entrypoint_fails_closed(self):
        def verify(repo_root):
            return {}

        with self.assertRaisesRegex(LocalExecutionFailure, "TAKES_NO_PAYLOAD"):
            _invoke_entrypoint(verify, {"a": 1}, "/r")

    def test_root_param_names_stay_in_sync_with_the_admission_module(self):
        self.assertEqual(set(intake.ROOT_PARAM_NAMES), set(_ROOT_PARAM_NAMES))


class ClassifierTests(unittest.TestCase):
    def test_result_success_mirrors_tool_truth(self):
        self.assertTrue(intake.result_success({"status": "PASS_X"}))
        self.assertTrue(intake.result_success({"pass": True}))
        self.assertFalse(intake.result_success({"pass": False}))
        self.assertFalse(intake.result_success({"status": "OPEN__X"}))
        self.assertFalse(intake.result_success({"status": "FAIL__X"}))
        self.assertFalse(intake.result_success(["not", "a", "mapping"]))

    def test_bindable_shapes(self):
        base = {"entrypoint": "evaluate", "param_names": ["payload"], "kwargs": {}}
        ok, shape = intake._bindable({**base, "args": [{"a": 1}], "result": {"pass": True}})
        self.assertTrue(ok)
        self.assertEqual(shape, "PAYLOAD")
        ok, shape = intake._bindable({"entrypoint": "verify", "param_names": ["repo_root"],
                                      "kwargs": {}, "args": ["/tmp/x"], "result": {"pass": True}})
        self.assertTrue(ok)
        self.assertEqual(shape, "ROOT_ONLY")
        ok, shape = intake._bindable({"entrypoint": "run", "param_names": ["args", "root"],
                                      "kwargs": {}, "args": [{"a": 1}, "/tmp/x"], "result": {"pass": True}})
        self.assertTrue(ok)
        self.assertEqual(shape, "PAYLOAD_ROOT")
        ok, shape = intake._bindable({"entrypoint": "manifest", "param_names": [],
                                      "kwargs": {}, "args": [], "result": {"pass": True}})
        self.assertTrue(ok)
        self.assertEqual(shape, "NONE")

    def test_unbindable_rejections(self):
        base = {"entrypoint": "evaluate", "param_names": ["payload"], "kwargs": {}}
        self.assertEqual(intake._bindable({**base, "args": None, "result": {"pass": True}})[1], "UNSNAPSHOTABLE_ARGUMENTS")
        self.assertEqual(intake._bindable({**base, "args": [{"a": 1}], "kwargs": None, "result": {"pass": True}})[1], "UNSNAPSHOTABLE_ARGUMENTS")
        self.assertEqual(intake._bindable({**base, "args": [{"a": 1}], "kwargs": {"x": 1}, "result": {"pass": True}})[1], "KEYWORD_ARGUMENTS")
        self.assertEqual(intake._bindable({**base, "args": [{"a": 1}], "result": {"pass": False}})[1], "RESULT_NOT_SUCCESS")
        self.assertEqual(intake._bindable({**base, "args": [{"a": 1}], "result": ["x"]})[1], "RESULT_NOT_MAPPING")
        self.assertEqual(intake._bindable({**base, "args": [{"a": 1}], "result": None})[1], "RESULT_NOT_MAPPING")
        self.assertEqual(intake._bindable({**base, "args": ["${input.foo}"], "result": {"pass": True}})[1], "ARGUMENT_SHAPE_UNSUPPORTED")
        self.assertEqual(intake._bindable({**base, "args": [{"k": "${input.foo}"}], "result": {"pass": True}})[1],
                         "PAYLOAD_CONTAINS_TEMPLATE_MARKERS")

    def test_select_binding_prefers_pass_true_then_entrypoint_priority(self):
        calls = [
            {"entrypoint": "verify", "param_names": ["payload"], "kwargs": {}, "args": [{"a": 1}],
             "result": {"status": "PASS_VERIFY"}},
            {"entrypoint": "evaluate", "param_names": ["payload"], "kwargs": {}, "args": [{"b": 2}],
             "result": {"pass": True, "status": "PASS_EVAL"}},
        ]
        binding = intake.select_binding(calls)
        self.assertEqual(binding["entrypoint"], "evaluate")
        self.assertEqual(binding["payload"], {"b": 2})
        self.assertTrue(intake.result_pass_true(binding["result"]))


class DirectInvocationTests(unittest.TestCase):
    """The real example module, executed exactly as the live route executes it."""

    def _entry(self, **extra):
        rel = "canonical/runtime/" + EXAMPLE + ".py"
        entry = {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "source": {"type": "repository_python_source", "path": rel, "adapter_path": rel, "modules": []},
            "adapter_module": EXAMPLE,
            "entrypoint": "evaluate",
            "incremental_spend_usd": 0,
        }
        entry.update(extra)
        return entry

    def test_run_adapter_locally_executes_one_arg_entrypoint(self):
        action = {"args": _payload(), "expect": {"type": "field_equals", "field": "pass", "value": True}}
        result = run_adapter_locally(self._entry(), action)
        self.assertTrue(result["pass"])
        self.assertEqual(result["status"], "PASS_INTERNAL_ONLY")
        self.assertEqual(result["dependency"]["executor"], "FRONT_LAYER_LOCAL_ADAPTER_EXECUTION_V1")

    def test_module_and_entrypoint_are_derived_when_undeclared(self):
        rel = "canonical/runtime/" + EXAMPLE + ".py"
        entry = {"source": {"adapter_path": rel, "modules": []}, "incremental_spend_usd": 0}
        result = run_adapter_locally(entry, {"args": _payload()})
        self.assertTrue(result["pass"])

    def test_expectation_failure_still_fails_closed(self):
        action = {"args": _payload(), "expect": {"type": "field_equals", "field": "pass", "value": False}}
        with self.assertRaisesRegex(LocalExecutionFailure, "ACTION_EXPECTATION_FAILED"):
            run_adapter_locally(self._entry(), action)

    def test_nonzero_declared_cost_is_rejected(self):
        with self.assertRaisesRegex(LocalExecutionFailure, "NONZERO_COST"):
            run_adapter_locally(self._entry(incremental_spend_usd=0.01), {"args": _payload()})


class IntakePipelineTests(unittest.TestCase):
    def test_paired_stems_finds_the_example_and_excludes_self(self):
        stems = intake.paired_stems(pathlib.Path(intake.ROOT))
        self.assertIn(EXAMPLE, stems)
        self.assertNotIn(intake.SELF_STEM, stems)

    def test_example_pair_is_promotable_with_matching_replay(self):
        row = intake.intake_stem(EXAMPLE)
        self.assertEqual(row["status"], "PROMOTABLE", row)
        self.assertEqual(row["tests"]["failed"], 0)
        self.assertGreaterEqual(row["tests"]["executed"], 1)
        self.assertTrue(row["entry"]["verification"]["front_local_replay"]["ok"])
        self.assertTrue(row["entry"]["verification"]["front_local_replay"]["matches_capture"])
        self.assertEqual(row["entry"]["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(row["entry"]["incremental_spend_usd"], 0)
        template_args = {k: v for k, v in row["entry"]["action_template"]["args"].items() if k != "capability_id"}
        self.assertEqual(intake._sha(template_args), row["capture"]["input_sha256"])
        self.assertEqual(row["entry"]["verification"]["routing_sentinel"], "capability_id")

    def test_action_template_expects_the_captured_success(self):
        row = intake.intake_stem(EXAMPLE)
        self.assertEqual(row["entry"]["action_template"]["expect"],
                         {"type": "field_equals", "field": "pass", "value": True})


class SentenceReachabilityTests(unittest.TestCase):
    def test_bindable_key_detection(self):
        payload = {
            "text": "hello",
            "source_path": "canonical/x.py",
            "objective": {"a": 1},
            "target": "not-a-known-key",
            "external_help_allowed": False,
            "nested": {"text": "inner"},
        }
        self.assertEqual(sorted(intake._sentence_bindable_keys(payload)),
                         ["objective", "source_path", "text"])

    def test_parameterization_round_trips_and_marks_routable(self):
        payload = {"text": "hello world", "frozen": {"proof": 1}, "n": 3}
        entry = {
            "action_template": {"type": "invoke_capability", "args": dict(payload)},
            "verification": {"verified": True},
        }
        keys = intake.parameterize_action_template(entry, payload)
        self.assertEqual(keys, ["text"])
        self.assertEqual(entry["action_template"]["args"]["text"], "${input.text}")
        self.assertEqual(entry["action_template"]["args"]["frozen"], {"proof": 1})
        self.assertEqual(entry["action_template"]["args"]["capability_id"], "${input.capability_id}")
        self.assertEqual(entry["verification"]["routing_sentinel"], "capability_id")
        self.assertTrue(entry["verification"]["template_roundtrip_ok"])

    def test_parameterization_reverts_keys_but_keeps_sentinel(self):
        payload = {"text": "hello", "nested": {"v": "${input.text}"}}
        entry = {
            "action_template": {"type": "invoke_capability", "args": dict(payload)},
            "verification": {"verified": True},
        }
        keys = intake.parameterize_action_template(entry, payload)
        self.assertEqual(keys, [])
        self.assertEqual(entry["action_template"]["args"]["text"], "hello")
        self.assertEqual(entry["action_template"]["args"]["nested"], {"v": "${input.text}"})
        self.assertEqual(entry["action_template"]["args"]["capability_id"], "${input.capability_id}")
        self.assertEqual(entry["verification"]["sentence_input_keys"], [])

    def test_sentinel_never_overwrites_a_payload_owned_capability_id(self):
        payload = {"capability_id": "owned", "x": 1}
        entry = {
            "action_template": {"type": "invoke_capability", "args": dict(payload)},
            "verification": {"verified": True},
        }
        keys = intake.parameterize_action_template(entry, payload)
        self.assertEqual(keys, [])
        self.assertEqual(entry["action_template"]["args"]["capability_id"], "owned")
        self.assertNotIn("routing_sentinel", entry["verification"])


class SentinelRankingTests(unittest.TestCase):
    def _registry(self):
        entry = {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "provides": ["future.matched.scope.nontransport"],
            "requires": [],
            "keywords": ["future", "matched", "scope", "nontransport"],
            "action_template": {
                "type": "invoke_capability",
                "args": {"objective": "${input.objective}", "capability_id": "${input.capability_id}"},
                "expect": {"type": "field_equals", "field": "pass", "value": True},
            },
        }
        return {"canonical/runtime/future_matched_scope_nontransport_v1.py.auto.v1": entry}

    def test_unstated_sentinel_never_ranks(self):
        from canonical.runtime import goal_front_compiler_v1 as front

        ranked = front.ranked_candidates(
            "Apply the future matched scope nontransport capability", self._registry())
        self.assertEqual(ranked, [])

    def test_stated_sentinel_ranks_first(self):
        from canonical.runtime import goal_front_compiler_v1 as front

        goal = ('Apply the future matched scope nontransport capability '
                'with objective "x" and capability_id "intake"')
        ranked = front.ranked_candidates(goal, self._registry())
        self.assertTrue(ranked)
        self.assertTrue(ranked[0][2].endswith("future_matched_scope_nontransport_v1.py.auto.v1"))

    def test_canonical_templates_without_sentinel_rank_unaffected(self):
        from canonical.runtime import goal_front_compiler_v1 as front

        entry = dict(self._registry())
        cid = next(iter(entry))
        entry[cid] = {**entry[cid], "action_template": {"type": "invoke_capability",
                                                        "args": {"objective": "${input.objective}"}}}
        ranked = front.ranked_candidates("Apply the future matched scope nontransport capability", entry)
        self.assertTrue(ranked)


if __name__ == "__main__":
    unittest.main()
