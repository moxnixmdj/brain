"""A command-containing DAG must be refused before any step or kernel retry."""
import time
import unittest
from unittest import mock

from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import live_brain_route_admission_v1 as door


class LocalCliDagConfinementGuardTests(unittest.TestCase):
    def setUp(self):
        self.compiled = {'capability_dag': {'steps': [
            {'capability_id': 'first', 'action': {'args': {}}},
            {'capability_id': 'command', 'action': {'args': {}}}]}}
        self.registry = {'first': {'adapter_module': 'some_other_adapter'},
                         'command': {'adapter_module': 'cli_command'}}
        self.contract = {'task_sha256': 'a', 'task_contract_sha256': 'b',
                         'acceptance_contract': {'obligations': []}}

    def test_local_plan_refuses_before_first_step(self):
        with mock.patch.object(door, 'run_adapter_locally', return_value={'ok': True}) as run:
            result = door.execute_capability_plan_locally('T', 'task', self.compiled, self.registry,
                                                           self.contract, time.perf_counter_ns())
        run.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])
        self.assertEqual(result['execution'], [])

    def test_kernel_retry_cannot_override_local_boundary_refusal(self):
        with mock.patch.object(door, 'run_adapter_locally', return_value={'ok': True}) as run, \
             mock.patch.object(door, 'dag_executor', return_value='OTHER') as choose, \
             mock.patch.object(door.astra_runtime, 'run_goal') as kernel:
            result = door._execute_capability_dag('T', 'task', self.compiled, self.registry,
                                                  self.contract, time.perf_counter_ns())
        run.assert_not_called(); choose.assert_not_called(); kernel.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])


if __name__ == '__main__':
    unittest.main()
