"""Content identity across existing candidate acceptance and public publication.

Explicit operator composition, not a new atomic publication API or independent benchmark.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from canonical.tests.test_public_delivery_measured_acceptance_chain_reuse_v1 import FILES, CONTRACT
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import python_request_acceptance_union_v1 as union
from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as controller
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement

ROOT = Path(__file__).resolve().parents[2]


class AcceptedCandidateDeliveryIdentityReuseTests(unittest.TestCase):
    def test_accepted_snapshot_matches_public_delivery_then_final_acceptance(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',
                                         prefix='accepted_delivery_identity_') as directory:
            base = Path(directory)
            source = base/'candidate'
            source.mkdir()
            for name,text in FILES.items():
                path = source/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            baseline = base/'baseline'
            shutil.copytree(source,baseline)
            original = measurement._tree_manifest(source,max_files=100,max_bytes=1_000_000)
            accepted = controller.run({'source_root':'candidate','task_text':CONTRACT,
                                       'test_paths':['candidate/tests/test_checkout.py'],
                                       'output_path':'accepted.json','timeout_s':5,
                                       'mutations_per_file':12,'max_pair_candidates':300},base)
            self.assertTrue(accepted['acceptance_stop_authorized'],accepted)
            self.assertEqual(accepted['baseline_snapshot_sha256'],original[1])
            self.assertEqual(measurement._tree_manifest(source,max_files=100,max_bytes=1_000_000),original)
            relative = source.relative_to(ROOT).as_posix()
            report = (base/'published.json').relative_to(ROOT).as_posix()
            goal = (f'Repair the python source root {relative} so the unit tests in '
                    f'{relative}/tests/test_checkout.py pass, apply the fix in place, '
                    f'and save the repair report to {report}.')
            delivered = door.solve({'task_id':base.name,'goal':goal})
            self.assertTrue(delivered['pass'],delivered.get('status'))
            self.assertIs(delivered['executed'],True)
            self.assertFalse(delivered['semantic_acceptance_complete'])
            publication = json.loads((base/'published.json').read_text())
            self.assertTrue(publication['applied'])
            self.assertEqual(len(publication['files_written']),2)
            final = measurement._tree_manifest(source,max_files=100,max_bytes=1_000_000)
            # Passing tests alone is insufficient: require exact accepted tree identity.
            self.assertEqual(final[1],accepted['candidate_subject_snapshot_sha256'])
            for patch in accepted['realized_patches']:
                import hashlib
                self.assertEqual(hashlib.sha256((source/patch['candidate_relative_path']).read_bytes()).hexdigest(),
                                 patch['candidate_sha256'])

            def measure():
                return measurement.run({'source_root':'candidate',
                                        'test_paths':['tests/test_checkout.py'],
                                        'output_path':'final-measurement.json','timeout_s':5},base)

            def accept_final():
                return union.evaluate_union(CONTRACT,measurement_receipt_path='final-measurement.json',
                                            receipt_root=base,baseline_root=baseline,candidate_root=source,
                                            expected_baseline_snapshot_sha256=original[1])

            measured = measure()
            self.assertTrue(measured['measurements']['tests_pass'])
            self.assertEqual(measured['subject']['snapshot_sha256'],final[1])
            self.assertTrue(accept_final()['acceptance_stop_authorized'])
            settings = source/'settings.json'
            settings.write_text('{"preserve":"unauthorized change"}\n')
            with self.subTest(control='old receipt cannot authorize changed delivery'):
                rejected = accept_final()
                self.assertFalse(rejected['acceptance_stop_authorized'])
                self.assertEqual(rejected['status'],'FAIL_CLOSED')
                self.assertIn('CANDIDATE_SNAPSHOT_MISMATCH',str(rejected['errors']))
            with self.subTest(control='new passing tests cannot erase preservation requirement'):
                remeasured = measure()
                self.assertTrue(remeasured['measurements']['tests_pass'])
                rejected = accept_final()
                self.assertFalse(rejected['acceptance_stop_authorized'])
                self.assertTrue(rejected['failed_obligation_ids'])
            settings.write_text(FILES['settings.json'])
            self.assertEqual(measurement._tree_manifest(source,max_files=100,max_bytes=1_000_000),final)
            self.assertTrue(measure()['measurements']['tests_pass'])
            self.assertTrue(accept_final()['acceptance_stop_authorized'])
            self.assertEqual(measurement._tree_manifest(baseline,max_files=100,max_bytes=1_000_000),original)
