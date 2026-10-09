import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.d_finality_bound_material_compiler_v2 import (
    MaterialCompileV2Error,
    PROVIDER_THEOREM_PATHS,
    compile_candidate,
)


class BoundMaterialCompilerV2Tests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory(prefix="d-material-v2-")
        root = Path(td.name)
        (root / "canonical/runtime/bound_capabilities").mkdir(parents=True)
        for rel in (
            "canonical/__init__.py",
            "canonical/runtime/__init__.py",
            "canonical/runtime/bound_capabilities/__init__.py",
        ):
            (root / rel).write_text("", encoding="utf-8")

        # Deliberately put an unresolved dynamic loader in a provider theorem
        # subject. V2 must not contaminate member material with it.
        for i, rel in enumerate(PROVIDER_THEOREM_PATHS):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                (
                    "import importlib.util\n"
                    "def provider_dynamic(path):\n"
                    "    return importlib.util.spec_from_file_location('x', path)\n"
                )
                if i == 0
                else "PROVIDER=1\n",
                encoding="utf-8",
            )
        return td, root

    def _registry(self, root, adapter, source=None):
        doc = {
            "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
            "capabilities": {
                "cap.test": {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "incremental_spend_usd": 0,
                    "adapter_module": adapter,
                    "entrypoint": "run",
                    "source": source or {
                        "type": "python_stdlib",
                        "module": "json",
                    },
                }
            },
        }
        (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").write_text(
            json.dumps(doc), encoding="utf-8"
        )

    def test_provider_unresolved_loader_does_not_contaminate_clean_member(self):
        td, root = self._repo()
        try:
            self._registry(root, "clean")
            (root / "canonical/runtime/bound_capabilities/clean.py").write_text(
                "import json\ndef run(args, root): return {'ok': True}\n",
                encoding="utf-8",
            )
            out = compile_candidate("cap.test", repo_root=root)
            self.assertEqual(
                out["status"],
                "MEMBER_MATERIAL_CLOSURE_CANDIDATE_COMPILED",
            )
            self.assertTrue(out["provider_theorem_required"])
            self.assertEqual(
                out["member"]["signals"]["unresolved_dynamic_load_count"], 0
            )
            member_paths = {
                row["path"] for row in out["member"]["materials"]
            }
            for provider in PROVIDER_THEOREM_PATHS:
                self.assertNotIn(provider, member_paths)
            self.assertIn(
                "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
                member_paths,
            )
            self.assertIn(
                "canonical/runtime/bound_capabilities/clean.py",
                member_paths,
            )
        finally:
            td.cleanup()

    def test_member_unresolved_dynamic_loader_stays_open(self):
        td, root = self._repo()
        try:
            self._registry(root, "dynamic")
            (root / "canonical/runtime/bound_capabilities/dynamic.py").write_text(
                "import importlib.util\n"
                "def run(args, root):\n"
                "    path=args['path']\n"
                "    return importlib.util.spec_from_file_location('x', path)\n",
                encoding="utf-8",
            )
            out = compile_candidate("cap.test", repo_root=root)
            self.assertEqual(
                out["status"],
                "OPEN__MEMBER_DYNAMIC_LOAD_UNRESOLVED",
            )
            self.assertGreater(
                out["member"]["signals"]["unresolved_dynamic_load_count"], 0
            )
        finally:
            td.cleanup()

    def test_literal_sibling_is_recursively_member_bound(self):
        td, root = self._repo()
        try:
            self._registry(root, "parent")
            (root / "canonical/runtime/bound_capabilities/helper.py").write_text(
                "from canonical.runtime.bound_capabilities import leaf\nVALUE=1\n",
                encoding="utf-8",
            )
            (root / "canonical/runtime/bound_capabilities/leaf.py").write_text(
                "VALUE=2\n", encoding="utf-8"
            )
            (root / "canonical/runtime/bound_capabilities/parent.py").write_text(
                "import importlib.util\n"
                "import pathlib\n"
                "def run(args, root):\n"
                "    path=pathlib.Path(__file__).resolve().with_name('helper.py')\n"
                "    spec=importlib.util.spec_from_file_location('helper', path)\n"
                "    return spec\n",
                encoding="utf-8",
            )
            out = compile_candidate("cap.test", repo_root=root)
            self.assertEqual(
                out["status"],
                "MEMBER_MATERIAL_CLOSURE_CANDIDATE_COMPILED",
            )
            paths = {row["path"] for row in out["member"]["materials"]}
            self.assertIn(
                "canonical/runtime/bound_capabilities/helper.py", paths
            )
            self.assertIn(
                "canonical/runtime/bound_capabilities/leaf.py", paths
            )
            self.assertEqual(
                out["member"]["dynamic_literal_targets"],
                ["canonical/runtime/bound_capabilities/helper.py"],
            )
        finally:
            td.cleanup()

    def test_source_obligation_stays_member_specific(self):
        td, root = self._repo()
        try:
            self._registry(
                root,
                "clean",
                source={
                    "type": "pypi",
                    "project": "x",
                    "version": "1",
                    "wheel_sha256": "0" * 64,
                },
            )
            (root / "canonical/runtime/bound_capabilities/clean.py").write_text(
                "def run(args, root): return {'ok': True}\n",
                encoding="utf-8",
            )
            out = compile_candidate("cap.test", repo_root=root)
            self.assertTrue(
                out["member"]["source_obligations"][
                    "external_material_required"
                ]
            )
            self.assertEqual(
                out["member"]["source_obligations"]["substrate_class"],
                "PYPI",
            )
            self.assertFalse(out["d_finality_authority"])
        finally:
            td.cleanup()

    def test_unknown_capability_fails_closed(self):
        td, root = self._repo()
        try:
            (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").write_text(
                json.dumps(
                    {
                        "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
                        "capabilities": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                MaterialCompileV2Error, "BOUND_CAPABILITY_UNKNOWN"
            ):
                compile_candidate("missing", repo_root=root)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
