"""Actual unittest discovery after existing candidate argv relocation."""
from pathlib import Path
import sys
import tempfile
import pytest
from canonical.tests.test_public_delivery_measured_acceptance_chain_reuse_v1 import FILES, CONTRACT
from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as controller
from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as measured
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement


@pytest.mark.parametrize('absolute', [False, True], ids=['relative','absolute'])
def test_explicit_discovery_repairs_and_measures_same_candidate_suite(absolute):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'candidate'
        source.mkdir()
        for name, text in FILES.items():
            path = source/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        original = measurement._tree_manifest(source, max_files=100, max_bytes=1_000_000)
        start = str(source/'tests') if absolute else 'candidate/tests'
        result = controller.run({'source_root':'candidate', 'task_text':CONTRACT,
                                 'test_paths':['candidate/tests/test_checkout.py'],
                                 'test_argv':[sys.executable,'-B','-m','unittest','discover','-s',start],
                                 'output_path':'report.json', 'timeout_s':5,
                                 'mutations_per_file':12, 'max_pair_candidates':300}, root)
        assert result['repair_pass'] is True, result
        assert result['pass'] is True, result
        assert result['acceptance_stop_authorized'] is True
        assert result['measured_fields']['tests_pass'] is True
        assert result['measured_fields']['test_count'] > 0
        assert len(result['realized_patches']) == 2
        assert not result['failed_obligation_ids']
        assert not result['unbound_obligation_ids']
        assert measurement._tree_manifest(source, max_files=100, max_bytes=1_000_000) == original


@pytest.mark.parametrize('absolute', [False, True])
@pytest.mark.parametrize('relative,expected', [('candidate/tests','tests'), ('candidate','.')])
def test_existing_source_local_directory_tokens_are_rebased(absolute, relative, expected):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'candidate'
        (source/'tests').mkdir(parents=True)
        test = source/'tests/check.py'
        test.write_text('assert True\n')
        raw = str(root/relative) if absolute else relative
        argv = [sys.executable,'-m','unittest','discover','-s',raw]
        paths, relocated = measured._candidate_test_layout(root, source, [test], argv)
        assert paths == ['tests/check.py']
        assert relocated == argv[:-1]+[expected]
        assert argv[-1] == raw


def test_outside_directories_nonpaths_and_source_files_keep_existing_policy():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'candidate'
        source.mkdir()
        (root/'outside').mkdir()
        test = source/'driver.py'
        test.write_text('value = 1\n')
        argv = [sys.executable,'-B','candidate/driver.py','outside','missing','x'*5000]
        paths, relocated = measured._candidate_test_layout(root, source, [test], argv)
        assert paths == ['driver.py']
        assert relocated == [sys.executable,'-B','driver.py','outside','missing','x'*5000]
