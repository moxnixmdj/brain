#!/usr/bin/env python3
"""Infer a bounded, auditable CLI invocation contract from probe evidence.

The contract describes I/O shape rather than a task recipe. Supported
structural modes are deliberately small: output option, positional artifact,
stdout capture; and flagged, positional, or stdin text input. Semantic
translation into tool-specific languages is outside this layer and fails
closed when it cannot be bound literally.
"""
from __future__ import annotations
import json,pathlib,re,sys

class ContractInferenceFailure(RuntimeError): pass

MAGIC_BY_SUFFIX={
    ".png":"89504e470d0a1a0a",
    ".jpg":"ffd8ff",
    ".jpeg":"ffd8ff",
    ".pdf":"25504446",
    ".sqlite":"53514c69746520666f726d6174203300",
    ".sqlite3":"53514c69746520666f726d6174203300",
    ".db":"53514c69746520666f726d6174203300",
}
TEXT_SUFFIXES={".md",".markdown",".txt",".csv",".tsv",".json",".html",".htm",".xml"}
TEXT_FORMAT_NAMES={
    ".md":"markdown",".markdown":"markdown",".txt":"text",".csv":"csv",
    ".tsv":"tsv",".json":"json",".html":"html",".htm":"html",".xml":"xml",
}
FILE_TOKENS=("FILE","FILENAME","PATH","DATABASE","DB","OUTPUT","OUTFILE")
TEXT_TOKENS=("STRING","TEXT","DATA","SQL","QUERY","EXPRESSION","COMMAND")

def _help_text(probe):
    choices=[]
    for exe in probe.get("executables",[]):
        for att in exe.get("help_attempts",[]):
            text=str(att.get("text") or "")
            lower=text.lower()
            if not text:
                continue
            if "usage:" in lower or "options:" in lower:
                quality=4 if "usage:" in lower else 3
                choices.append((quality,len(text),exe.get("executable"),text))
                continue
            option_lines=[
                line for line in text.splitlines()
                if re.search(r"(?:^|\s)-[A-Za-z0-9](?:,|\s)|--[A-Za-z0-9]",line)
            ]
            io_markers=("output","write","file","stdin","stdout","input","convert","query","database","expression","data")
            if len(option_lines)>=3 and any(k in lower for k in io_markers):
                choices.append((2,len(text),exe.get("executable"),text))
    if not choices:
        raise ContractInferenceFailure("CLI_HELP_CONTRACT_TEXT_REQUIRED")
    choices.sort(reverse=True)
    _,_,exe,text=choices[0]
    return str(exe),text

def _goal_output(goal):
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(goal or ""))
    paths=[x.rstrip(".,;:!?)]}") for x in paths]
    if len(paths)!=1:
        raise ContractInferenceFailure("CLI_OUTPUT_PATH_UNRESOLVED:"+str(len(paths)))
    output_path=paths[0]
    suffix=pathlib.Path(output_path).suffix.lower()
    magic=MAGIC_BY_SUFFIX.get(suffix)
    text_output=suffix in TEXT_SUFFIXES
    if not magic and not text_output:
        raise ContractInferenceFailure("CLI_OUTPUT_FORMAT_UNVERIFIABLE:"+suffix)
    return output_path,suffix,magic,text_output

def _short_or_long_flag(line):
    m=re.search(r"(?:^|\s)(-[A-Za-z0-9])(?:\s|,)",line)
    if m:
        return m.group(1)
    m=re.search(r"(?<!\w)(--[A-Za-z0-9][A-Za-z0-9-]*)",line)
    return m.group(1) if m else None

def _output_flag(lines):
    for line in lines:
        ll=line.lower()
        if any(x in ll for x in ("--output","output file","write image to","write output to","save to file")):
            flag=_short_or_long_flag(line)
            if flag:
                return flag,line.strip()
    return None,None

def _usage_payload_role(usage_line):
    if not usage_line:
        return None,None
    upper=usage_line.upper()
    for token in TEXT_TOKENS:
        if re.search(r"(?<![A-Z])(?:\[|<)?"+re.escape(token)+r"(?:\]|>)?(?![A-Z])",upper):
            return "POSITIONAL_TEXT",token.lower()
    return None,None

def _input_flag(lines):
    for line in lines:
        ll=line.lower()
        if any(x in ll for x in ("--data","string to encode","data to encode","--query","--expression","query to execute","expression to evaluate")):
            flag=_short_or_long_flag(line)
            if flag:
                return flag
    return None

def _stdin_supported(help_text,usage_line):
    low=(help_text+"\n"+str(usage_line or "")).lower()
    return any(x in low for x in ("standard input","stdin","read from -","read input from standard"))

def _positional_artifact_supported(usage_line,command,suffix,help_text):
    if not usage_line:
        return None
    upper=usage_line.upper()
    candidates=[]
    for token in FILE_TOKENS:
        if re.search(r"(?<![A-Z])(?:\[|<)?"+re.escape(token)+r"(?:\]|>)?(?![A-Z])",upper):
            candidates.append(token)
    unique=list(dict.fromkeys(candidates))
    if len(unique)!=1:
        return None
    fmt=suffix.lstrip(".").lower()
    aliases={
      "sqlite3":{"sqlite","sqlite3","database"},
      "sqlite":{"sqlite","sqlite3","database"},
      "db":{"database","sqlite","db"},
    }
    signals=aliases.get(fmt,{fmt})
    identity=(command+" "+help_text).lower()
    if not any(sig and sig in identity for sig in signals):
        return None
    return unique[0]

