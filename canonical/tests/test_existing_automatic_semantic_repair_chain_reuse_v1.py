"""Exercise existing automated repair/acceptance, not a new runtime or publication path."""
import json
from pathlib import Path
import tempfile
import pytest
from canonical.tests.test_public_delivery_measured_acceptance_chain_reuse_v1 import FILES, CONTRACT
from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as controller
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement


@pytest.mark.parametrize('extra,accepted,reason', [
    ('', True, None),
    (' File "rules/age.py" must contain "impossible_marker".', False, 'failed_obligation_ids'),
    (' Preserve compatibility with historic clients.', False, 'unbound_obligation_ids'),
    (' Must not modify "rules/age.py".', False, 'failed_obligation_ids'),
], ids=['complete-contract','false-source-requirement','unsupported-requirement','forbidden-repair'])
def test_existing_controller_derives_suite_repairs_pair_and_measures_all_requirements(extra, accepted, reason):
    with tempfile.TemporaryDirectory(prefix='automatic_semantic_reuse_') as directory:
        root = Path(directory)
        source = root/'candidate'
        source.mkdir()
        for name, text in FILES.items():
            path = source/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        original = measurement._tree_manifest(source, max_files=100, max_bytes=1_000_000)
        # Reuse existing suite derivation; no operator-supplied argv or new composer.
        result = controller.run({'source_root':'candidate', 'task_text':CONTRACT+extra,
                                 'test_paths':['candidate/tests/test_checkout.py'],
                                 'output_path':'report.json', 'timeout_s':5,
                                 'mutations_per_file':12, 'max_pair_candidates':300}, root)
        assert result['repair_pass'] is True, result
        assert result['pass'] is accepted, result
        assert result['acceptance_stop_authorized'] is accepted
        assert result['source_restored'] is True
        assert result['measured_fields']['tests_pass'] is True
        assert result['winner_mode'] == 'COUPLED_PAIR_GUIDED'
        assert {p['candidate_relative_path'] for p in result['realized_patches']} == {
            'rules/age.py', 'rules/funds.py'}
        assert result['baseline_snapshot_sha256'] == original[1]
        assert result['candidate_subject_snapshot_sha256'] != original[1]
        assert measurement._tree_manifest(source, max_files=100, max_bytes=1_000_000) == original
        for name, text in FILES.items():
            assert (source/name).read_text() == text
        if accepted:
            assert not result['failed_obligation_ids']
            assert not result['unbound_obligation_ids']
            assert all(row['pass'] for row in result['obligation_results'])
        else:
            assert result[reason]
        report = json.loads((root/'report.json').read_text())
        assert report['pass'] is accepted
        assert report['acceptance_stop_authorized'] is accepted
        assert result['output_verified'] is True
        assert not list(root.glob('.v9_repair_*'))
