import tempfile
from pathlib import Path
from canonical.runtime.brain_owned_python_closure_census_v1 import census

def test_recursive_owned_import_and_external_separation():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)
        (r/"canonical/runtime").mkdir(parents=True)
        (r/"canonical/__init__.py").write_text("")
        (r/"canonical/runtime/__init__.py").write_text("")
        (r/"canonical/runtime/a.py").write_text("import math\nfrom canonical.runtime import b\n")
        (r/"canonical/runtime/b.py").write_text("from typing import Any\nX=1\n")
        out=census(r,["canonical/runtime/a.py"])
        assert out["brain_owned_file_count"]==2
        assert {x["path"] for x in out["brain_owned_transitive_files"]}=={"canonical/runtime/a.py","canonical/runtime/b.py"}
        assert out["external_or_stdlib_substrate_imports"]==["math","typing"]
        assert out["brain_owned_transitive_source_bytes"]==len((r/"canonical/runtime/a.py").read_bytes())+len((r/"canonical/runtime/b.py").read_bytes())

def test_duplicate_import_does_not_double_count():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/"canonical/runtime").mkdir(parents=True)
        (r/"canonical/__init__.py").write_text(""); (r/"canonical/runtime/__init__.py").write_text("")
        (r/"canonical/runtime/a.py").write_text("from canonical.runtime import b\nfrom canonical.runtime import b\n")
        (r/"canonical/runtime/b.py").write_text("X=1\n")
        out=census(r,["canonical/runtime/a.py"])
        assert out["brain_owned_file_count"]==2

def test_namespace_package_child_import_resolves_concrete_child_module():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)
        (r/"canonical/runtime/ns_pkg").mkdir(parents=True)
        (r/"canonical/__init__.py").write_text("")
        (r/"canonical/runtime/__init__.py").write_text("")
        # Deliberately no ns_pkg/__init__.py: this is a namespace-package shape.
        (r/"canonical/runtime/ns_pkg/child.py").write_text("X=1\n")
        (r/"canonical/runtime/a.py").write_text(
            "from canonical.runtime.ns_pkg import child\n"
        )
        out=census(r,["canonical/runtime/a.py"])
        assert out["brain_owned_file_count"]==2
        assert {x["path"] for x in out["brain_owned_transitive_files"]}=={
            "canonical/runtime/a.py",
            "canonical/runtime/ns_pkg/child.py",
        }

def test_from_module_import_symbol_falls_back_to_parent_module():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)
        (r/"canonical/runtime").mkdir(parents=True)
        (r/"canonical/__init__.py").write_text("")
        (r/"canonical/runtime/__init__.py").write_text("")
        (r/"canonical/runtime/b.py").write_text("X=1\n")
        (r/"canonical/runtime/a.py").write_text(
            "from canonical.runtime.b import X\n"
        )
        out=census(r,["canonical/runtime/a.py"])
        assert out["brain_owned_file_count"]==2
        assert {x["path"] for x in out["brain_owned_transitive_files"]}=={
            "canonical/runtime/a.py",
            "canonical/runtime/b.py",
        }

