from __future__ import annotations

import json
import pathlib
import unittest

from canonical.runtime.sealed_field_projection_consumer_v1 import (
    PROJECTION_FILE,
    RUNNER_FILE,
    RUNNER_SCHEMA,
    _runner_source,
    prepare_projection_bundle,
    run_sealed_consumer,
)


class FakeLauncher:
    def __init__(self):
        self.policies=[]

    def __call__(self,policy):
        self.policies.append(policy)
        root=pathlib.Path(policy["input_dir"])
        projection=json.loads((root/PROJECTION_FILE).read_text(encoding="utf-8"))
        entries=sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file()
        )
        payload={
            "schema":RUNNER_SCHEMA,
            "projection_bundle_sha256":projection["projection_bundle_sha256"],
            "consumer_result":{
                "seen_sources":projection["source_count"],
                "input_files":entries,
            },
        }
        return {
            "status":"CHILD_EXITED",
            "returncode":0,
            "policy_sha256":"f"*64,
            "broker_payload":json.dumps(payload,separators=(",",":")).encode(),
        }


class SealedFieldProjectionConsumerTests(unittest.TestCase):
    def documents(self):
        return {
            "canonical/governance/A.json":{
                "authority":{"proved":7,"open":12},
                "scheduler":{"generation":44},
            }
        }

    def dependencies(self):
        return {
            "canonical/governance/A.json":[
                "/authority/proved",
                "/authority/open",
            ]
        }

    def consumer_files(self):
        return {
            "consumer.py":(
                "def evaluate(projection):\n"
                "    return {'ok': projection['source_count']==1}\n"
            )
        }

    def test_unrelated_same_file_churn_has_same_projection_hash(self):
        a=prepare_projection_bundle(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
        )
        bdocs=self.documents()
        bdocs["canonical/governance/A.json"]["scheduler"]["generation"]=999
        b=prepare_projection_bundle(
            source_documents=bdocs,
            field_dependencies=self.dependencies(),
        )
        self.assertEqual(
            a["projection_bundle_sha256"],
            b["projection_bundle_sha256"],
        )

    def test_declared_field_change_changes_projection_hash(self):
        a=prepare_projection_bundle(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
        )
        bdocs=self.documents()
        bdocs["canonical/governance/A.json"]["authority"]["proved"]=8
        b=prepare_projection_bundle(
            source_documents=bdocs,
            field_dependencies=self.dependencies(),
        )
        self.assertNotEqual(
            a["projection_bundle_sha256"],
            b["projection_bundle_sha256"],
        )

    def test_consumer_receives_closed_world_tree_and_zero_authority(self):
        launcher=FakeLauncher()
        out=run_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_files=self.consumer_files(),
            consumer_module="consumer.py",
            launcher=launcher,
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["undeclared_host_repository_reads_available"])
        self.assertEqual(out["closed_world_input_entry_count"],3)
        policy=launcher.policies[0]
        self.assertEqual(
            policy["argv"],
            ["/usr/bin/python3","-I","-S","/input/"+RUNNER_FILE],
        )
        self.assertEqual(
            out["consumer_result"]["input_files"],
            [PROJECTION_FILE,RUNNER_FILE,"consumer.py"],
        )

    def test_helper_files_are_explicit_manifest_entries(self):
        launcher=FakeLauncher()
        files=self.consumer_files()
        files["helpers/util.py"]="VALUE=1\n"
        out=run_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_files=files,
            consumer_module="consumer.py",
            launcher=launcher,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["closed_world_input_entry_count"],4)
        self.assertIn("helpers/util.py",out["consumer_result"]["input_files"])

    def test_undeclared_consumer_module_fails_closed(self):
        out=run_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_files=self.consumer_files(),
            consumer_module="other.py",
            launcher=FakeLauncher(),
        )
        self.assertFalse(out["pass"])
        self.assertIn("CONSUMER_MODULE_NOT_DECLARED",out["error"])

    def test_path_traversal_fails_closed(self):
        out=run_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_files={"../escape.py":"def evaluate(x): return {}\n"},
            consumer_module="../escape.py",
            launcher=FakeLauncher(),
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNSAFE_INPUT_PATH",out["error"])

    def test_child_binding_mismatch_fails_closed(self):
        def bad_launcher(policy):
            payload={
                "schema":RUNNER_SCHEMA,
                "projection_bundle_sha256":"0"*64,
                "consumer_result":{"ok":True},
            }
            return {
                "status":"CHILD_EXITED",
                "returncode":0,
                "policy_sha256":"f"*64,
                "broker_payload":json.dumps(payload).encode(),
            }
        out=run_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_files=self.consumer_files(),
            consumer_module="consumer.py",
            launcher=bad_launcher,
        )
        self.assertFalse(out["pass"])
        self.assertIn("CHILD_PROJECTION_BINDING_MISMATCH",out["error"])

    def test_runner_source_compiles_and_binds_projection_hash(self):
        src=_runner_source(
            consumer_module="consumer.py",
            consumer_entrypoint="evaluate",
            projection_sha256="a"*64,
        )
        compile(src,"<sealed-runner>","exec")
        self.assertIn('EXPECTED_PROJECTION_SHA256=' + json.dumps("a"*64),src)


if __name__=="__main__":
    unittest.main(verbosity=2)
