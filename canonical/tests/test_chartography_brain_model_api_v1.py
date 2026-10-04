#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from inspect_ai.model import ChatMessageUser, ContentImage, ContentText, GenerateConfig

HERE=Path(__file__).resolve()
RUNTIME=HERE.parents[1]/"runtime"/"eval_adapters"/"chartography_brain_model_api_v1.py"
spec=importlib.util.spec_from_file_location("chartography_brain_adapter_v1",RUNTIME)
adapter=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(adapter)


BACKEND_SOURCE=r"""#!/usr/bin/env python3
import base64,hashlib,json,sys
req=json.loads(sys.stdin.read())
raw=base64.b64decode(req["image_bytes_b64"],validate=True)
question=req["question"]
out={
  "schema":"PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_RESPONSE_V1",
  "backend_id":req["backend_id"],
  "question_sha256":hashlib.sha256(question.encode("utf-8")).hexdigest(),
  "image_sha256":hashlib.sha256(raw).hexdigest(),
  "answer":"ECHO:"+question+"|BYTES:"+str(len(raw)),
  "fallback_used":False,
  "incremental_spend_usd":0
}
print(json.dumps(out,sort_keys=True))
"""


class ChartographyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.old_root=adapter.ROOT
        adapter.ROOT=self.root
        self.backend=self.root/"backend.py"
        self.backend.write_text(BACKEND_SOURCE,encoding="utf-8")
        self.image=self.root/"chart.png"
        self.image.write_bytes(b"\x89PNG\r\n\x1a\nFAKE_CHART_BYTES")
        self.binding=self.root/"binding.json"
        self._write_binding()

    def tearDown(self):
        adapter.ROOT=self.old_root
        self.tmp.cleanup()

    def _write_binding(self,**overrides):
        payload={
          "schema":"PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_BACKEND_BINDING_V1",
          "status":"VERIFIED_BOUND_MULTIMODAL_BACKEND",
          "backend_id":"fixture-internal-multimodal-v1",
          "program_path":"backend.py",
          "program_sha256":hashlib.sha256(self.backend.read_bytes()).hexdigest(),
          "input_contract":"QUESTION_PLUS_IMAGE_BYTES_V1",
          "output_contract":"ANSWER_TEXT_V1",
          "capability_internalization_status":"INTERNALIZED_CONFIGURED",
          "brain_controlled":True,
          "external_model_dependency_count":0,
          "network_required":False,
          "fallback_allowed":False,
          "incremental_spend_usd":0,
          "timeout_s":30
        }
        payload.update(overrides)
        self.binding.write_text(json.dumps(payload),encoding="utf-8")

    def _message(self,question="What is shown?"):
        return ChatMessageUser(content=[
          ContentText(text=question),
          ContentImage(image=str(self.image)),
        ])

    def _api(self):
        return adapter.BrainChartographyModelAPI(
          model_name="brain",
          binding_path="binding.json"
        )

    def test_exact_question_and_image_bytes_reach_backend(self):
        api=self._api()
        out=asyncio.run(api.generate(
          [self._message("Read this chart exactly.")],[],None,GenerateConfig()
        ))
        self.assertEqual(
          out.completion,
          "ECHO:Read this chart exactly.|BYTES:"+str(len(self.image.read_bytes()))
        )

    def test_missing_verified_binding_fails_closed(self):
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"VERIFIED_BACKEND_BINDING_REQUIRED"):
            adapter.BrainChartographyModelAPI(model_name="brain")

    def test_nonzero_spend_binding_rejected(self):
        self._write_binding(incremental_spend_usd=0.01)
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"NONZERO_INCREMENTAL_SPEND_FORBIDDEN"):
            self._api()

    def test_external_model_dependency_rejected(self):
        self._write_binding(external_model_dependency_count=1)
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"EXTERNAL_MODEL_DEPENDENCY_FORBIDDEN"):
            self._api()

    def test_network_dependency_rejected(self):
        self._write_binding(network_required=True)
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"NETWORK_DEPENDENCY_FORBIDDEN"):
            self._api()

    def test_fallback_binding_rejected(self):
        self._write_binding(fallback_allowed=True)
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"BACKEND_FALLBACK_FORBIDDEN"):
            self._api()

    def test_program_hash_drift_rejected(self):
        self.backend.write_text(BACKEND_SOURCE+"\n# drift\n",encoding="utf-8")
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"BACKEND_PROGRAM_HASH_MISMATCH"):
            self._api()

    def test_tools_are_rejected(self):
        api=self._api()
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"TOOLS_NOT_ALLOWED"):
            asyncio.run(api.generate([self._message()],[object()],None,GenerateConfig()))

    def test_extra_message_rejected(self):
        api=self._api()
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"EXACT_SINGLE_USER_MESSAGE_REQUIRED"):
            asyncio.run(api.generate([self._message(),self._message()],[],None,GenerateConfig()))

    def test_wrong_content_order_rejected(self):
        api=self._api()
        msg=ChatMessageUser(content=[
          ContentImage(image=str(self.image)),
          ContentText(text="question"),
        ])
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"CONTENT_ORDER_MUST_BE_TEXT_THEN_IMAGE"):
            asyncio.run(api.generate([msg],[],None,GenerateConfig()))

    def test_remote_image_fetch_rejected(self):
        api=self._api()
        msg=ChatMessageUser(content=[
          ContentText(text="question"),
          ContentImage(image="https://example.com/chart.png"),
        ])
        with self.assertRaisesRegex(adapter.ChartographyAdapterError,"REMOTE_IMAGE_FETCH_FORBIDDEN"):
            asyncio.run(api.generate([msg],[],None,GenerateConfig()))


if __name__=="__main__":
    unittest.main(verbosity=2)
