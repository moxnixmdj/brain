#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"executor_broker.py"
spec=importlib.util.spec_from_file_location("executor_broker_test_target",PATH)
broker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(broker)


class ExecutorBrokerTests(unittest.TestCase):
    def capsule(self,platform="linux"):
        return {
            "executor_policy":{
                "required_platform":platform,
                "gpu_allowed":False,
                "heavy_compute_allowed":False,
            }
        }

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
