"""Isolated child-process loader for native-risk bound capability adapters.

This module exists to keep native-extension imports out of the parent ASTRA
runtime. It is not a sandbox and does not claim that child-process effects are
safe or mediated. Root3 classifies all effects inside this process under the
separate child-process residual.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
MAX_JSON_BYTES=8_000_000
ALLOWED_ADAPTERS={
    "python_library_codec",
    "docx_report_from_json",
    "python_document_builder",
    "xlsx_verify_openpyxl",
}


class IsolatedAdapterError(ValueError):
    pass


def _token(value: str, label: str) -> str:
    value=str(value or "")
    if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in value):
        raise IsolatedAdapterError(label+"_INVALID")
    return value


def _result_path(raw: str) -> pathlib.Path:
    p=pathlib.Path(raw).resolve()
    temp_root=pathlib.Path(tempfile.gettempdir()).resolve()
    if p.parent.parent!=temp_root or not p.parent.name.startswith("project-brain-isolated-cap-"):
        raise IsolatedAdapterError("RESULT_PATH_OUTSIDE_DEDICATED_TEMP_DIR")
    return p


def execute(module_name: str, entrypoint: str, raw_input: bytes, result_path: pathlib.Path) -> None:
    module_name=_token(module_name,"MODULE")
    entrypoint=_token(entrypoint,"ENTRYPOINT")
    if module_name not in ALLOWED_ADAPTERS:
        raise IsolatedAdapterError("MODULE_NOT_ALLOWLISTED:"+module_name)
    if len(raw_input)>MAX_JSON_BYTES:
        raise IsolatedAdapterError("INPUT_TOO_LARGE")
    try:
        payload=json.loads(raw_input.decode("utf-8"))
    except Exception as exc:
        raise IsolatedAdapterError("INPUT_JSON_INVALID") from exc
    if not isinstance(payload,dict) or set(payload)!={"args"} or not isinstance(payload["args"],dict):
        raise IsolatedAdapterError("INPUT_SCHEMA_INVALID")

    path=ROOT/"canonical"/"runtime"/"bound_capabilities"/(module_name+".py")
    if not path.is_file():
        raise IsolatedAdapterError("ADAPTER_MISSING:"+module_name)
    spec=importlib.util.spec_from_file_location("project_brain_isolated_"+module_name,path)
    if spec is None or spec.loader is None:
        raise IsolatedAdapterError("ADAPTER_LOAD_FAILED:"+module_name)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    fn=getattr(module,entrypoint,None)
    if not callable(fn):
        raise IsolatedAdapterError("ENTRYPOINT_MISSING:"+entrypoint)
    result=fn(dict(payload["args"]),ROOT)
    if not isinstance(result,dict):
        raise IsolatedAdapterError("RESULT_NOT_OBJECT")
    try:
        raw=json.dumps(
            result,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
        ).encode("utf-8")
    except Exception as exc:
        raise IsolatedAdapterError("RESULT_NOT_JSON") from exc
    if len(raw)>MAX_JSON_BYTES:
        raise IsolatedAdapterError("RESULT_TOO_LARGE")
    result_path.write_bytes(raw)


def main() -> None:
    if len(sys.argv)!=4:
        raise SystemExit("usage: runner MODULE ENTRYPOINT RESULT_PATH")
    module_name,entrypoint=sys.argv[1],sys.argv[2]
    result_path=_result_path(sys.argv[3])
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    try:
        execute(module_name,entrypoint,raw,result_path)
    except Exception as exc:
        print(type(exc).__name__+":"+str(exc),file=sys.stderr)
        raise SystemExit(2)


if __name__=="__main__":
    main()
