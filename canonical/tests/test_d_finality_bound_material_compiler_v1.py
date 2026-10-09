import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.d_finality_bound_material_compiler_v1 import (
    MaterialCompileError,
    SHARED_ROOTS,
    compile_candidate,
)


class BoundMaterialCompilerTests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory(prefix="d-material-compiler-")
        root = Path(td.name)
        (root / "canonical/runtime/bound_capabilities").mkdir(parents=True)
        for p in ("canonical/__init__.py", "canonical/runtime/__init__.py", "canonical/runtime/bound_capabilities/__init__.py"):
            (root / p).write_text("", encoding="utf-8")
        for rel in SHARED_ROOTS:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("X=1\n", encoding="utf-8")
        return td, root

    def test_compiles_static_and_literal_dynamic_closure(self):
        td, root = self._repo()
        try:
            (root / "canonical/runtime/helper.py").write_text("import math\nVALUE=1\n", encoding="utf-8")
            (root / "canonical/runtime/bound_capabilities/sibling.py").write_text(
                "import decimal\nVALUE=2\n", encoding="utf-8"
            )
            (root / "canonical/runtime/bound_capabilities/a.py").write_text(
                "import importlib.util\n"
                "import pathlib\n"
                "import json\n"
                "from canonical.runtime import helper\n"
                "def load():\n"
                "    path=pathlib.Path(__file__).resolve().with_name('sibling.py')\n"
                "    spec=importlib.util.spec_from_file_location('sib',path)\n"
                "    return spec\n",
                encoding="utf-8",
            )
            registry = {
                "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
                "capabilities": {
                    "cap.a": {
                        "status": "VERIFIED_BOUND_CAPABILITY",
                        "incremental_spend_usd": 0,
                        "adapter_module": "a",
                        "entrypoint": "run",
                        "source": {"type": "python_stdlib", "module": "json"},
                    }
                },
            }
            (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            out = compile_candidate("cap.a", repo_root=root)
            self.assertEqual(out["status"], "MATERIAL_CLOSURE_CANDIDATE_COMPILED")
            paths = {row["path"] for row in out["materials"]}
            self.assertIn("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json", paths)
            self.assertIn("canonical/runtime/bound_capabilities/a.py", paths)
            self.assertIn("canonical/runtime/bound_capabilities/sibling.py", paths)
            self.assertIn("canonical/runtime/helper.py", paths)
            for shared in SHARED_ROOTS:
                self.assertIn(shared, paths)
            self.assertEqual(
                out["dynamic_literal_targets"],
                ["canonical/runtime/bound_capabilities/sibling.py"],
            )
            self.assertEqual(out["signals"]["unresolved_dynamic_load_count"], 0)
            self.assertFalse(out["source_obligations"]["external_material_required"])
            self.assertFalse(out["d_finality_authority"])
        finally:
            td.cleanup()

    def test_unresolved_dynamic_loader_stays_open(self):
        td, root = self._repo()
        try:
            (root / "canonical/runtime/bound_capabilities/b.py").write_text(
                "import importlib.util\n"
                "def load(path):\n"
                "    return importlib.util.spec_from_file_location('x',path)\n",
                encoding="utf-8",
            )
            registry = {
                "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
                "capabilities": {
                    "cap.b": {
                        "status": "VERIFIED_BOUND_CAPABILITY",
                        "incremental_spend_usd": 0,
                        "adapter_module": "b",
                        "entrypoint": "run",
                        "source": {"type": "python_stdlib", "module": "json"},
                    }
                },
            }
            (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            out = compile_candidate("cap.b", repo_root=root)
            self.assertEqual(out["status"], "OPEN__UNRESOLVED_DYNAMIC_LOAD")
            self.assertGreater(out["signals"]["unresolved_dynamic_load_count"], 0)
            self.assertFalse(out["d_finality_authority"])
        finally:
            td.cleanup()

    def test_unknown_capability_fails_closed(self):
        td, root = self._repo()
        try:
            (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").write_text(
                json.dumps({
                    "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
                    "capabilities": {},
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MaterialCompileError, "BOUND_CAPABILITY_UNKNOWN"):
                compile_candidate("missing", repo_root=root)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
