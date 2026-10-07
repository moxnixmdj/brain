from __future__ import annotations

import collections
import io
import pickle
import struct
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

from canonical.runtime.h100_unichart_chartqa_bin_packer_v1 import (
    PackerError,
    parse_checkpoint_metadata,
)


class _FakeStorage:
    pass


def _make_torch_like_checkpoint(path: Path, *, conflict_alias: bool = False):
    torch = types.ModuleType("torch")
    utils = types.ModuleType("torch._utils")

    FloatStorage = type("FloatStorage", (), {})
    FloatStorage.__module__ = "torch"
    LongStorage = type("LongStorage", (), {})
    LongStorage.__module__ = "torch"

    def rebuild(storage, offset, size, stride, requires_grad, hooks):
        return ("tensor", storage, offset, size, stride, requires_grad, hooks)
    rebuild.__module__ = "torch._utils"
    rebuild.__name__ = "_rebuild_tensor_v2"
    rebuild.__qualname__ = "_rebuild_tensor_v2"

    torch.FloatStorage = FloatStorage
    torch.LongStorage = LongStorage
    utils._rebuild_tensor_v2 = rebuild
    torch._utils = utils

    old_torch = sys.modules.get("torch")
    old_utils = sys.modules.get("torch._utils")
    sys.modules["torch"] = torch
    sys.modules["torch._utils"] = utils
    try:
        class Ref:
            def __init__(self, stype, key, size):
                self.stype=stype; self.key=key; self.size=size
            def __reduce__(self):
                return (_persistent_marker,(self.stype,self.key,self.size))

        # We need persistent IDs, so use a custom Pickler.
        class P(pickle.Pickler):
            def persistent_id(self,obj):
                if isinstance(obj,Ref):
                    return ("storage",obj.stype,obj.key,"cpu",obj.size)
                return None

        f0=Ref(FloatStorage,"0",4)
        i0=Ref(LongStorage,"1",2)
        state=collections.OrderedDict()
        state["encoder.weight"] = rebuild(f0,0,(2,2),(2,1),False,collections.OrderedDict())
        if conflict_alias:
            state["decoder.alias"] = rebuild(f0,0,(2,2),(2,1),False,collections.OrderedDict())
        state["encoder.ids"] = rebuild(i0,0,(2,),(1,),False,collections.OrderedDict())

        # Replace tuples with objects that reduce through the expected global.
        class TensorProxy:
            def __init__(self, args): self.args=args
            def __reduce__(self): return (rebuild,self.args)
        for k,v in list(state.items()):
            if isinstance(v,tuple) and v and v[0]=="tensor":
                _,*args=v
                state[k]=TensorProxy(tuple(args))

        bio=io.BytesIO()
        P(bio,protocol=2).dump(state)
        with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_STORED) as z:
            z.writestr("archive/data.pkl",bio.getvalue())
            z.writestr("archive/data/0",struct.pack("<4f",1,2,3,4))
            z.writestr("archive/data/1",struct.pack("<2q",1,2))
    finally:
        if old_torch is None: sys.modules.pop("torch",None)
        else: sys.modules["torch"]=old_torch
        if old_utils is None: sys.modules.pop("torch._utils",None)
        else: sys.modules["torch._utils"]=old_utils


def _persistent_marker(*args):
    raise RuntimeError("not called")


class ChartQABinPackerTests(unittest.TestCase):
    def test_parse_torch_like_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"m.bin"
            _make_torch_like_checkpoint(p)
            out=parse_checkpoint_metadata(p)
            self.assertEqual(out["tensor_count"],2)
            self.assertEqual(out["storage_count"],2)
            self.assertEqual(out["unique_f32_elements"],4)
            self.assertEqual(out["unique_i64_elements"],2)
            self.assertEqual(out["alias_storage_count"],0)

    def test_alias_precision_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"m.bin"
            _make_torch_like_checkpoint(p,conflict_alias=True)
            with self.assertRaisesRegex(PackerError,"ALIAS_PRECISION_CONFLICT"):
                parse_checkpoint_metadata(p)


if __name__=="__main__":
    unittest.main(verbosity=2)
