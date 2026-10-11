from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.eval_adapters import chartography_qwen3vl_backend_v2 as v2


class BackendV2Tests(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        model=root/"model.gguf"; model.write_bytes(b"model-fixture")
        proj=root/"mmproj.gguf"; proj.write_bytes(b"projector-fixture")
        env={
            "PROJECT_BRAIN_QWEN_MODEL":str(model),
            "PROJECT_BRAIN_QWEN_MMPROJ":str(proj),
        }
        return td,model,proj,env

    def test_exact_fixture_hashes_can_be_bound(self):
        td,model,proj,env=self.fixture()
        with td, patch.dict(os.environ,env,clear=False), \
             patch.object(v2,"MODEL_SHA256",hashlib.sha256(model.read_bytes()).hexdigest()), \
             patch.object(v2,"PROJECTOR_SHA256",hashlib.sha256(proj.read_bytes()).hexdigest()):
            got_model,got_proj=v2.verify_artifacts()
        self.assertEqual(got_model,model)
        self.assertEqual(got_proj,proj)

    def test_model_hash_drift_fails_closed(self):
        td,model,proj,env=self.fixture()
        with td, patch.dict(os.environ,env,clear=False), \
             patch.object(v2,"PROJECTOR_SHA256",hashlib.sha256(proj.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(RuntimeError,"QWEN_MODEL_SHA256_MISMATCH"):
                v2.verify_artifacts()

    def test_projector_hash_drift_fails_closed(self):
        td,model,proj,env=self.fixture()
        with td, patch.dict(os.environ,env,clear=False), \
             patch.object(v2,"MODEL_SHA256",hashlib.sha256(model.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(RuntimeError,"QWEN_MMPROJ_SHA256_MISMATCH"):
                v2.verify_artifacts()

    @patch.object(v2,"verify_artifacts")
    @patch.object(v2.v1,"main",return_value=0)
    def test_main_verifies_before_delegate(self,delegate,verify):
        self.assertEqual(v2.main(),0)
        verify.assert_called_once_with()
        delegate.assert_called_once_with()


if __name__=="__main__":
    unittest.main(verbosity=2)
