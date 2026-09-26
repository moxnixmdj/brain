#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

generator=load(
    "project_brain_test_capability_proposal_generator",
    RUNTIME_DIR/"capability_proposal_generators.py",
)
runtime=load(
    "project_brain_test_auto_proposal_runtime",
    RUNTIME_DIR/"astra_runtime.py",
)


class AutoSingleCapabilityProposalTests(unittest.TestCase):
    GOAL='Generate a QR code for the text "AUTO-SEMANTIC-QR" and save it as canonical/astra_runtime/tmp/AUTO_SEMANTIC_QR.png.'
    TARGET="image.qr.generate"

    def qr_registry(self):
        return {
            "image.qr.generate.qrencode":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":[],
                "provides":[self.TARGET],
                "keywords":[],
                "platforms":["linux","windows","darwin"],
                "cost":1,
                "action_template":{
                    "type":"invoke_capability",
                    "args":{
                        "capability_id":"image.qr.generate.qrencode",
                        "argv":[
                            "qrencode","-o",
                            "${input.output_path}",
                            "${input.text}",
                        ],
                        "output_path":"${input.output_path}",
                    },
                },
            },
            "image.code.decode.zbarimg":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":[],
                "provides":["image.code.decode"],
                "keywords":["decode","qr","barcode","image"],
                "platforms":["linux"],
                "cost":1,
                "action_template":{
                    "type":"invoke_capability",
                    "args":{"capability_id":"image.code.decode.zbarimg","path":"${input.path}"},
                },
            },
        }

    def test_generator_selects_one_verified_zero_spend_capability_and_binds_literals(self):
        proposal,evidence=generator.generate(
            "single-verified-capability-v1",
            self.GOAL,
            [self.TARGET],
            [],
            self.qr_registry(),
            CANONICAL_ROOT.parent,
            RUNTIME_DIR,
        )
        instance=proposal["capability_instances"][0]
        self.assertEqual(instance["capability_id"],"image.qr.generate.qrencode")
        self.assertEqual(instance["inputs"]["text"],"AUTO-SEMANTIC-QR")
        self.assertEqual(
            instance["inputs"]["output_path"],
            "canonical/astra_runtime/tmp/AUTO_SEMANTIC_QR.png",
        )
        self.assertEqual(evidence["selected_capability"],"image.qr.generate.qrencode")

    def test_current_platform_mismatch_is_not_selected(self):
        registry=self.qr_registry()
        registry["image.qr.generate.qrencode"]["platforms"]=["definitely-not-this-platform"]
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "NO_BINDABLE_VERIFIED_CAPABILITY",
        ):
            generator.generate(
                "single-verified-capability-v1",
                self.GOAL,
                [self.TARGET],
                [],
                registry,
                CANONICAL_ROOT.parent,
                RUNTIME_DIR,
            )

    def test_unsatisfied_requirement_is_not_assumed(self):
        registry=self.qr_registry()
        registry["test.needs.fact"]={
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "requires":["fact.required"],
            "provides":["target.effect"],
            "cost":1,
            "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
        }
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "NO_BINDABLE_VERIFIED_CAPABILITY",
        ):
            generator.generate(
                "single-verified-capability-v1",
                "Do the target effect.",
                ["target.effect"],
                [],
                registry,
                CANONICAL_ROOT.parent,
                RUNTIME_DIR,
            )

    def test_ambiguous_equal_capabilities_fail_closed(self):
        registry={
            "a":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":[],"provides":["target.effect"],"cost":1,
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            },
            "b":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":[],"provides":["target.effect"],"cost":1,
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            },
        }
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "AMBIGUOUS_BINDABLE_VERIFIED_CAPABILITY",
        ):
            generator.generate(
                "single-verified-capability-v1",
                "Do the target effect.",
                ["target.effect"],
                [],
                registry,
                CANONICAL_ROOT.parent,
                RUNTIME_DIR,
            )

    def test_runtime_generated_proposal_still_passes_constrained_proposal_validation(self):
        semantic_contract={
            "schema":"PROJECT_BRAIN_SEMANTIC_GOAL_CONTRACT_V1",
            "goal_sha256":"placeholder",
            "target_effects":[self.TARGET],
            "grounding":{self.TARGET:[0]},
            "signature_sha256":"placeholder",
            "authority_ids":["a","b"],
            "authority_classes":["x","y"],
            "minimum_distinct_authority_classes":2,
            "status":"QUORUM_VERIFIED",
        }
        fake_module=mock.Mock()
        proposal,evidence=generator.generate(
            "single-verified-capability-v1",
            self.GOAL,
            [self.TARGET],
            [],
            self.qr_registry(),
            CANONICAL_ROOT.parent,
            RUNTIME_DIR,
        )
        fake_module.generate.return_value=(proposal,evidence)
        step={
            "verified_initial_facts":[],
            "capability_proposal_generator":"single-verified-capability-v1",
        }
        with mock.patch.object(
            runtime,"_semantic_goal_contract",return_value=semantic_contract
        ), mock.patch.object(
            runtime,"_load_capability_proposal_generators",return_value=fake_module
        ), mock.patch.object(
            runtime,"_load_bound_capability_registry",return_value=self.qr_registry()
        ):
            problem=runtime._capability_problem_proposal(step,{},self.GOAL)
        self.assertEqual(problem["target_effects"],[self.TARGET])
        self.assertEqual(
            problem["capability_instances"][0]["capability_id"],
            "image.qr.generate.qrencode",
        )
        self.assertEqual(
            problem["_proposal_generation"]["generator"],
            "single-verified-capability-v1",
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
