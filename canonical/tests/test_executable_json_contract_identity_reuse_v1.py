"""Real generated acceptance execution, including false-positive candidates."""
from pathlib import Path
import sys
import tempfile
import pytest
from canonical.runtime.bound_capabilities import python_software_request_semantic_acceptance_v1 as compiler
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement


@pytest.mark.parametrize('requirement,body,accepted', [
    ('must be true.', 'return True', True),
    ('must be false.', 'return False', True),
    ('must be true.', 'return 1', False),
    ('must be false.', 'return 0', False),
    ('must be true.', 'return 1.0', False),
    ('must be false.', 'return 0.0', False),
    ('must equal 1.', 'return True', False),
    ('must equal 0.', 'return False', False),
    ('must equal [true, false].', 'return [1, 0]', False),
    ('must equal {"ready": true, "count": 1}.', 'return {"ready": 1, "count": True}', False),
    ('must equal {"ready": true, "count": 1}.', 'return {"ready": True, "count": 1}', True),
    ('must equal 1.', 'return 1.0', True),
    ('must equal null.', 'return None', True),
    ('must equal "ready".', 'return "ready"', True),
    ('must equal [1, 2].', 'return (1, 2)', False),
    ('must equal {"values": [true, {"ok": false}]}.', 'return {"values": [True, {"ok": 0}]}', False),
])
def test_rendered_contract_rejects_coercion_and_preserves_valid_json(requirement, body, accepted):
    task = 'Calling m.f with JSON arguments [] ' + requirement
    compiled = compiler.compile_request(task)
    assert compiled['coverage_complete'] is True
    program = compiler.render_test(compiled)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'m.py').write_text('def f():\n    ' + body + '\n')
        (root/'behavior.py').write_text(program)
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        result = measurement.run({'source_root': '.', 'test_paths': ['behavior.py'],
                                  'test_argv': [sys.executable, 'behavior.py'],
                                  'output_path': 'measurement.json', 'timeout_s': 3}, root)
        assert result['measurements']['tests_pass'] is accepted
        for name, content in before.items():
            assert (root/name).read_bytes() == content


def test_arbitrary_python_equality_cannot_satisfy_json_contract():
    compiled = compiler.compile_request('Calling m.f with JSON arguments [] must equal {"ok": true}.')
    assert compiled['coverage_complete'] is True
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'m.py').write_text('class Spoof:\n    def __eq__(self, other): return True\ndef f(): return Spoof()\n')
        (root/'behavior.py').write_text(compiler.render_test(compiled))
        result = measurement.run({'source_root': '.', 'test_paths': ['behavior.py'],
                                  'test_argv': [sys.executable, 'behavior.py'],
                                  'output_path': 'measurement.json', 'timeout_s': 3}, root)
        assert result['measurements']['tests_pass'] is False
