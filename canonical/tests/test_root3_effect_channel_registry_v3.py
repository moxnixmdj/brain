from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.root3_effect_channel_registry_v3 import audit, git_blob_sha


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return git_blob_sha(path.read_bytes())


class Root3C1V3Tests(unittest.TestCase):
    def _fixture(self, *, add_unclassified_subprocess: bool = False) -> tuple[Path, str]:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)

        astra = root / "canonical/runtime/astra_runtime.py"
        helper = root / "canonical/runtime/helper.py"
        adapter = root / "canonical/runtime/bound_capabilities/adapter.py"
        registry = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        parent = root / "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json"
        manifest = root / "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V3.json"

        _write(astra, "import helper\n")
        helper_text = (
            "import urllib.request\n"
            "from pathlib import Path\n"
            "def f():\n"
            "    urllib.request.urlopen('https://example.invalid')\n"
            "    Path('x').write_text('x')\n"
        )
        if add_unclassified_subprocess:
            helper_text += "    import subprocess\n    subprocess.run(['true'])\n"
        helper_sha = _write(helper, helper_text)
        adapter_sha = _write(adapter, "import sympy\ndef run(): return 1\n")

        registry_obj = {"capabilities": {}}
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(registry_obj), encoding="utf-8")
        registry_sha = git_blob_sha(registry.read_bytes())

        parent_obj = {
            "schema": "PARENT",
            "subject": {"astra_runtime": {"path": "canonical/runtime/astra_runtime.py"}},
            "expected_repo_dynamic_universe": {
                "fixed_loader_sites": {"_load": "canonical/runtime/helper.py"},
                "literal_runtime_helpers": [],
                "ordinary_adapter_modules": ["adapter"],
            },
        }
        parent.parent.mkdir(parents=True, exist_ok=True)
        parent.write_text(json.dumps(parent_obj), encoding="utf-8")
        parent_sha = git_blob_sha(parent.read_bytes())

        manifest_obj = {
            "schema": "PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V3",
            "parent": {"path": str(parent.relative_to(root)), "git_blob_sha": parent_sha},
            "bound_registry": {"path": str(registry.relative_to(root)), "git_blob_sha": registry_sha},
            "network_modules": {"canonical/runtime/helper.py": helper_sha},
            "child_process_modules": {},
            "local_filesystem_write_modules": {"canonical/runtime/helper.py": helper_sha},
            "inprocess_third_party_imports": {
                "canonical/runtime/bound_capabilities/adapter.py": ["sympy"]
            },
            "third_party_module_blobs": {
                "canonical/runtime/bound_capabilities/adapter.py": adapter_sha
            },
            "registry_constrained_dynamic_imports": {},
        }
        manifest.write_text(json.dumps(manifest_obj), encoding="utf-8")
        return root, str(manifest.relative_to(root))

    def test_classified_fixture_passes(self):
        root, manifest = self._fixture()
        out = audit(root, manifest)
        self.assertTrue(out["pass"], out)
        self.assertIn("canonical/runtime/helper.py", out["network_modules_observed"])
        self.assertIn("canonical/runtime/helper.py", out["local_filesystem_write_modules_observed"])

    def test_new_subprocess_edge_fails_closed(self):
        root, manifest = self._fixture(add_unclassified_subprocess=True)
        out = audit(root, manifest)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("UNCLASSIFIED_CHILD_PROCESS:") for x in out["errors"]))

    def test_git_blob_known_vector(self):
        self.assertEqual(
            git_blob_sha(b"hello\n"),
            "ce013625030ba8dba906f756967f9e9ca394464a",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
