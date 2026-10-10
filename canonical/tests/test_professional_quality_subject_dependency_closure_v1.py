from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_subject_dependency_closure_v1 as d


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value)
    else:
        path.write_text(json.dumps(value, indent=2) + "\n")


class SubjectDependencyClosureV1Tests(unittest.TestCase):
    def _repo(self, dynamic=False):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        subject_path = root / "canonical/governance/subject.json"
        base_runtime = root / "canonical/runtime/base.py"
        child_runtime = root / "canonical/runtime/child.py"
        config = root / "canonical/governance/config.json"
        evidence = root / "canonical/verification/evidence.json"
        write(config, {"x": 1})
        write(evidence, {"pass": True})
        write(child_runtime, "VALUE = 1\n")
        source = (
            "from canonical.runtime import child\n"
            "CONFIG='canonical/governance/config.json'\n"
        )
        if dynamic:
            source += "import importlib\nname='canonical.runtime.'+'late'\nimportlib.import_module(name)\n"
        write(base_runtime, source)
        subject = {
            "system_material": {
                "components": [{"path": "canonical/runtime/base.py", "git_blob_sha": blob(base_runtime)}]
            }
        }
        write(subject_path, subject)
        worklist = {
            "candidate_subject": {
                "path": "canonical/governance/subject.json",
                "git_blob_sha": blob(subject_path),
            }
        }
        write(root / d.WORKLIST_PATH, worklist)
        entries = []
        for root_id in d.EXPECTED_ROOTS:
            entries.append({
                "root_id": root_id,
                "scope_id": root_id + "::S",
                "reusable_compiler": {
                    "path": "canonical/runtime/base.py",
                    "git_blob_sha": blob(base_runtime),
                },
                "source_receipt": {
                    "path": "canonical/verification/evidence.json",
                    "git_blob_sha": blob(evidence),
                },
            })
        write(root / d.REGISTRY_PATH, {"entries": entries})
        return td, root

    def test_recurses_runtime_imports_and_literal_config(self):
        td, root = self._repo()
        with td:
            out = d.compile_closure(repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["unique_missing_subject_components"], [
            "canonical/governance/config.json",
            "canonical/runtime/child.py",
        ])
        self.assertFalse(out["subject_dependency_closure_complete"])

    def test_external_receipt_is_not_subject_material_without_runtime_reference(self):
        td, root = self._repo()
        with td:
            out = d.compile_closure(repo_root=root)
        for row in out["roots"]:
            self.assertIn("canonical/verification/evidence.json", row["external_evidence_inputs"])
            self.assertNotIn("canonical/verification/evidence.json", row["system_material_dependencies"])

    def test_dynamic_import_blocks_classification(self):
        td, root = self._repo(dynamic=True)
        with td:
            out = d.compile_closure(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertTrue(any("DYNAMIC_IMPORT" in x for x in out["unresolved_dependencies"]))

    def test_all_twelve_roots_are_required(self):
        td, root = self._repo()
        with td:
            reg = root / d.REGISTRY_PATH
            doc = json.loads(reg.read_text())
            doc["entries"] = doc["entries"][:-1]
            write(reg, doc)
            out = d.compile_closure(repo_root=root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "ROOT_SCOPED_SUPPORT_MISSING")

    def test_adding_closure_to_subject_can_make_subject_dependency_closed(self):
        td, root = self._repo()
        with td:
            first = d.compile_closure(repo_root=root)
            sp = root / "canonical/governance/subject.json"
            subject = json.loads(sp.read_text())
            for rel in first["unique_missing_subject_components"]:
                p = root / rel
                subject["system_material"]["components"].append({"path": rel, "git_blob_sha": blob(p)})
            write(sp, subject)
            second = d.compile_closure(repo_root=root)
        self.assertTrue(second["pass"], second)
        self.assertTrue(second["subject_dependency_closure_complete"])
        self.assertEqual(second["unique_missing_subject_component_count"], 0)


if __name__ == "__main__":
    unittest.main()
