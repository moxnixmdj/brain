"""Retention cannot be silently dropped or authorize unconfined repair execution."""
from copy import deepcopy
import unittest
from unittest import mock

from canonical.runtime import astra_runtime
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import live_brain_runtime_v1 as runtime
from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound

CID = 'python.software.repair.apply.verified.v1'
CONFIG = {'enabled': True, 'db_path': 'memory/skills.sqlite', 'target_path': 'p/mod.py',
          'contract': {'scope_id': 'test'}, 'context': {}}


class RetainedRepairBoundaryTests(unittest.TestCase):
    def setUp(self):
        _, _, registry = bound._load_registry()
        self.entry = deepcopy(registry[CID])
        self.inputs = {'source_root': 'p', 'test_paths': ['p/test_mod.py'],
                       'test_argv': [], 'synthesize_regression_test': False,
                       'output_path': 'p/report.json', 'retained_learning': deepcopy(CONFIG)}
        self.inspected = {'capability_id': CID, 'entry': self.entry,
                          'registry_file_sha256': 'test', 'registry_entry_sha256': 'test'}

    def test_real_registry_still_requires_independent_verification(self):
        with self.assertRaisesRegex(bound.BoundExecutionError, 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT'):
            bound.prepare(CID, inputs=self.inputs)

    def test_even_if_inspection_later_succeeds_frozen_template_cannot_drop_retention(self):
        with mock.patch.object(bound, 'inspect', return_value=self.inspected):
            with self.assertRaisesRegex(bound.BoundExecutionError, 'RETAINED_LEARNING_NOT_BOUND_BY_FROZEN_TEMPLATE'):
                bound.prepare(CID, inputs=self.inputs)

    def test_a_template_that_binds_retention_preserves_the_exact_config(self):
        # Synthetic template is only a preparation-unit fixture, not a registry change or evidence.
        self.entry['action_template']['args']['retained_learning'] = '${input.retained_learning}'
        with mock.patch.object(bound, 'inspect', return_value=self.inspected):
            prepared = bound.prepare(CID, inputs=self.inputs)
        self.assertEqual(prepared['rendered_action']['args']['retained_learning'], CONFIG)
        self.assertFalse(prepared['execution_authority'])

    def test_current_repair_template_prepares_without_omitted_optional_arguments(self):
        # Inspect is mocked only because the actual registry remains unadmitted.
        required = {'source_root': 'p', 'test_paths': ['p/test_mod.py'], 'output_path': 'p/report.json'}
        frozen = deepcopy(self.entry['action_template'])
        with mock.patch.object(bound, 'inspect', return_value=self.inspected):
            prepared = bound.prepare(CID, inputs=required)
        args = prepared['rendered_action']['args']
        self.assertNotIn('test_argv', args)
        self.assertNotIn('synthesize_regression_test', args)
        self.assertEqual(args['source_root'], 'p')
        self.assertEqual(self.entry['action_template'], frozen)
        self.assertFalse(prepared['execution_authority'])

    def test_candidate_template_binds_opt_in_and_supports_omitted_optional_inputs(self):
        # This is a proposed shape only; mocking inspect supplies no verification.
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        candidate = json.loads((root / 'RETAINED_REPAIR_ACTION_TEMPLATE_CANDIDATE_20261102.json').read_text())
        baseline = deepcopy(self.entry['action_template'])
        self.assertEqual(candidate['status'], 'DRAFT__NOT_ADMITTED__NO_EXECUTION_AUTHORITY')
        self.assertEqual(candidate['basis_action_template_canonical_sha256'], bound._sha(baseline))
        expected = deepcopy(baseline)
        expected['args']['retained_learning'] = '${input.retained_learning}'
        expected['optional'].append('retained_learning')
        self.assertEqual(candidate['candidate_action_template'], expected)
        self.entry['action_template'] = deepcopy(expected)
        required = {'source_root': 'p', 'test_paths': ['p/test_mod.py'], 'output_path': 'p/report.json'}
        with mock.patch.object(bound, 'inspect', return_value=self.inspected):
            without = bound.prepare(CID, inputs=required)
            disabled = bound.prepare(CID, inputs={**required, 'retained_learning': {'enabled': False}})
            enabled = bound.prepare(CID, inputs={**required, 'retained_learning': deepcopy(CONFIG)})
        args = without['rendered_action']['args']
        self.assertNotIn('retained_learning', args)
        self.assertNotIn('test_argv', args)
        self.assertNotIn('synthesize_regression_test', args)
        self.assertEqual(disabled['rendered_action']['args']['retained_learning'], {'enabled': False})
        self.assertEqual(enabled['rendered_action']['args']['retained_learning'], CONFIG)
        self.assertEqual(self.entry['action_template'], expected)  # frozen source not mutated
        self.assertEqual(enabled['inputs'], {**required, 'retained_learning': CONFIG})
        self.assertFalse(enabled['execution_authority'])

    def test_shared_kernel_renderer_has_not_been_changed_to_accept_optional_inputs(self):
        # The candidate is not an admitted contract, and this separate path
        # still does not implement its optional-input behavior.
        from pathlib import Path
        import json
        doc = json.loads((Path(__file__).resolve().parents[2] /
                          'RETAINED_REPAIR_ACTION_TEMPLATE_CANDIDATE_20261102.json').read_text())
        with self.assertRaisesRegex(astra_runtime.Blocker, 'BOUND_CAPABILITY_INPUT_MISSING'):
            astra_runtime._render_bound_template(doc['candidate_action_template'],
                                                 {'source_root': 'p', 'test_paths': [],
                                                  'output_path': 'p/report.json'})

    def test_candidate_rejects_malformed_explicit_retention_before_preparation(self):
        from pathlib import Path
        import json
        root = Path(__file__).resolve().parents[2]
        doc = json.loads((root / 'RETAINED_REPAIR_ACTION_TEMPLATE_CANDIDATE_20261102.json').read_text())
        self.entry['action_template'] = doc['candidate_action_template']
        for bad in (None, {}, {'enabled': 1}, {'enabled': 'false'}, True):
            with self.subTest(bad=bad), mock.patch.object(bound, 'inspect', return_value=self.inspected):
                with self.assertRaisesRegex(bound.BoundExecutionError, 'RETAINED_LEARNING_CONFIG_INVALID'):
                    bound.prepare(CID, inputs={**self.inputs, 'retained_learning': bad})

    def test_optional_input_binding_does_not_drop_required_or_malformed_placeholders(self):
        template = self.entry['action_template']
        required = {'source_root': 'p', 'test_paths': ['p/test_mod.py']}
        with mock.patch.object(bound, 'inspect', return_value=self.inspected):
            with self.assertRaisesRegex(bound.BoundExecutionError, 'BOUND_TEMPLATE_RENDER_FAILED'):
                bound.prepare(CID, inputs=required)
            template['args']['test_argv'] = '${input.some_other_input}'
            with self.assertRaisesRegex(bound.BoundExecutionError, 'BOUND_TEMPLATE_RENDER_FAILED'):
                bound.prepare(CID, inputs={**required, 'output_path': 'p/report.json'})

    def test_a_future_successful_inspection_does_not_authorize_host_execution(self):
        # Inspection is mocked to exercise the *next* gate, not to certify this adapter.
        with mock.patch.object(bound, 'inspect', return_value=self.inspected) as inspect, \
             mock.patch.object(bound, '_receipt_backed_execution') as receipt, \
             mock.patch.object(astra_runtime, '_invoke_bound_capability') as invoke:
            result = bound.execute(CID, inputs={'source_root': 'p'})
        inspect.assert_called()
        receipt.assert_not_called(); invoke.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_fabric_raw_goal_does_not_silently_ignore_retention_configuration(self):
        for container in ('payload', 'options'):
            request = {'mode': 'RAW_GOAL', 'payload': {'task_id': 't', 'goal': 'repair example'},
                       'options': {'learn': True, 'auto_repair': False}}
            request[container]['retained_learning'] = deepcopy(CONFIG)
            with self.subTest(container=container), mock.patch.object(runtime, 'run') as run:
                result = fabric.run(request)
                run.assert_not_called()
                self.assertFalse(result['pass'])
                self.assertIn('RAW_GOAL_RETAINED_LEARNING_UNSUPPORTED', str(result))

    def test_raw_runtime_rejects_unsupported_retention_before_compilation(self):
        for container in ('request', 'outer'):
            request = {'mode': 'raw_bound', 'request': {'task_id': 't', 'goal': 'repair example'}}
            (request['request'] if container == 'request' else request)['retained_learning'] = deepcopy(CONFIG)
            with self.subTest(container=container), mock.patch.object(runtime, '_raw_bound_run') as run:
                result = runtime.run(request)
                run.assert_not_called()
                self.assertFalse(result['pass'])
                self.assertIn('RAW_GOAL_RETAINED_LEARNING_UNSUPPORTED', str(result))

    def test_fabric_rejects_learning_disabled_with_explicit_retained_learning(self):
        request = {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID,
                   'inputs': {'retained_learning': deepcopy(CONFIG)}}, 'options': {'learn': False}}
        with mock.patch.object(fabric, 'execute_bound') as execute:
            result = fabric.run(request)
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertIn('RETAINED_LEARNING_CONFLICTS_WITH_LEARN_FALSE', str(result))

    def test_real_fabric_bound_call_still_fails_gate_before_store_or_execution(self):
        from pathlib import Path
        import tempfile
        root = Path(__file__).resolve().parents[2]
        parent = root / 'canonical/astra_runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repair_gate_', dir=parent) as td:
            db = Path(td) / 'skills.sqlite'
            config = {'enabled': False, 'db_path': db.relative_to(root).as_posix()}
            request = {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID,
                       'inputs': {'retained_learning': config}}, 'options': {'learn': False}}
            with mock.patch.object(astra_runtime, '_invoke_bound_capability') as invoke:
                result = fabric.run(request)
            invoke.assert_not_called()
            self.assertFalse(result['result']['pass'])
            self.assertIn('BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT', result['result']['reason'])
            self.assertFalse(db.exists())

    def test_live_capability_rejects_enabled_retention_when_learning_is_disabled(self):
        from canonical.runtime import live_capability_invoker_v1 as invoker
        request = {'mode': 'LIVE_CAPABILITY', 'payload': {'capability_id': 'bound:' + CID,
                   'capability_payload': {'retained_learning': deepcopy(CONFIG)}},
                   'options': {'learn': False}}
        with mock.patch.object(invoker, 'execute_bound') as execute:
            result = fabric.run(request)
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertIn('RETAINED_LEARNING_CONFLICTS_WITH_LEARN_FALSE', str(result))

    def test_retention_configuration_cannot_be_silently_misplaced(self):
        from canonical.runtime import live_capability_invoker_v1 as invoker
        for mode in ('BOUND_CAPABILITY', 'LIVE_CAPABILITY'):
            payload = ({'capability_id': CID, 'inputs': {}} if mode == 'BOUND_CAPABILITY'
                       else {'capability_id': 'bound:' + CID, 'capability_payload': {}})
            request = {'mode': mode, 'payload': payload,
                       'options': {'learn': False, 'retained_learning': deepcopy(CONFIG)}}
            with self.subTest(mode=mode), mock.patch.object(fabric, 'execute_bound') as direct, \
                 mock.patch.object(invoker, 'execute_bound') as through_invoker:
                result = fabric.run(request)
                direct.assert_not_called(); through_invoker.assert_not_called()
                self.assertFalse(result['pass'])
                self.assertIn('RETAINED_LEARNING_MUST_BE_BOUND_CAPABILITY_INPUT', str(result))

    def test_live_capability_gate_surfaces_same_gap_without_queue(self):
        from pathlib import Path
        import tempfile
        root = Path(__file__).resolve().parents[2]
        parent = root / 'canonical/astra_runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repair_gate_', dir=parent) as td:
            state = str(Path(td) / 'r3.json')
            request = {'mode': 'LIVE_CAPABILITY', 'payload': {'capability_id': 'bound:' + CID,
                       'capability_payload': {'retained_learning': deepcopy(CONFIG)}},
                       'options': {'learn': True, 'state_path': state}}
            with mock.patch.object(runtime, 'observe_runtime_outcome') as observation, \
                 mock.patch.object(fabric.improvement_driver, 'drain') as drain:
                result = fabric.run(request)
            observation.assert_not_called(); drain.assert_not_called()
            out = result['result']
            self.assertFalse(out['pass'])
            self.assertIn('BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT', out['result']['reason'])
            self.assertEqual(out['knowledge_gap']['status'], 'RECORDED')
            self.assertTrue(Path(state + '.ignorance.json').is_file())

    def test_real_fabric_bound_gate_records_one_gap_without_repair_or_queue(self):
        from pathlib import Path
        import tempfile
        root = Path(__file__).resolve().parents[2]
        parent = root / 'canonical/astra_runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repair_gate_', dir=parent) as td:
            state = str(Path(td) / 'r3.json')
            request = {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID,
                       'inputs': {'retained_learning': deepcopy(CONFIG)}},
                       'options': {'learn': True, 'state_path': state}}
            with mock.patch.object(astra_runtime, '_invoke_bound_capability') as invoke, \
                 mock.patch.object(runtime, 'observe_runtime_outcome') as observation, \
                 mock.patch.object(fabric.improvement_driver, 'drain') as drain:
                result = fabric.run(request)
            invoke.assert_not_called(); observation.assert_not_called(); drain.assert_not_called()
            out = result['result']
            self.assertFalse(out['pass'])
            self.assertIn('BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT', out['reason'])
            self.assertEqual(out['knowledge_gap']['status'], 'RECORDED')
            self.assertTrue(Path(state + '.ignorance.json').is_file())
            request['options']['learn'] = False
            request['payload']['inputs']['retained_learning']['enabled'] = False
            before = Path(state + '.ignorance.json').read_bytes()
            again = fabric.run(request)
            self.assertFalse(again['result']['pass'])
            self.assertNotIn('knowledge_gap', again['result'])
            self.assertEqual(Path(state + '.ignorance.json').read_bytes(), before)

    def test_gap_continuity_across_real_fabric_modes_and_fresh_processes(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        from canonical.tests.retained_repair_curriculum_v1 import build_case
        root = Path(__file__).resolve().parents[2]
        parent = root / 'canonical/astra_runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repair_gate_', dir=parent) as td:
            base = Path(td)
            case = build_case(base, 'floor_boundary', 'teaching')
            original = case['target'].read_bytes()
            state = str(base / 'state.json')
            rel = case['project'].relative_to(root).as_posix()
            report = (base / 'report.json').relative_to(root).as_posix()
            goal = 'Fix the failing tests in the python source root ' + rel + ' and write the report to ' + report
            child = '''import json, os, sys
from canonical.runtime.unified_cognitive_fabric_v1 import run
r=run(json.loads(sys.stdin.read()))
print(json.dumps({'pid':os.getpid(), 'result':r.get('result')}))
'''
            env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1',
                       BRAIN_SELF_PREDICTION_LEDGER=str(base / 'calibration.jsonl'))
            requests = [
                {'mode': 'RAW_GOAL', 'payload': {'task_id': 'teach', 'goal': goal},
                 'options': {'learn': True, 'state_path': state}},
                {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID, 'inputs': {}},
                 'options': {'learn': True, 'state_path': state}},
                {'mode': 'LIVE_CAPABILITY', 'payload': {'capability_id': 'bound:' + CID,
                                                       'capability_payload': {}},
                 'options': {'learn': True, 'state_path': state}},
                {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID, 'inputs': {}},
                 'options': {'learn': False, 'state_path': state}},
            ]
            gap_ids, pids = [], set()
            before_disabled = None
            ledger = Path(state + '.ignorance.json')
            for request in requests:
                if request['options']['learn'] is False:
                    before_disabled = ledger.read_bytes()
                proc = subprocess.run([sys.executable, '-B', '-c', child], input=json.dumps(request),
                                      text=True, capture_output=True, cwd=root, env=env,
                                      timeout=45, check=True)
                value = json.loads(proc.stdout); pids.add(value['pid'])
                result = value['result']
                self.assertFalse(result['pass'], result)
                if request['options']['learn']:
                    gap_ids.append(result['knowledge_gap']['gap_id'])
                else:
                    self.assertNotIn('knowledge_gap', result)
                    self.assertEqual(ledger.read_bytes(), before_disabled)
            self.assertEqual(len(pids), 4)
            self.assertEqual(len(set(gap_ids)), 1)
            self.assertEqual(case['target'].read_bytes(), original)
            self.assertFalse((base / 'memory/skills.sqlite').exists())
            self.assertFalse((root / report).exists())

    def test_fabric_allows_disabled_retention_to_reach_unchanged_admission(self):
        request = {'mode': 'BOUND_CAPABILITY', 'payload': {'capability_id': CID,
                   'inputs': {'retained_learning': {'enabled': False}}}, 'options': {'learn': False}}
        with mock.patch.object(fabric, 'execute_bound', return_value={'pass': False, 'status': 'REFUSED'}) as execute:
            result = fabric.run(request)
        execute.assert_called_once()
        self.assertFalse(result['result']['pass'])

    def test_missing_independent_verification_records_gap_without_auto_replay(self):
        from pathlib import Path
        import tempfile
        root = Path(__file__).resolve().parents[2]
        parent = root / 'canonical/astra_runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        refusal = {'pass': False, 'status': 'FAIL__LIVE_CONTROLLER_EXECUTION',
                   'compiled_capability_id': CID,
                   'reason': 'Blocker:BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:' + CID}
        with tempfile.TemporaryDirectory(prefix='repair_gap_', dir=parent) as td:
            state = str(Path(td) / 'r3.json')
            request = {'mode': 'RAW_GOAL', 'payload': {'task_id': 't', 'goal': 'repair example'},
                       'options': {'learn': True, 'state_path': state}}
            with mock.patch.object(live, '_run_raw_goal_impl', return_value=refusal), \
                 mock.patch.object(live, '_advance_learning_queue') as raw_queue, \
                 mock.patch.object(live, '_record_raw_goal_failure_diagnosis') as diagnosis, \
                 mock.patch.object(runtime, '_observe_runtime_outcome') as observation, \
                 mock.patch.object(runtime, 'execute_failure_repair_cycle') as repair, \
                 mock.patch.object(fabric.improvement_driver, 'drain') as drain:
                result = fabric.run(request)
            raw_queue.assert_not_called(); diagnosis.assert_not_called(); observation.assert_not_called()
            repair.assert_not_called(); drain.assert_not_called()
            self.assertFalse(result['result']['pass'])
            self.assertEqual(result['result']['knowledge_gap']['status'], 'RECORDED')
            self.assertTrue(Path(state + '.ignorance.json').is_file())

    def test_even_a_preexisting_repair_diagnosis_cannot_override_gate_refusal(self):
        refusal = {'pass': False, 'compiled_capability_id': CID,
                   'reason': 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:' + CID}
        wrapped = {'pass': False, 'raw_result': refusal,
                   'learning': {'pass': False, 'diagnosis': {'failure_fingerprint': 'x'},
                                'retry_capsule_sha256': 'y'}}
        with mock.patch.object(runtime, 'execute_failure_repair_cycle') as repair:
            result = runtime._auto_repair_live_failure(wrapped, {'mode': 'raw_bound'},
                         repo_root='.', information_provider=None, proposal_provider=None,
                         capability_expander=None)
        repair.assert_not_called()
        self.assertFalse(result['pass'])

    def test_raw_action_plan_is_preflighted_before_any_repair_step(self):
        actions = [{'type': 'invoke_capability', 'args': {'capability_id': 'first'}},
                   {'type': 'invoke_capability', 'args': {'capability_id': CID}}]
        compiled = {'controller_actions': actions, 'target_effects': ['repair']}
        with mock.patch.object(live, 'compile_against_live_registry', return_value=({}, {CID: self.entry}, compiled)), \
             mock.patch.object(live, 'drive_controller') as controller:
            result = live.run_raw_goal({'task_id': 't', 'goal': 'repair example'}, record_experience=False)
        controller.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_composer_preflights_repair_before_earlier_steps(self):
        from canonical.runtime import composer_route_v1 as composer
        registry = {'first': {'adapter_module': 'text_file_write'}, CID: self.entry}
        with mock.patch.object(door, 'run_adapter_locally') as dispatch:
            result = composer.execute_chain(['first', CID], 'repair', registry=registry)
        dispatch.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])
        self.assertEqual(result['steps'], [])

    def test_repair_path_alias_is_refused_before_adapter_import(self):
        entry = {'adapter_module': 'alternate_name', 'source': {'adapter_path':
                 './canonical/runtime/bound_capabilities/../bound_capabilities/python_repair_apply_verified_v1.py'}}
        with mock.patch.object(door.importlib.util, 'spec_from_file_location') as loader:
            with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                door.run_adapter_locally(entry, {'args': {}})
        loader.assert_not_called()

    def test_local_dispatch_refuses_the_known_repair_adapter(self):
        with mock.patch.object(door.importlib.util, 'spec_from_file_location') as loader:
            with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                door.run_adapter_locally(dict(self.entry, capability_id=CID), {'args': {}})
        loader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