def _stdout_supported(help_text,usage_line,text_output):
    if not text_output:
        return False
    low=(help_text+"\n"+str(usage_line or "")).lower()
    return any(x in low for x in ("stdout","standard output","print","writes result","write result","output to standard"))

def infer_contract(probe, goal):
    exe,help_text=_help_text(probe)
    lines=help_text.splitlines()
    usage_line=next((x.strip() for x in lines if x.strip().lower().startswith("usage:")),None)
    lower_help=help_text.lower()
    command=pathlib.Path(exe).name

    _,suffix,magic,text_output=_goal_output(goal)
    format_name=suffix.lstrip(".")
    aliases={"jpg":"jpeg","sqlite3":"sqlite","db":"database"}
    wanted=TEXT_FORMAT_NAMES.get(suffix,aliases.get(format_name,format_name))
    identity=(command+" "+help_text).lower()
    signals={wanted,format_name}
    if format_name in {"sqlite","sqlite3","db"}:
        signals.update({"sqlite","database"})
    if wanted and not any(x and x in identity for x in signals):
        raise ContractInferenceFailure("CLI_OUTPUT_FORMAT_UNSUPPORTED:"+suffix)

    out_flag,out_line=_output_flag(lines)
    positional_output=None
    stdout_capture=False
    if out_flag:
        output_mode="OUTPUT_FLAG"
    else:
        positional_output=_positional_artifact_supported(usage_line,command,suffix,help_text)
        if positional_output:
            output_mode="POSITIONAL_ARTIFACT"
        elif _stdout_supported(help_text,usage_line,text_output):
            output_mode="STDOUT_CAPTURE"
            stdout_capture=True
        else:
            raise ContractInferenceFailure("CLI_OUTPUT_BINDING_UNRESOLVED")

    input_flag=_input_flag(lines)
    positional_role,positional_name=_usage_payload_role(usage_line)
    stdin_supported=_stdin_supported(help_text,usage_line)
    if input_flag:
        input_mode="INPUT_FLAG"
    elif positional_role:
        input_mode="POSITIONAL_TEXT"
    elif stdin_supported:
        input_mode="STDIN_TEXT"
    else:
        input_mode="NONE"

    selector=[]
    normalized_goal=re.sub(r"[^a-z0-9]+","",str(goal).lower())
    if "code128" in normalized_goal:
        barcode_flag=None
        for line in lines:
            ll=line.lower()
            if "--barcode" in ll and ("type" in ll or "symbolog" in ll):
                barcode_flag=_short_or_long_flag(line)
                if barcode_flag:
                    break
        if barcode_flag:
            selector=[barcode_flag,"CODE128"]
        elif "code128" in lower_help or "code 128" in lower_help:
            for line in lines:
                if "encoding type" in line.lower():
                    flag=_short_or_long_flag(line)
                    if flag:
                        selector=[flag,"code128"]
                        break

    required_inputs=["output_path"]
    argv=[command,*selector]
    if output_mode=="OUTPUT_FLAG":
        argv.extend([out_flag,"__OUTPUT_PLACEHOLDER__"])
    elif output_mode=="POSITIONAL_ARTIFACT":
        argv.append("__OUTPUT_PLACEHOLDER__")

    stdin_template=None
    if input_mode=="INPUT_FLAG":
        required_inputs.insert(0,"text")
        argv.extend([input_flag,"__TEXT_PLACEHOLDER__"])
    elif input_mode=="POSITIONAL_TEXT":
        required_inputs.insert(0,"text")
        argv.append("__TEXT_PLACEHOLDER__")
    elif input_mode=="STDIN_TEXT":
        required_inputs.insert(0,"text")
        stdin_template="__TEXT_PLACEHOLDER__"

    argv=[x.replace("__OUTPUT_PLACEHOLDER__","$"+"{input.output_path}").replace("__TEXT_PLACEHOLDER__","$"+"{input.text}") for x in argv]
    if stdin_template is not None:
        stdin_template=stdin_template.replace("__TEXT_PLACEHOLDER__","$"+"{input.text}")

    return {
      "schema":"PROJECT_BRAIN_CLI_CONTRACT_CANDIDATE_V2",
      "status":"CANDIDATE_REQUIRES_EFFECT_VERIFICATION",
      "executable":exe,
      "command":command,
      "required_inputs":required_inputs,
      "io_contract":{
        "input_mode":input_mode,
        "output_mode":output_mode,
        "positional_output_token":positional_output,
        "positional_input_token":positional_name,
      },
      "argv_template":argv,
      "stdin_template":stdin_template,
      "output_path_template":"$"+"{input.output_path}",
      "capture_stdout_to_output":bool(stdout_capture),
      "output_prefix_hex":magic or "",
      "output_text_utf8":bool(text_output),
      "timeout_s":60,
      "evidence":{
        "usage_line":usage_line,
        "output_line":out_line,
        "output_flag":out_flag,
        "input_flag":input_flag,
        "input_mode":input_mode,
        "output_mode":output_mode,
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
