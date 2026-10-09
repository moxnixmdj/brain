import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from canonical.runtime import d_final_live_bound_bridge_v1 as b


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="d-live-bridge-")
        self.root=Path(self.t.name)
        for rel in b.PROVIDER_CLOSURE:
            p=self.root/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("x\n",encoding="utf-8")
        self.adapter_rel="canonical/runtime/bound_capabilities/archive_tarfile.py"
        p=self.root/self.adapter_rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text("adapter\n",encoding="utf-8")

    def tearDown(self):
        self.t.cleanup()

    def test_no_epoch_returns_none(self):
        with mock.patch.object(
            b.d_epoch,
            "current_epoch",
            side_effect=b.d_epoch.DFinalityError("NO_ACTIVE_D_FINALITY_EPOCH"),
        ):
            self.assertIsNone(b.active_epoch_or_none())

    def test_contract_mismatch_fails(self):
        epoch=SimpleNamespace(capability_contract_sha256="a"*64,material_bindings=tuple())
        with mock.patch.object(b.d_epoch,"require_capability",return_value=epoch), \
             mock.patch.object(b.d_epoch,"require_material",return_value=None), \
             mock.patch.object(
                 b.provider,"inspect",
                 return_value={
                     "registry_entry_sha256":"b"*64,
                     "entry":{"source":{"adapter_path":self.adapter_rel}},
                 },
             ):
            with self.assertRaisesRegex(b.DFinalLiveBoundBridgeError,"D_EPOCH_CAPABILITY_CONTRACT_MISMATCH"):
                b.invoke("bound:x","x",{},repo_root=self.root)

    def test_adapter_must_be_material_bound(self):
        contract="a"*64
        epoch=SimpleNamespace(capability_contract_sha256=contract,material_bindings=tuple())
        with mock.patch.object(b.d_epoch,"require_capability",return_value=epoch), \
             mock.patch.object(b.d_epoch,"require_material",return_value=None), \
             mock.patch.object(
                 b.provider,"inspect",
                 return_value={
                     "registry_entry_sha256":contract,
                     "entry":{"source":{"adapter_path":self.adapter_rel}},
                 },
             ):
            with self.assertRaisesRegex(b.DFinalLiveBoundBridgeError,"D_EPOCH_ADAPTER_NOT_BOUND"):
                b.invoke("bound:x","x",{},repo_root=self.root)

    def test_provider_closure_and_adapter_are_required_point_of_use(self):
        contract="a"*64
        epoch=SimpleNamespace(
            capability_contract_sha256=contract,
            material_bindings=((self.adapter_rel,"b"*40),),
        )
        with mock.patch.object(b.d_epoch,"require_capability",return_value=epoch), \
             mock.patch.object(b.d_epoch,"require_material",return_value=None) as req, \
             mock.patch.object(
                 b.provider,"inspect",
                 return_value={
                     "registry_entry_sha256":contract,
                     "entry":{"source":{"adapter_path":self.adapter_rel}},
                 },
             ), \
             mock.patch.object(b.confined_runner,"run",return_value={"pass":True,"status":"OK"}) as exe, \
             mock.patch.dict(b.PURE_FILE_INPUT_FIELDS,{"x":("input_path",)}):
            input_file=self.root/"task.json"
            input_file.write_text("{}",encoding="utf-8")
            out=b.invoke("bound:x","x",{"input_path":"task.json"},repo_root=self.root)
        self.assertTrue(out["pass"])
        required=[call.args[0] for call in req.call_args_list]
        self.assertEqual(required[:-1],list(b.PROVIDER_CLOSURE))
        self.assertEqual(required[-1],self.adapter_rel)
        self.assertEqual(exe.call_args.kwargs["expected_adapter_git_blob_sha"],"b"*40)
        self.assertEqual(exe.call_args.kwargs["expected_registry_entry_sha256"],contract)
        self.assertEqual(exe.call_args.kwargs["task_input_paths"],["task.json"])

    def test_provider_failure_is_not_returned_as_success(self):
        contract="a"*64
        epoch=SimpleNamespace(
            capability_contract_sha256=contract,
            material_bindings=((self.adapter_rel,"b"*40),),
        )
        with mock.patch.object(b.d_epoch,"require_capability",return_value=epoch), \
             mock.patch.object(b.d_epoch,"require_material",return_value=None), \
             mock.patch.object(
                 b.provider,"inspect",
                 return_value={
                     "registry_entry_sha256":contract,
                     "entry":{"source":{"adapter_path":self.adapter_rel}},
                 },
             ), \
             mock.patch.object(b.confined_runner,"run",return_value={"pass":False,"errors":["boom"]}), \
             mock.patch.dict(b.PURE_FILE_INPUT_FIELDS,{"x":("input_path",)}):
            input_file=self.root/"task.json"
            input_file.write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(b.DFinalLiveBoundBridgeError,"D_FINAL_CONFINED_RUNNER_FAILED"):
                b.invoke("bound:x","x",{"input_path":"task.json"},repo_root=self.root)


    def test_effectful_or_unclassified_capability_fails_closed(self):
        contract="a"*64
        epoch=SimpleNamespace(
            capability_contract_sha256=contract,
            material_bindings=((self.adapter_rel,"b"*40),),
        )
        with mock.patch.object(b.d_epoch,"require_capability",return_value=epoch), \
             mock.patch.object(b.d_epoch,"require_material",return_value=None), \
             mock.patch.object(
                 b.provider,"inspect",
                 return_value={
                     "registry_entry_sha256":contract,
                     "entry":{"source":{"adapter_path":self.adapter_rel}},
                 },
             ):
            with self.assertRaisesRegex(
                b.DFinalLiveBoundBridgeError,
                "D_FINAL_LIVE_CAPABILITY_NOT_PURE_CONFINED_YET",
            ):
                b.invoke("bound:archive.tar_gz.create_from_manifest","archive.tar_gz.create_from_manifest",{},repo_root=self.root)


if __name__=="__main__":
    unittest.main(verbosity=2)
