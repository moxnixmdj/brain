#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import goal_compiler


class SourceTreeIndependentVerificationCompilationTests(unittest.TestCase):
    def test_source_tree_producer_routes_to_existing_independent_npm_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "canonical" / "CANONICAL_POINTER.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps({
                    "name": "PROJECT_BRAIN",
                    "sequence": [1, 2, 3],
                    "active": True,
                    "nullable": None,
                }) + "\n",
                encoding="utf-8",
            )
            registry = {
                "auto.source.py-ubjson": {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "platforms": ["linux"],
                    "provides": [
                        "structured.binary.encode",
                        "structured.binary.encode.ubj",
                    ],
                    "requires": ["json.file.available"],
                    "keywords": [
                        "encode", "binary", "ubj", "ubjson", "py-ubjson"
                    ],
                    "adapter_module": "python_source_tree_codec",
                    "entrypoint": "run",
                    "source": {
                        "type": "git_source_tree",
                        "repository": "Iotic-Labs/py-ubjson",
                    },
                    "action_template": {
                        "type": "invoke_capability",
                        "args": {
                            "capability_id": "auto.source.py-ubjson",
                            "module": "ubjson",
                            "encode_callable": "dumpb",
                            "decode_callable": "loadb",
                            "encode_kwargs": {},
                            "decode_kwargs": {},
                            "envelope_key": None,
                            "json_path": "${input.json_path}",
                            "output_path": "${input.output_path}",
                        },
                        "expect": {
                            "type": "field_equals",
                            "field": "output_verified",
                            "value": True,
                        },
                    },
                    "incremental_spend_usd": 0,
                }
            }
            goal = (
                "Encode canonical/CANONICAL_POINTER.json as UBJSON and save "
                "canonical/astra_runtime/artifacts/CANONICAL_POINTER_20260927.ubj. "
                "Independently decode the UBJSON artifact using a different "
                "implementation than the producer and verify the decoded JSON "
                "object is exactly identical to canonical/CANONICAL_POINTER.json."
            )

            compiled = goal_compiler.compile_goal(goal, registry, root)

            self.assertEqual(
                compiled["compiler_mode"],
                "DETERMINISTIC_COMPOUND_ACTION_PLAN",
            )
            self.assertTrue(compiled["clause_coverage_verified"])
            self.assertEqual(len(compiled["compiled_parts"]), 2)

            encode = compiled["controller_actions"][0]
            verify = compiled["controller_actions"][1]
            self.assertEqual(encode["type"], "invoke_capability")
            self.assertEqual(
                encode["args"]["capability_id"],
                "auto.source.py-ubjson",
            )
            self.assertEqual(
                verify["type"],
                "verify_with_independent_npm_codec",
            )
            self.assertEqual(
                verify["args"]["producer_project"],
                "Iotic-Labs/py-ubjson",
            )
            self.assertEqual(verify["args"]["format"], "ubj")
            self.assertEqual(
                verify["args"]["json_path"],
                "canonical/CANONICAL_POINTER.json",
            )
            self.assertEqual(
                verify["args"]["binary_path"],
                "canonical/astra_runtime/artifacts/CANONICAL_POINTER_20260927.ubj",
            )
            self.assertEqual(
                compiled["compiled_parts"][1]["mode"],
                "CROSS_SUPPLIER_PRODUCER_INDEPENDENT_CODEC_VERIFICATION",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
