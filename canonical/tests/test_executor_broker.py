#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
import hashlib
import json

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"executor_broker.py"
spec=importlib.util.spec_from_file_location("executor_broker_test_target",PATH)
broker=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=broker
spec.loader.exec_module(broker)


class ExecutorBrokerTests(unittest.TestCase):
    def _sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _obs(self):
        repo_root=ROOT.parent
        pointer=json.loads((repo_root/"canonical"/"CANONICAL_POINTER.json").read_text(encoding="utf-8"))
        state_paths=(
            "canonical/CANONICAL_POINTER.json",
            "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
            "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
        )
        return {
            "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1",
            "status":"CURRENT",
            "canonical_generation":pointer["canonical_generation"],
            "dependency_inventory_complete":True,
            "material_world_state_dependencies_complete":True,
            "unknown_material_dependencies":[],
            "stale_authority_absent":True,
            "valid_proof_action_priority":True,
            "obs_layers_current":{k:True for k in ("goal","capability","blocker","solution","verification","inherited_system","obs_process")},
            "canonical_state_dependencies":[
                {"path":p,"sha256":self._sha(repo_root/p)}
                for p in state_paths
            ],
            "dependencies":[{
                "dependency_id":"executor_attestation_set",
                "class":"EXECUTION_AUTHORITY",
                "material":True,
                "volatility":"STATIC",
                "scope":"GLOBAL",
                "status":"READY",
                "evidence":["test fixture"],
            }],
        }

    def capsule(self,platform="linux"):
        return {
            "continuous_obs":self._obs(),
            "executor_policy":{
                "required_platform":platform,
                "gpu_allowed":False,
                "heavy_compute_allowed":False,
            }
        }

    def test_missing_obs_fails_closed(self):
        capsule=self.capsule("linux")
        capsule.pop("continuous_obs")
        with self.assertRaisesRegex(broker.ExecutorUnavailable,"CONTINUOUS_OBS_BLOCKED"):
            broker.select_executor(capsule,[])

    def test_provider_is_not_authority(self):
        executors=[
            {
                "executor_id":"cloud-a","provider":"render",
                "status":"AVAILABLE","platforms":["linux"],
                "incremental_spend_usd":0,"hard_zero_spend":True,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            },
            {
                "executor_id":"laptop","provider":"remote-desktop",
                "status":"AVAILABLE","platforms":["windows"],
                "incremental_spend_usd":0,"hard_zero_spend":True,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            },
        ]
        selected=broker.select_executor(self.capsule("linux"),executors)
        self.assertEqual(selected.executor_id,"cloud-a")

    def test_offline_named_machine_does_not_block_other_executor(self):
        executors=[
            {
                "executor_id":"Mo","provider":"remote-desktop",
                "status":"OFFLINE","platforms":["windows"],
                "incremental_spend_usd":0,"hard_zero_spend":True,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            },
            {
                "executor_id":"verified-linux","provider":"cloud",
                "status":"AVAILABLE","platforms":["linux"],
                "incremental_spend_usd":0,"hard_zero_spend":True,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            },
        ]
        self.assertEqual(
            broker.select_executor(self.capsule("linux"),executors).executor_id,
            "verified-linux",
        )

    def test_rejects_unbounded_spend_even_when_nominal_cost_is_zero(self):
        with self.assertRaisesRegex(
            broker.ExecutorUnavailable,"HARD_ZERO_SPEND_NOT_ATTESTED"
        ):
            broker.select_executor(self.capsule("linux"),[{
                "executor_id":"maybe-free","provider":"cloud",
                "status":"AVAILABLE","platforms":["linux"],
                "incremental_spend_usd":0,"hard_zero_spend":False,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            }])

    def test_rejects_wrong_platform(self):
        with self.assertRaisesRegex(broker.ExecutorUnavailable,"PLATFORM_MISMATCH"):
            broker.select_executor(self.capsule("windows"),[{
                "executor_id":"linux-only","provider":"cloud",
                "status":"AVAILABLE","platforms":["linux"],
                "incremental_spend_usd":0,"hard_zero_spend":True,
                "gpu_allowed":False,"heavy_compute_allowed":False,
            }])

    def test_platform_neutral_capsule_can_use_any_admissible_platform(self):
        selected=broker.select_executor(self.capsule("platform_neutral"),[{
            "executor_id":"linux","provider":"cloud",
            "status":"AVAILABLE","platforms":["linux"],
            "incremental_spend_usd":0,"hard_zero_spend":True,
            "gpu_allowed":False,"heavy_compute_allowed":False,
        }])
        self.assertEqual(selected.executor_id,"linux")

    def test_platform_specific_claim_is_explicit_certification(self):
        self.assertEqual(
            broker.classify_platform_requirement(self.capsule("windows")),
            "PLATFORM_CERTIFICATION_REQUIRED:windows",
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
