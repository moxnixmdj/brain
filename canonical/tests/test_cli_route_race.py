#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

infer=load("generic_gnu_contract_test",RUNTIME/"cli_contract_inference.py")
apt=load("apt_effect_preflight_race_test",RUNTIME/"auto_apt_cli_acquisition.py")

class GenericGnuContractTests(unittest.TestCase):
    def test_outfile_content_and_format_flags_are_learned(self):
        probe={
          "package":"generic-encoder",
          "version":"1",
          "archive_sha256":"a"*64,
          "executables":[{
            "executable":"/usr/bin/encode2d",
            "help_attempts":[{
              "text":"Usage: encode2d [OPTIONS]\nGenerate a 2D image\n"
                     "  -c, --barcode=TEXT       Barcode text\n"
                     "  -o, --outfile=FILENAME   Output filename\n"
                     "  -f, --format=FORMAT      Text UTF-8 EPS Bin Hex PNG\n"
                     "  -v, --verbose            Verbose\n"
            }]
          }]
        }
        out=infer.infer_contract(
          probe,
          "Generate a matrix image for the text HELLO and save it as canonical/astra_runtime/tmp/out.png."
        )
        self.assertEqual(out["argv_template"],[
          "encode2d","-f","PNG","-o","${input.output_path}","-c","${input.text}"
        ])
        self.assertEqual(out["evidence"]["input_transport"],"FLAG")

class AptEffectPreflightRaceTests(unittest.TestCase):
    def test_failed_first_effect_falls_through_to_second_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            mission_dir=root/"canonical"/"astra_runtime"/"missions"
            mission_dir.mkdir(parents=True)
            mission_rel="canonical/astra_runtime/missions/M.json"
            (root/mission_rel).write_text('{"mission_id":"M"}\n')
            discovery={"candidates":[]}
            candidates=[
              {"name":"first","version":"1","archive_sha256":"a"*64,
               "discovery_source":"APT_CATALOG","zero_cost_eligible":True,
               "required_secret_count":0,"integration_friction":0,"score":50},
              {"name":"second","version":"1","archive_sha256":"b"*64,
               "discovery_source":"APT_CATALOG","zero_cost_eligible":True,
               "required_secret_count":0,"integration_friction":0,"score":40},
            ]
            contract={
              "argv_template":["writer","-o","${input.output_path}","${input.text}"],
              "output_path_template":"${input.output_path}",
              "stdin_text_template":None,
              "output_prefix_hex":"89504e470d0a1a0a",
              "output_text_utf8":False,
              "timeout_s":60,
              "required_inputs":["text","output_path"],
              "evidence":{}
            }
            calls=[]
            def run(args, _root):
                calls.append(list(args["argv"]))
                if len(calls)==1:
                    raise RuntimeError("producer crashed")
                return {"returncode":0,"output_verified":True,"output_path":args["output_path"]}
            with (
              mock.patch.object(apt,"_merge_role_conditioned_apt",return_value=discovery),
              mock.patch.object(apt,"_viable_candidates",return_value=candidates),
              mock.patch.object(apt.apt_cli_probe,"probe",side_effect=lambda pkg,*a,**k:{"package":pkg}),
              mock.patch.object(apt.cli_contract_inference,"infer_contract",return_value=contract),
              mock.patch.object(apt,"_bind_contract_inputs",return_value={
                "text":"HELLO","output_path":"canonical/astra_runtime/tmp/out.png"
              }),
              mock.patch.object(apt.cli_command,"run",side_effect=run),
            ):
                out=apt.dispatch(
                  "Generate image for the text HELLO and save it as canonical/astra_runtime/tmp/out.png.",
                  "M",mission_rel,root,discovery=discovery
                )
            self.assertEqual(out["supplier"],"second")
            self.assertEqual(len(calls),2)
            diag=pathlib.Path(root/out["acquisition_evidence_path"])
            evidence=json.loads(diag.read_text())
            self.assertEqual(evidence["attempts"][0]["status"],"EFFECT_PREFLIGHT_FAILED")
            self.assertEqual(evidence["attempts"][1]["status"],"EFFECT_PREFLIGHT_VERIFIED")

if __name__=="__main__":
    unittest.main(verbosity=2)
