"""Real-tree regressions for the two repair protocols combined during integration."""
import hashlib
import json
import sys

import pytest

from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace
from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as crossfile
from canonical.runtime.bound_capabilities import software_repair_loop_cegis_hypothesis_v1 as cegis
from canonical.tests.test_zero_ambient_namespace_launcher_v1 import policy, write_input


def test_parallel_index_retains_pure_request_local_interface(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for i in range(70):
        (source / f"m{i:02}.py").write_text("def target():\n    return 1\ndef caller():\n    return target()\n")
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    report = indexer.build_index("source", tmp_path)
    assert report["totals"]["files"] == 70
    assert report["callers_of"]["target"] == ["caller"]
    result = indexer.run({"source_root": "source", "output_path": "index.json"}, tmp_path)
    raw = (tmp_path / "index.json").read_bytes()
    assert json.loads(raw) == report
    assert result["output_sha256"] == hashlib.sha256(raw).hexdigest()
    assert before == {p.name: p.read_bytes() for p in source.iterdir()}


def test_upstream_conflict_repair_remains_executable(tmp_path):
    project = tmp_path / "project"
    (project / "tests").mkdir(parents=True)
    (project / "tests/__init__.py").write_text("")
    source = project / "m.py"
    source.write_text("<<<<<<< HEAD\ndef left():\n    return 1\n=======\ndef right():\n    return 2\n>>>>>>> other\n")
    (project / "tests/test_m.py").write_text(
        "import unittest\nfrom m import left, right\n"
        "class TestMerge(unittest.TestCase):\n"
        "    def test_both(self):\n        self.assertEqual(left() + right(), 3)\n")
    result = crossfile.run({"source_root": "project", "output_path": "report.json"}, tmp_path)
    assert result["verified"] is True
    assert result["mode"] == "conflict_merge"
    assert result["files_edited"] == ["project/m.py"]
    namespace_ = {}
    exec(compile(source.read_text(), str(source), "exec"), namespace_)
    assert namespace_["left"]() + namespace_["right"]() == 3


def test_malformed_staged_request_never_falls_back_to_in_place(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    module = source / "m.py"
    original = b"def f(x):\n    return x < 3\n"
    module.write_bytes(original)
    with pytest.raises(ValueError, match="EXACTLY_ONE_ISSUE_OR_TASK_REQUIRED"):
        crossfile.run({"source_root": "project", "output_path": "report.json", "task_path": None}, tmp_path)
    assert module.read_bytes() == original
    assert not (tmp_path / "report.json").exists()


def test_upstream_fixture_cegis_executes_real_repair(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    source = project / "m.py"
    source.write_text("def f(x):\n    return x < 3\n")
    (project / "test_m.py").write_text(
        "import unittest\nfrom m import f\n"
        "class TestBoundary(unittest.TestCase):\n"
        "    def test_boundary(self):\n        self.assertTrue(f(3))\n        self.assertFalse(f(4))\n")
    result = cegis.run({"source_root": "project", "test_paths": ["project/test_m.py"],
                        "test_argv": [sys.executable, "-B", "-m", "unittest", "discover", "-s", "project"],
                        "budget": 1, "timeout_s": 4, "wall_budget_s": 20,
                        "output_path": "cegis.json"}, tmp_path)
    assert result["pass"] is True, result
    artifact = json.loads((tmp_path / "cegis.json").read_text())
    assert artifact["mode"] == "FIXTURE_CEGIS"
    assert artifact["baseline_returncode"] != 0
    assert artifact["final_returncode"] == 0
    assert artifact["patches"]
    ns = {}
    exec(compile(source.read_text(), str(source), "exec"), ns)
    assert all(ns["f"](x) == (x <= 3) for x in range(-10, 11))


@pytest.mark.parametrize("value", [None, 1, "true", []])
def test_extended_device_policy_requires_explicit_boolean(value):
    td, root = write_input({"c.py": "pass\n"})
    try:
        with pytest.raises(namespace.NamespaceConfinementError, match="RUNTIME_DEVICE_POLICY_MUST_BE_BOOLEAN"):
            namespace.canonical_policy({**policy(root, "c.py"), "expose_runtime_devices": value})
    finally:
        td.cleanup()


def test_extended_devices_and_proc_are_policy_bound():
    td, root = write_input({"c.py": "pass\n"})
    try:
        base = policy(root, "c.py")
        default = namespace.canonical_policy(base)
        extended = namespace.canonical_policy({**base, "expose_runtime_devices": True})
        assert default["expose_runtime_devices"] is False
        assert default["authority"]["host_filesystem"] == "READ_ONLY_SYSTEM_AND_SINGLE_INPUT_BIND_ONLY"
        assert extended["authority"]["host_filesystem"] == "READ_ONLY_SYSTEM_INPUT_RUNTIME_DEVICES_AND_PRIVATE_PROC"
        assert namespace.policy_sha256(default) != namespace.policy_sha256(extended)
    finally:
        td.cleanup()


def test_opted_in_runtime_devices_and_private_proc_work_in_real_namespace():
    td, root = write_input({"c.py": '''\
        import json, os, pathlib, stat
        devices = sorted(p.name for p in pathlib.Path('/dev').iterdir())
        with open('/dev/urandom', 'rb') as stream: entropy = len(stream.read(4))
        payload = {'devices': devices, 'entropy_bytes': entropy,
                   'char_devices': all(stat.S_ISCHR(os.stat('/dev/' + name).st_mode) for name in devices),
                   'proc_self': pathlib.Path('/proc/self/status').is_file(),
                   'hidden': all(not pathlib.Path(p).exists() for p in ['/sys', '/home', '/etc'])}
        os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), json.dumps(payload).encode())
    '''})
    try:
        result = namespace.run_confined({**policy(root, 'c.py'), 'expose_runtime_devices': True})
        assert result['returncode'] == 0, result
        assert json.loads(result['broker_payload']) == {
            'devices': ['null', 'random', 'urandom', 'zero'], 'entropy_bytes': 4,
            'char_devices': True, 'proc_self': True, 'hidden': True}
    finally:
        td.cleanup()
