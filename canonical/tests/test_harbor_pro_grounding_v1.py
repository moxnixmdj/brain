"""Local filesystem and mocked model-seam tests; no Docker or benchmark claim."""
from __future__ import annotations

import asyncio
import base64
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import brain_unified_model_v1 as brain
from canonical.runtime import harbor_container_solver_worker_v1 as worker
from canonical.runtime import harbor_epistemic_agent_v1 as agent
from canonical.runtime import harbor_pro_grounding_v1 as grounder


class ProGroundingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.put('src/user/picture.js', 'User.removeCoverPicture = async function(uid) {};\n')
        self.put('test/picture.test.js', 'throw new Error("must not run");\n')
        self.put('pkg/thing.py', 'def repair(): return 1\n')
        self.put('tests/test_thing.py', 'raise RuntimeError("must not run")\n')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')

    def test_multilanguage_paths_tests_and_runners_are_only_hints(self):
        issue = ('In src/user/picture.js, User.removeCoverPicture(uid) must clean up. '
                 'Add the interface in lib/ansible/modules/mount_facts.py.')
        out = grounder.ground(issue, str(self.root))
        self.assertEqual(out['status'], 'OBSERVED__UNVERIFIED')
        self.assertEqual(out['authority'], 'NONE__ADVISORY_ONLY')
        self.assertEqual(out['explicit_paths'], [
            {'path': 'lib/ansible/modules/mount_facts.py', 'status': 'MISSING_OR_PARENT_MISSING'},
            {'path': 'src/user/picture.js', 'status': 'EXISTING_REGULAR_FILE'},
        ])
        self.assertIn('User.removeCoverPicture', out['mentioned_symbols'])
        self.assertEqual(out['test_candidates'], ['test/picture.test.js', 'tests/test_thing.py'])
        self.assertEqual(set(out['runners_on_path']), set(grounder.RUNNERS))
        self.assertFalse(out['tests_run'])
        self.assertFalse(out['repair_verified'])
        self.assertFalse((self.root / 'lib').exists())
        self.assertEqual(out['python_localization']['authority'], 'NONE__ADVISORY_ONLY')

    def test_python_ranked_localizer_is_reused_without_authority(self):
        out = grounder.ground('pkg/thing.py function repair fails; tests/test_thing.py', str(self.root))
        hints = out['python_localization']
        self.assertEqual(hints['status'], 'ADVISORY_CANDIDATES')
        self.assertEqual(hints['authority'], 'NONE__ADVISORY_ONLY')
        self.assertEqual(hints['target_paths'][0]['path'], 'pkg/thing.py')
        self.assertFalse(out['tests_run'])

    def test_symlink_and_unsafe_paths_not_followed(self):
        (self.root / 'outside').symlink_to('/etc', target_is_directory=True)
        (self.root / 'linked.js').symlink_to(self.root / 'src/user/picture.js')
        out = grounder.ground('outside/passwd.js linked.js ../evil.js /tmp/evil.js', str(self.root))
        paths = {p['path']: p['status'] for p in out['explicit_paths']}
        self.assertEqual(paths['outside/passwd.js'], 'UNSAFE_OR_UNREADABLE')
        self.assertEqual(paths['linked.js'], 'NOT_REGULAR_FILE')
        self.assertEqual(paths['../evil.js'], 'UNSAFE_PATH')
        self.assertEqual(paths['/tmp/evil.js'], 'UNSAFE_PATH')
        self.assertNotIn('outside/passwd.js', out['test_candidates'])

    def test_limits_are_explicit_and_no_test_is_executed(self):
        with patch.object(grounder, 'MAX_ENTRIES', 1):
            out = grounder.ground('Find tests.', str(self.root))
        self.assertFalse(out['test_inventory_complete'])
        self.assertFalse(out['tests_run'])
        self.assertEqual(grounder.ground('x' * (grounder.MAX_ISSUE_CHARS + 1), str(self.root))['reason'],
                         'INSTRUCTION_EMPTY_OR_TOO_LARGE')
        self.assertEqual(grounder.ground('Issue', '/')['reason'], 'WORKSPACE_INVALID')
        self.assertEqual(grounder.ground('Issue', str(self.root / 'missing'))['reason'], 'WORKSPACE_UNAVAILABLE')

    def test_first_cycle_uses_imported_engines_instead_of_open_model(self):
        issue = 'src/user/picture.js: call User.removeCoverPicture(uid).'
        request = {'goal': 'goal', 'mode': 'EPISTEMIC', 'inputs': {
            'harbor_suite': 'pro-v2', 'harbor_task': issue,
            'harbor_repo': str(self.root), 'observations': []}}
        token = base64.b64encode(json.dumps(request).encode()).decode()

        class BombModel:
            def solve(self, goal, **kwargs):
                raise AssertionError('ordinary open_model route must not run first')

        stdout = io.StringIO()
        with patch.object(worker.sys, 'argv', ['worker', token]), \
             patch.object(brain, 'open_model', return_value=BombModel()), redirect_stdout(stdout):
            self.assertEqual(worker.main(), 0)
        response = json.loads(stdout.getvalue().removeprefix(worker.MARKER))
        self.assertTrue(response['pass'])
        self.assertEqual([a['type'] for a in response['actions']], ['finish'])
        self.assertEqual(response['proposal_source'], 'DETERMINISTIC_IMPORTED_ENGINES_V1')
        self.assertTrue(response['official_verifier_expected'])
        self.assertFalse(response['task_completion_claimed'])

        class MockEnvironment:
            async def exec(self, command, **kwargs):
                return SimpleNamespace(returncode=0, stdout=worker.MARKER + json.dumps(response), stderr='')

        trace = asyncio.run(agent.run_epistemic_goal(issue, MockEnvironment(), suite='pro-v2', repo=str(self.root)))
        self.assertEqual(trace['status'], 'FINISHED__DETERMINISTIC_PROPOSAL__VERIFIER_DECIDES')
        self.assertEqual(trace['trace'][0]['proposed_actions'], ['finish'])
        self.assertEqual(trace['trace'][0]['imported_engine']['language'], 'javascript_typescript')
        self.assertFalse(trace['task_completion_claimed'])


if __name__ == '__main__':
    unittest.main()
