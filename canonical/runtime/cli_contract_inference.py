#!/usr/bin/env python3
"""Infer a narrow, auditable CLI invocation contract from probe evidence.

Conservative supported shape:
  COMMAND [output-option FILE] ... [STRING|TEXT|DATA]
Unsupported or ambiguous help fails closed.
"""
from __future__ import annotations
import json,pathlib,re,sys

class ContractInferenceFailure(RuntimeError): pass

MAGIC_BY_SUFFIX={
    ".png":"89504e470d0a1a0a",
    ".jpg":"ffd8ff",
    ".jpeg":"ffd8ff",
    ".pdf":"25504446",
}

def _help_text(probe):
    choices=[]
    for exe in probe.get("executables",[]):
        for att in exe.get("help_attempts",[]):
            text=str(att.get("text") or "")
            if text and "usage:" in text.lower():
                choices.append((len(text),exe.get("executable"),text))
    if not choices:
        raise ContractInferenceFailure("CLI_HELP_USAGE_REQUIRED")
    choices.sort(reverse=True)
    _,exe,text=choices[0]
    return str(exe),text

def infer_contract(probe, goal):
    exe,help_text=_help_text(probe)
    usage_line=next((x.strip() for x in help_text.splitlines() if x.strip().lower().startswith("usage:")),None)
    if not usage_line:
        raise ContractInferenceFailure("CLI_USAGE_LINE_REQUIRED")
    output_flag=None
    for line in help_text.splitlines():
        if re.search(r"(?:^|\s)-o\s+FILENAME",line) and "--output" in line:
            output_flag="-o"; break
    if output_flag is None:
        raise ContractInferenceFailure("CLI_OUTPUT_FLAG_UNRESOLVED")
    positional=None
    for token in ("STRING","TEXT","DATA"):
        if f"[{token}]" in usage_line:
            positional=token.lower(); break
    if positional is None:
        raise ContractInferenceFailure("CLI_POSITIONAL_TEXT_UNRESOLVED")
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(goal or ""))
    paths=[x.rstrip(".,;:!?)]}") for x in paths]
    output_path=paths[-1] if len(paths)==1 else None
    suffix=pathlib.Path(output_path).suffix.lower() if output_path else ""
    magic=MAGIC_BY_SUFFIX.get(suffix)
    if not magic:
        raise ContractInferenceFailure("CLI_OUTPUT_FORMAT_UNVERIFIABLE:"+suffix)
    command=pathlib.Path(exe).name
    return {
      "schema":"PROJECT_BRAIN_CLI_CONTRACT_CANDIDATE_V1",
      "status":"CANDIDATE_REQUIRES_EFFECT_VERIFICATION",
      "executable":exe,
      "command":command,
      "required_inputs":["text","output_path"],
      "argv_template":[command,output_flag,"${input.output_path}","${input.text}"],
      "output_path_template":"${input.output_path}",
      "output_prefix_hex":magic,
      "timeout_s":60,
      "evidence":{
        "usage_line":usage_line,
        "output_flag":output_flag,
        "positional_input":positional,
        "probe_package":probe.get("package"),
        "probe_version":probe.get("version"),
        "archive_sha256":probe.get("archive_sha256")
      }
    }

def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: cli_contract_inference.py PROBE_JSON GOAL_FILE_OR_TEXT OUT_JSON")
    probe=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    second=sys.argv[2]
    p=pathlib.Path(second)
    goal=p.read_text(encoding="utf-8") if p.is_file() else second
    out=infer_contract(probe,goal)
    dest=pathlib.Path(sys.argv[3]); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__": main()
