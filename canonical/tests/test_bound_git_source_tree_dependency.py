import hashlib
import json
import pathlib
import shutil
import unittest
from unittest import mock

from canonical.runtime import astra_runtime


class BoundGitSourceTreeTests(unittest.TestCase):
    def test_invoke_materializes_verified_source_tree_and_passes_source_root(self):
        source = (
            "import json\n"
            "def dumps(value):\n"
            "    return json.dumps(value,sort_keys=True,separators=(',',':')).encode('utf-8')\n"
            "def loads(raw):\n"
            "    return json.loads(raw.decode('utf-8'))\n"
        )
        raw = source.encode("utf-8")
        blob_sha = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        repository = "Project-Brain-Test/fakecodec"
        revision = "a" * 40
        files = [{
            "path": "fakecodec/__init__.py",
            "git_blob_sha": blob_sha,
            "content": source,
        }]
        manifest = {
            "schema": "PROJECT_BRAIN_CONTENT_ADDRESSED_PYTHON_SOURCE_TREE_V1",
            "repository": repository,
            "revision": revision,
            "package": "fakecodec",
            "files": [{
                "path": "fakecodec/__init__.py",
                "git_blob_sha": blob_sha,
                "bytes": len(raw),
            }],
            "total_bytes": len(raw),
        }
        tree_sha = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        tree = {
            "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
            "repository": repository,
            "revision": revision,
            "files": files,
        }
        capability_id = "test.auto.source.fakecodec"
        registry = {
            capability_id: {
                "status": "VERIFIED_BOUND_CAPABILITY",
                "platforms": ["linux", "windows", "darwin"],
                "provides": ["structured.binary.encode.test"],
                "requires": ["json.file.available"],
                "adapter_module": "python_source_tree_codec",
                "entrypoint": "run",
                "source": {
                    "type": "git_source_tree",
                    "repository": repository,
                    "revision": revision,
                    "tree_sha256": tree_sha,
                    "tree": tree,
                },
                "incremental_spend_usd": 0,
            }
        }

        tmp = astra_runtime.ROOT / "canonical" / "astra_runtime" / "tmp"
        input_path = tmp / "BOUND_GIT_SOURCE_TREE_TEST_INPUT.json"
        output_path = tmp / "BOUND_GIT_SOURCE_TREE_TEST_OUTPUT.bin"
        cache = tmp / "git_source_bound" / tree_sha
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(
            json.dumps({"message": "source-tree-runtime"}) + "\n",
            encoding="utf-8",
        )
        try:
            with mock.patch.object(
                astra_runtime, "_load_bound_capability_registry", return_value=registry
            ):
                result = astra_runtime._invoke_bound_capability({
                    "capability_id": capability_id,
                    "module": "fakecodec",
                    "encode_callable": "dumps",
                    "decode_callable": "loads",
                    "json_path": input_path.relative_to(astra_runtime.ROOT).as_posix(),
                    "output_path": output_path.relative_to(astra_runtime.ROOT).as_posix(),
                })

            self.assertTrue(result["output_verified"])
            self.assertTrue(output_path.is_file())
            self.assertEqual(result["dependency"]["type"], "git_source_tree")
            self.assertEqual(result["dependency"]["tree_sha256"], tree_sha)
            self.assertEqual(result["dependency"]["repository"], repository)
            self.assertTrue(pathlib.Path(result["dependency"]["source_root"]).is_dir())
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            shutil.rmtree(cache, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
