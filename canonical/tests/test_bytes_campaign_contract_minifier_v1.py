from pathlib import Path
from canonical.runtime.bytes_campaign_contract_minifier_v1 import transform_source

def test_public_surface_names_remain():
    src="def discover(x:int)->int:\n    return x\ndef predict(y:str):\n    return y\n"
    out=transform_source(src)
    assert "def discover(" in out
    assert "def predict(" in out
    assert "->" not in out

def test_internal_names_shorten_and_runtime_typing_survives():
    src=(
      "from __future__ import annotations\n"
      "from typing import Any, Mapping, Sequence\n"
      "_EPS=1\n"
      "class ExpressionTreeError(ValueError): pass\n"
      "def _finite(x:Any):\n"
      "    return isinstance(x,Sequence) and isinstance({},Mapping)\n"
    )
    out=transform_source(src)
    assert "__future__" not in out
    assert "Any" not in out
    assert "Mapping" in out and "Sequence" in out
    assert "A = 1" in out
    assert "class E(" in out
    assert "def F(" in out

def test_docstrings_removed():
    src='"""module doc"""\ndef f():\n    """function doc"""\n    return 1\n'
    out=transform_source(src)
    assert "module doc" not in out
    assert "function doc" not in out
