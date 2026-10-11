from __future__ import annotations
import ast
import json
import pathlib
import random
import tempfile
import unittest

from canonical.runtime import dna_storage_codec_v1 as codec
from canonical.runtime import dna_storage_task_adapter_v1 as a


class DNAStorageTaskAdapterV1Tests(unittest.TestCase):
    def test_encode_visible_contract(self):
        plan=a.resolve_plan(
            "Encode the input /root/data/payload.bin as DNA and save /root/results/payload.dna.",
            ["/root/results"],
        )
        self.assertEqual(plan.mode,"encode")
        self.assertEqual(plan.input_path,"/root/data/payload.bin")
        self.assertEqual(plan.output_path,"/root/results/payload.dna")

    def test_decode_visible_contract(self):
        plan=a.resolve_plan(
            "Recover the original bytes: decode from /data/reads.dna and write /results/recovered.bin.",
            ["/results"],
        )
        self.assertEqual(plan.mode,"decode")
        self.assertEqual(plan.input_path,"/data/reads.dna")
        self.assertEqual(plan.output_path,"/results/recovered.bin")

    def test_directory_artifact_plus_visible_basename(self):
        plan=a.resolve_plan(
            "Encode /root/data/input.bin into oligos. Write encoded.dna in the result directory.",
            ["/root/results"],
        )
        self.assertEqual(plan.output_path,"/root/results/encoded.dna")

    def test_source_materialization_is_bounded(self):
        plan=a.resolve_plan(
            "Implement a Python script for a deterministic DNA storage codec.",
            ["/root/results"],
        )
        self.assertEqual(plan.mode,"source")
        self.assertEqual(plan.output_path,"/root/results/dna_storage_codec.py")

    def test_ambiguous_contract_fails_closed(self):
        with self.assertRaises(a.DNAStorageTaskAdapterError):
            a.resolve_plan(
                "Encode the data in /data/a.bin and /data/b.bin to DNA.",
                ["/results"],
            )

    def test_roundtrip_end_to_end(self):
        rng=random.Random(991)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            inp=root/"payload.bin"
            out=root/"recovered.bin"
            data=bytes(rng.randrange(256) for _ in range(700))
            inp.write_bytes(data)
            plan=a.CodecTaskPlan("roundtrip",str(inp),str(out),(str(root),),("TEST",))
            receipt=a.execute_plan(plan)
            self.assertTrue(receipt["status"].startswith("PASS__"))
            self.assertEqual(out.read_bytes(),data)

    def test_encode_decode_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            inp=root/"x.bin"; dna=root/"x.dna"; out=root/"x.out.bin"
            data=bytes((i*29+3)%256 for i in range(1300))
            inp.write_bytes(data)
            e=a.execute_plan(a.CodecTaskPlan("encode",str(inp),str(dna),(str(root),),("TEST",)))
            d=a.execute_plan(a.CodecTaskPlan("decode",str(dna),str(out),(str(root),),("TEST",)))
            self.assertTrue(e["status"].startswith("PASS__"))
            self.assertTrue(d["status"].startswith("PASS__"))
            self.assertEqual(out.read_bytes(),data)

    def test_no_rank23_or_benchmark_answer_binding(self):
        source=pathlib.Path(a.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("dna-storage-codec::trial-0",source)
        self.assertNotIn("rank23",source)
        self.assertNotIn("terminal-bench-science",source)

    def test_no_model_or_network_dependencies(self):
        tree=ast.parse(pathlib.Path(a.__file__).read_text(encoding="utf-8"))
        imported=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.update(n.name for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden={"openai","anthropic","transformers","torch","requests","httpx","urllib","socket","ollama","vllm","litellm"}
        self.assertFalse(any(name.split(".")[0] in forbidden for name in imported),sorted(imported))
        self.assertEqual(a.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(a.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
