#!/usr/bin/env python3
import importlib.util, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))

spec=importlib.util.spec_from_file_location("cli_contract_inference_role_test",RUNTIME/"cli_contract_inference.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CliContractRoleSelectionTests(unittest.TestCase):
    def test_generation_goal_prefers_writer_help_over_longer_reader_help(self):
        probe={
          "package":"multi-tool",
          "version":"1",
          "archive_sha256":"a"*64,
          "executables":[
            {
              "executable":"/usr/bin/thingread",
              "help_attempts":[{"text":"Usage: thingread [FILE]\nScan image FILE and decode results to standard output.\nOPTIONS:\n  -a, --alpha=A\n  -b, --beta=B\n  -c, --charlie=C\n  -d, --delta=D\n"+"reader detail "*100}]
            },
            {
              "executable":"/usr/bin/thingwrite",
              "help_attempts":[{"text":"Usage: thingwrite [TEXT]\nEncode text and write PNG image output.\nOPTIONS:\n  -o, --output FILE   output file\n  -a, --alpha=A\n  -b, --beta=B\n  -c, --charlie=C\n"}]
            }
          ]
        }
        exe,text=mod._help_text(probe,"Generate an image and save it as canonical/astra_runtime/tmp/out.png.")
        self.assertEqual(pathlib.Path(exe).name,"thingwrite")
        self.assertIn("Encode text",text)

if __name__=="__main__":
    unittest.main(verbosity=2)
