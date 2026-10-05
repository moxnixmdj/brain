from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime.opus55_sdk_schema_closure_v1 import (
    SchemaClosureError,
    compile_schema_closure,
    extract_contracts,
    git_blob_sha,
)


class Opus55SDKSchemaClosureTests(unittest.TestCase):
    def test_git_blob_sha_matches_git_object_format(self) -> None:
        self.assertEqual(
            git_blob_sha(b"abc"),
            "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f",
        )

    def test_extracts_union_literal_and_typed_dict_contracts(self) -> None:
        source = """
from typing import Union
from typing_extensions import Literal, Required, TypeAlias, TypedDict

A: TypeAlias = Union[int, str]
B: TypeAlias = Literal["x", "y"]

class Request(TypedDict, total=False):
    value: Required[int]
    mode: str
"""
        contracts = extract_contracts(source)
        self.assertEqual(
            contracts["aliases"]["A"],
            {"kind": "union", "members": ["int", "str"]},
        )
        self.assertEqual(
            contracts["aliases"]["B"],
            {"kind": "literal", "values": ["x", "y"]},
        )
        self.assertEqual(
            contracts["typed_dicts"]["Request"],
            {"value": "Required[int]", "mode": "str"},
        )

    def test_recursively_closes_relative_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "types").mkdir(parents=True)
            (root / "_models.py").write_text("FLAG = True\n", encoding="utf-8")
            (root / "types" / "leaf.py").write_text(
                "from typing import Union\n"
                "from typing_extensions import TypeAlias\n"
                "Leaf: TypeAlias = Union[int, str]\n",
                encoding="utf-8",
            )
            (root / "types" / "root.py").write_text(
                "from .leaf import Leaf\n"
                "from .._models import FLAG\n",
                encoding="utf-8",
            )

            manifest = compile_schema_closure(
                root,
                roots=["types/root.py"],
                expected_root_blobs={},
            )

            self.assertEqual(
                set(manifest["files"]),
                {"_models.py", "types/leaf.py", "types/root.py"},
            )
            self.assertEqual(manifest["file_count"], 3)

    def test_fails_closed_on_root_blob_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "types").mkdir(parents=True)
            (root / "types" / "root.py").write_text("X = 1\n", encoding="utf-8")

            with self.assertRaisesRegex(SchemaClosureError, "ROOT_BLOB_DRIFT"):
                compile_schema_closure(
                    root,
                    roots=["types/root.py"],
                    expected_root_blobs={"types/root.py": "0" * 40},
                )

    def test_fails_closed_on_unresolved_relative_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "types").mkdir(parents=True)
            (root / "types" / "root.py").write_text(
                "from .missing import Thing\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                SchemaClosureError,
                "UNRESOLVED_INTERNAL_IMPORTS",
            ):
                compile_schema_closure(
                    root,
                    roots=["types/root.py"],
                    expected_root_blobs={},
                )


if __name__ == "__main__":
    unittest.main()
