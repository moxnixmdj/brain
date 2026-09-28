#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

infer=load("cli_contract_stdin_infer_test",RUNTIME/"cli_contract_inference.py")
cli=load("cli_contract_stdin_adapter_test",RUNTIME/"bound_capabilities"/"cli_command.py")

class CliStdinContractTests(unittest.TestCase):
    def test_inference_accepts_standard_input_transport(self):
        probe={
          "package":"writer-suite",
          "version":"1",
          "archive_sha256":"a"*64,
          "executables":[{
            "executable":"/usr/bin/imgwrite",
            "help_attempts":[{
              "text":"Usage: imgwrite [OPTION]... [FILE]\nEncode FILE or standard input and write PNG image\nOPTIONS:\n  -o, --output=FILE output filename\n  -f, --format=FORMAT PNG [default]\n  -a, --alpha=A\n  -b, --beta=B\n"
            }]
          }]
        }
        out=infer.infer_contract(
            probe,
            "Generate an image for the text HELLO and save it as canonical/astra_runtime/tmp/out.png."
        )
        self.assertEqual(out["evidence"]["input_transport"],"STDIN_TEXT")
        self.assertEqual(out["stdin_text_template"],"$"+"{input.text}")
        self.assertNotIn("$"+"{input.text}",out["argv_template"])

    def test_cli_adapter_supplies_bounded_stdin_text(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            code=(
              "import pathlib,sys;"
              "data=sys.stdin.buffer.read();"
              "pathlib.Path(sys.argv[1]).write_bytes(data)"
            )
            out=cli.run({
              "argv":[sys.executable,"-c",code,"out.txt"],
              "stdin_text":"HELLO STDIN",
              "output_path":"out.txt",
              "output_text_utf8":True,
              "timeout_s":30
            },root)
            self.assertTrue(out["stdin_text_supplied"])
            self.assertEqual((root/"out.txt").read_text(),"HELLO STDIN")


    def test_inference_exposes_positional_file_fallback_when_stdin_and_file_are_declared(self):
        probe={
          "package":"writer","version":"1","archive_sha256":"a"*64,
          "executables":[{
            "executable":"/usr/bin/writer",
            "help_attempts":[{"text":
              "Usage: writer [OPTION]... [FILE]\n"
              "Encode FILE or standard input and write image\n"
              "  -o, --output=FILE output filename\n"
              "  -f, --format=FORMAT PNG [default]\n"
            }]
          }]
        }
        out=infer.infer_contract(
          probe,
          "Generate image for the text HELLO and save it as canonical/astra_runtime/tmp/out.png."
        )
        self.assertEqual(out["evidence"]["input_transport"],"STDIN_TEXT")
        self.assertEqual(out["alternate_input_transports"],[
          {"type":"POSITIONAL_TEXT_FILE","arg_token":"__PB_TEXT_FILE__"}
        ])

if __name__=="__main__":
    unittest.main(verbosity=2)
