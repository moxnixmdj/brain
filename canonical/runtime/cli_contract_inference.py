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
TEXT_SUFFIXES={".md",".markdown",".txt",".csv",".tsv",".json",".html",".htm",".xml"}
TEXT_FORMAT_NAMES={
    ".md":"markdown",".markdown":"markdown",".txt":"text",".csv":"csv",
    ".tsv":"tsv",".json":"json",".html":"html",".htm":"html",".xml":"xml"
}

def _help_text(probe):
    choices=[]
    for exe in probe.get("executables",[]):
        for att in exe.get("help_attempts",[]):
            text=str(att.get("text") or "")
            lower=text.lower()
            if text:
                if "usage:" in lower or "options:" in lower:
                    quality=3 if "usage:" in lower else 2
                    choices.append((quality,len(text),exe.get("executable"),text))
                    continue
                # Some mature CLIs (for example option-table style tools)
                # provide complete help without literal "Usage:"/"Options:"
                # headings. Accept only clearly structured help with several
                # option declarations and action-bearing flags, otherwise fail
                # closed as before.
                option_lines=[
                    line for line in text.splitlines()
                    if re.search(r"(?:^|\s)-[A-Za-z0-9](?:,|\s)|--[A-Za-z0-9]",line)
                ]
                if (
                    len(option_lines)>=4
                    and any(k in lower for k in ("--output","output file","--data","data content","input data"))
                ):
                    choices.append((1,len(text),exe.get("executable"),text))
    if not choices:
        raise ContractInferenceFailure("CLI_HELP_CONTRACT_TEXT_REQUIRED")
    choices.sort(reverse=True)
    _,_,exe,text=choices[0]
    return str(exe),text

def infer_contract(probe, goal):
    exe,help_text=_help_text(probe)
    lines=help_text.splitlines()
    usage_line=next((x.strip() for x in lines if x.strip().lower().startswith("usage:")),None)
    lower_help=help_text.lower()

    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(goal or ""))
    paths=[x.rstrip(".,;:!?)]}") for x in paths]
    output_path=paths[-1] if len(paths)==1 else None
    suffix=pathlib.Path(output_path).suffix.lower() if output_path else ""
    magic=MAGIC_BY_SUFFIX.get(suffix)
    text_output=suffix in TEXT_SUFFIXES
    if not magic and not text_output:
        raise ContractInferenceFailure("CLI_OUTPUT_FORMAT_UNVERIFIABLE:"+suffix)
    format_name=suffix.lstrip(".")
    aliases={"jpg":"jpeg"}
    wanted=TEXT_FORMAT_NAMES.get(suffix,aliases.get(format_name,format_name))
    if wanted and wanted not in lower_help:
        raise ContractInferenceFailure("CLI_OUTPUT_FORMAT_UNSUPPORTED:"+suffix)

    output_flag=None
    output_line=None
    for line in lines:
        ll=line.lower()
        if "--output" in ll or "output file" in ll or "write image to" in ll:
            m=re.search(r"(?:^|\s)(-[A-Za-z0-9])(?:\s|,)",line)
            if m:
                output_flag=m.group(1); output_line=line.strip(); break
    if output_flag is None:
        raise ContractInferenceFailure("CLI_OUTPUT_FLAG_UNRESOLVED")

    input_flag=None
    positional=None
    if usage_line:
        for token in ("STRING","TEXT","DATA"):
            if f"[{token}]" in usage_line:
                positional=token.lower(); break
    if positional is None:
        for line in lines:
            ll=line.lower()
            if "--data" in ll or "string to encode" in ll or "data to encode" in ll:
                m=re.search(r"(?:^|\s)(-[A-Za-z0-9])(?:\s|,)",line)
                if m:
                    input_flag=m.group(1); break
    if positional is None and input_flag is None:
        raise ContractInferenceFailure("CLI_TEXT_INPUT_UNRESOLVED")

    selector=[]
    normalized_goal=re.sub(r"[^a-z0-9]+","",str(goal).lower())
    if "code128" in normalized_goal:
        barcode_flag=None
        for line in lines:
            ll=line.lower()
            if "--barcode" in ll and ("type" in ll or "symbolog" in ll):
                m=re.search(r"(?:^|\s)(-[A-Za-z0-9])(?:\s|,)",line)
                if m:
                    barcode_flag=m.group(1); break
        if barcode_flag:
            selector=[barcode_flag,"CODE128"]
        elif "code128" in lower_help or "code 128" in lower_help:
            for line in lines:
                if "encoding type" in line.lower():
                    m=re.search(r"(?:^|\s)(-[A-Za-z0-9])(?:\s|,)",line)
                    if m:
                        selector=[m.group(1),"code128"]; break

    command=pathlib.Path(exe).name
    argv=[command,*selector,output_flag,"__OUT_PLACEHOLDER__"]
    if input_flag:
        argv.extend([input_flag,"__TEXT_PLACEHOLDER__"])
    else:
        argv.append("__TEXT_PLACEHOLDER__")
    argv=[x.replace("__OUT_PLACEHOLDER__","$"+"{input.output_path}").replace("__TEXT_PLACEHOLDER__","$"+"{input.text}") for x in argv]
    return {
      "schema":"PROJECT_BRAIN_CLI_CONTRACT_CANDIDATE_V1",
      "status":"CANDIDATE_REQUIRES_EFFECT_VERIFICATION",
      "executable":exe,
      "command":command,
      "required_inputs":["text","output_path"],
      "argv_template":argv,
      "output_path_template":"$"+"{input.output_path}",
      "output_prefix_hex":magic or "",
      "output_text_utf8":bool(text_output),
      "timeout_s":60,
      "evidence":{
        "usage_line":usage_line,
        "output_line":output_line,
        "output_flag":output_flag,
        "input_flag":input_flag,
        "positional_input":positional,
        "selector":selector,
        "requested_suffix":suffix,
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
