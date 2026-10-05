from __future__ import annotations
import hashlib, json, pathlib, re
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_BOUND_CLASS_ADMISSION_V1"
ALLOWED_CLASSES=frozenset({"READ_ONLY_DECLARED_QUERY","TEMPORARY_FILESYSTEM_TRANSFORM"})
ALLOWED_SITES={
 ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",32,"subprocess.run"):"TAR_LIST",
 ("canonical/runtime/bound_capabilities/jq_query.py",41,"subprocess.run"):"JQ",
 ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",44,"subprocess.run"):"TESSERACT_STDOUT",
 ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py",66,"subprocess.run"):"SQLITE_READ",
 ("canonical/runtime/bound_capabilities/yq_yaml_json.py",21,"subprocess.run"):"YQ",
 ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",29,"subprocess.run"):"PDFTOPPM_TEMP",
}
JQ_FORBIDDEN=(
 r"(?<![A-Za-z0-9_.])import\s+",
 r"(?<![A-Za-z0-9_.])include\s+",
 r"(?<![A-Za-z0-9_.])module\s+",
 r"(?<![A-Za-z0-9_.])input\s*\(",
 r"(?<![A-Za-z0-9_.])inputs\b",
 r"(?<![A-Za-z0-9_])env\.",
 r"\$ENV\b",
)

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _sha(value:Any)->str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _argv(req:Mapping[str,Any])->list[str]:
    cmd=req.get("command")
    if not isinstance(cmd,Mapping) or cmd.get("kind")!="ARGV":
        raise ValueError("COMMAND_NOT_ARGV")
    items=cmd.get("items")
    if not isinstance(items,list) or not items:
        raise ValueError("COMMAND_ITEMS_INVALID")
    out=[]
    for item in items:
        if not isinstance(item,Mapping) or item.get("kind")!="STRING" or not isinstance(item.get("value"),str):
            raise ValueError("COMMAND_ITEM_NOT_STRING")
        out.append(item["value"])
    return out

def _base(req:Mapping[str,Any])->tuple[tuple[str,int,str],str,list[str]]:
    cs=req.get("callsite")
    if not isinstance(cs,Mapping):
        raise ValueError("CALLSITE_MISSING")
    key=(str(cs.get("module_path") or ""),int(cs.get("lineno") or 0),str(cs.get("process_api") or ""))
    effect=str(cs.get("effect_class") or "")
    profile=ALLOWED_SITES.get(key)
    if effect not in ALLOWED_CLASSES or profile is None:
        raise ValueError("CLASS_OR_CALLSITE_NOT_ALLOWED")
    if req.get("api")!="subprocess.run" or key[2]!="subprocess.run":
        raise ValueError("API_NOT_ALLOWED")
    if req.get("env") is not None or req.get("input") is not None or req.get("shell") is not False:
        raise ValueError("AMBIENT_INPUT_FORBIDDEN")
    if req.get("stdin") not in (None,"DEVNULL"):
        raise ValueError("STDIN_FORBIDDEN")
    if req.get("capture_output") is not True or req.get("text") is not True:
        raise ValueError("CAPTURED_TEXT_REQUIRED")
    if req.get("stdout") is not None or req.get("stderr") is not None:
        raise ValueError("EXPLICIT_STDIO_FORBIDDEN")
    return key,profile,_argv(req)

def _basename(x:str)->str:
    return pathlib.PurePath(x).name

def _validate_profile(profile:str,argv:list[str],timeout:Any)->None:
    if profile=="TAR_LIST":
        if len(argv)!=3 or _basename(argv[0])!="tar" or argv[1]!="-tzf":
            raise ValueError("TAR_LIST_SHAPE")
    elif profile=="JQ":
        if _basename(argv[0])!="jq":
            raise ValueError("JQ_EXEC")
        offset=2 if len(argv)>=2 and argv[1]=="-r" else 1
        if len(argv)!=offset+2:
            raise ValueError("JQ_SHAPE")
        filt=argv[offset]
        if not filt or len(filt)>8000 or any(re.search(p,filt,flags=re.I) for p in JQ_FORBIDDEN):
            raise ValueError("JQ_FILTER")
    elif profile=="TESSERACT_STDOUT":
        if len(argv)!=7 or _basename(argv[0])!="tesseract" or argv[2]!="stdout" or argv[3]!="-l" or argv[5]!="--psm":
            raise ValueError("TESSERACT_SHAPE")
        if not argv[4].replace("+","").isalnum() or argv[6] not in {"3","6","7","11"}:
            raise ValueError("TESSERACT_OPTIONS")
    elif profile=="SQLITE_READ":
        if len(argv)!=4 or _basename(argv[0])!="sqlite3" or argv[1]!="-json":
            raise ValueError("SQLITE_SHAPE")
        sql=argv[3].strip()
        allowed=(re.match(r"(?is)^SELECT\s+",sql)
                 or re.fullmatch(r'(?is)PRAGMA\s+table_info\("[A-Za-z_][A-Za-z0-9_]{0,127}"\)',sql)
                 or re.fullmatch(r"(?is)PRAGMA\s+integrity_check",sql))
        if not allowed:
            raise ValueError("SQLITE_MUTATION")
    elif profile=="YQ":
        if len(argv)!=3 or _basename(argv[0])!="yq" or argv[1]!=".":
            raise ValueError("YQ_SHAPE")
    elif profile=="PDFTOPPM_TEMP":
        if len(argv)!=10 or _basename(argv[0])!="pdftoppm":
            raise ValueError("PDFTOPPM_SHAPE")
        if argv[1]!="-f" or argv[2]!="1" or argv[3]!="-l" or argv[5]!="-r" or argv[7]!="-png":
            raise ValueError("PDFTOPPM_OPTIONS")
        try:
            pages=int(argv[4]); dpi=int(argv[6])
        except Exception as exc:
            raise ValueError("PDFTOPPM_NUMERIC") from exc
        if not (1<=pages<=500 and 72<=dpi<=600):
            raise ValueError("PDFTOPPM_RANGE")
    else:
        raise ValueError("PROFILE_UNKNOWN")
    if timeout is not None:
        try:
            t=float(timeout)
        except Exception as exc:
            raise ValueError("TIMEOUT_INVALID") from exc
        maximum=300 if profile=="PDFTOPPM_TEMP" else 180
        if not (0<t<=maximum):
            raise ValueError("TIMEOUT_RANGE")

def make_authorizer(*,verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]]|None=None):
    if verifier is None:
        from canonical.runtime.root3_subprocess_final_authorizer_adapter_v2 import verify_mediator_request
        verifier=verify_mediator_request
    if not callable(verifier):
        raise TypeError("VERIFIER_NOT_CALLABLE")
    def authorize(req:Mapping[str,Any])->Mapping[str,Any]:
        try:
            verified=verifier(req)
            key,profile,argv=_base(verified)
            _validate_profile(profile,argv,verified.get("timeout"))
            proof={
              "schema":SCHEMA,
              "request_sha256":verified["request_sha256"],
              "effect_class":verified["callsite"]["effect_class"],
              "callsite":[key[0],key[1],key[2]],
              "profile":profile,
              "policy":"CLASS_BOUND_SHAPE_ADMISSION__EXECUTOR_REMAINS_FINAL_SEMANTIC_AND_CONFINEMENT_GATE",
            }
            return {"schema":SCHEMA,"allowed":True,"authorization_sha256":_sha(proof),"profile":profile,"acceptance_credit_delta":0}
        except Exception as exc:
            return {"schema":SCHEMA,"allowed":False,"reason":type(exc).__name__+":"+str(exc),"acceptance_credit_delta":0}
    return authorize
