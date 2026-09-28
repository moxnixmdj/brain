#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

contracts=load("project_brain_test_generic_cli_contracts",RUNTIME_DIR/"cli_contract_inference.py")
cli=load("project_brain_test_generic_cli_adapter",RUNTIME_DIR/"bound_capabilities"/"cli_command.py")

def probe(executable,help_text):
    return {
      "package":"demo",
      "version":"1.0",
      "archive_sha256":"a"*64,
      "executables":[{
        "executable":executable,
        "help_attempts":[{"flag":"--help","returncode":0,"text":help_text}],
      }],
    }

class GenericCliContractIRTests(unittest.TestCase):
    def test_existing_output_flag_text_contract_still_works(self):
        p=probe("/usr/bin/demoimg","""Usage: demoimg [TEXT]
Options:
  -o, --output FILE  write image to output file
  -d, --data TEXT    data to encode
  -x, --extra        extra
  -q, --quiet        quiet
PNG output supported
""")
        goal="Generate PNG for the text alpha and save canonical/astra_runtime/tmp/x.png."
        out=contracts.infer_contract(p,goal)
        self.assertEqual(out["io_contract"]["output_mode"],"OUTPUT_FLAG")
        self.assertEqual(out["io_contract"]["input_mode"],"INPUT_FLAG")
        self.assertEqual(set(out["required_inputs"]),{"text","output_path"})
        self.assertIn("$"+"{input.output_path}",out["argv_template"])
        self.assertIn("$"+"{input.text}",out["argv_template"])

    def test_positional_artifact_and_positional_semantic_input(self):
        p=probe("/usr/bin/sqlite3","""Usage: sqlite3 [OPTIONS] FILENAME [SQL]
SQLite database command line interface.
Options:
  -batch  force batch
  -csv    CSV output
  -json   JSON output
""")
        goal="Create canonical/astra_runtime/tmp/x.sqlite."
        out=contracts.infer_contract(p,goal)
        self.assertEqual(out["io_contract"]["output_mode"],"POSITIONAL_ARTIFACT")
        self.assertEqual(out["io_contract"]["input_mode"],"POSITIONAL_TEXT")
        self.assertEqual(out["argv_template"][1],"$"+"{input.output_path}")
        self.assertEqual(out["argv_template"][2],"$"+"{input.text}")

    def test_stdout_capture_contract(self):
        p=probe("/usr/bin/xmlconvert","""Usage: xmlconvert [TEXT]
Convert input data to XML and write result to standard output.
Options:
  -c, --compact compact output
  -p, --pretty pretty output
  -q, --quiet quiet
""")
        goal="Transform data and save canonical/astra_runtime/tmp/x.xml."
        out=contracts.infer_contract(p,goal)
        self.assertEqual(out["io_contract"]["output_mode"],"STDOUT_CAPTURE")
        self.assertTrue(out["capture_stdout_to_output"])
        self.assertEqual(out["io_contract"]["input_mode"],"POSITIONAL_TEXT")

    def test_cli_adapter_can_capture_stdout_to_repo_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            proc=types.SimpleNamespace(returncode=0,stdout=b"<x>1</x>\n",stderr=b"")
            with mock.patch.object(cli.subprocess,"run",return_value=proc) as run:
                out=cli.run({
                  "argv":["demo","payload"],
                  "output_path":"out.xml",
                  "capture_stdout_to_output":True,
                  "output_text_utf8":True,
                  "timeout_s":5,
                },root)
            self.assertTrue(out["output_verified"])
            self.assertEqual((root/"out.xml").read_bytes(),b"<x>1</x>\n")
            self.assertTrue(out["stdout_captured_to_output"])
            self.assertIsNone(run.call_args.kwargs["input"])

    def test_cli_adapter_passes_stdin_without_shell(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            proc=types.SimpleNamespace(returncode=0,stdout=b"ok\n",stderr=b"")
            with mock.patch.object(cli.subprocess,"run",return_value=proc) as run:
                cli.run({"argv":["demo"],"stdin_text":"payload","timeout_s":5},root)
            self.assertEqual(run.call_args.kwargs["input"],b"payload")
            self.assertNotIn("shell",run.call_args.kwargs)

if __name__=="__main__":
    unittest.main(verbosity=2)
