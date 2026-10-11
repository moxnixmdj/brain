"""Pinned host-media transformations for OSWorld 2.1.

Guest files are pulled through the official PythonController, transformed with
the OSWorld host's pinned ffmpeg/ffprobe commands, uploaded through the official
SetupController, then pulled again for byte-level postcondition verification.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

SAFE_ROOT="/home/oai"
MAX_MEDIA_BYTES=600_000_000


class MediaOpsError(RuntimeError):
    pass


def _path(value:Any)->str:
    if not isinstance(value,str) or not value.startswith(SAFE_ROOT+"/"):
        raise MediaOpsError("MEDIA_PATH_OUTSIDE_SAFE_ROOT")
    p=PurePosixPath(value)
    if ".." in p.parts:
        raise MediaOpsError("MEDIA_PATH_TRAVERSAL_FORBIDDEN")
    text=str(p)
    if any(x in text for x in ("/evaluation_examples","/benchmark_releases","osworld_v2_tasks","desktop_env/evaluators")):
        raise MediaOpsError("MEDIA_PATH_PROTECTED")
    return text


def _number(value:Any,name:str,lo:float,hi:float)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise MediaOpsError(name+"_INVALID")
    out=float(value)
    if not lo<=out<=hi:
        raise MediaOpsError(name+"_OUT_OF_RANGE")
    return out


def _integer(value:Any,name:str,lo:int,hi:int)->int:
    if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:
        raise MediaOpsError(name+"_INVALID")
    return value


@dataclass
class OSWorldHostMediaOps:
    environment:Any|None=None

    def bind_environment(self,environment:Any)->None:
        controller=getattr(environment,"controller",None)
        setup=getattr(environment,"setup_controller",None)
        if controller is None or not callable(getattr(controller,"get_file",None)):
            raise MediaOpsError("MEDIA_GET_FILE_UNAVAILABLE")
        if setup is None or not callable(getattr(setup,"download",None)):
            raise MediaOpsError("MEDIA_UPLOAD_UNAVAILABLE")
        self.environment=environment

    def _pull(self,guest_path:str)->bytes:
        if self.environment is None:
            raise MediaOpsError("MEDIA_ENVIRONMENT_NOT_BOUND")
        data=self.environment.controller.get_file(guest_path)
        if not isinstance(data,(bytes,bytearray)) or not data:
            raise MediaOpsError("MEDIA_INPUT_UNAVAILABLE")
        data=bytes(data)
        if len(data)>MAX_MEDIA_BYTES:
            raise MediaOpsError("MEDIA_INPUT_TOO_LARGE")
        return data

    def _probe_local(self,path:Path)->dict[str,Any]:
        exe=shutil.which("ffprobe")
        if not exe:
            raise MediaOpsError("PINNED_FFPROBE_UNAVAILABLE")
        r=subprocess.run(
            [exe,"-v","error","-show_streams","-show_format","-of","json",str(path)],
            capture_output=True,text=True,timeout=60,check=False,
        )
        if r.returncode!=0:
            raise MediaOpsError("FFPROBE_FAILED:"+r.stderr[-1000:])
        try:
            out=json.loads(r.stdout)
        except Exception as exc:
            raise MediaOpsError("FFPROBE_JSON_INVALID") from exc
        return out if isinstance(out,dict) else {}

    def _transform(self,input_path:str,output_path:str,args:list[str])->dict[str,Any]:
        source=self._pull(input_path)
        exe=shutil.which("ffmpeg")
        if not exe:
            raise MediaOpsError("PINNED_FFMPEG_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="brain-osw-media-") as td:
            root=Path(td)
            src=root/("input"+PurePosixPath(input_path).suffix)
            dst=root/("output"+PurePosixPath(output_path).suffix)
            src.write_bytes(source)
            bound=[str(src) if x=="{input}" else x for x in args]
            if "{input}" not in args:
                raise MediaOpsError("MEDIA_INPUT_PLACEHOLDER_MISSING")
            cmd=[exe,"-hide_banner","-loglevel","error","-y",*bound,str(dst)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,check=False)
            if r.returncode!=0 or not dst.is_file() or dst.stat().st_size<=0:
                raise MediaOpsError("FFMPEG_TRANSFORM_FAILED:"+r.stderr[-1500:])
            local_bytes=dst.read_bytes()
            local_sha=hashlib.sha256(local_bytes).hexdigest()
            probe=self._probe_local(dst)
            self.environment.setup_controller.download([{"url":str(dst),"path":output_path}])
            guest_bytes=self._pull(output_path)
            guest_sha=hashlib.sha256(guest_bytes).hexdigest()
            if guest_sha!=local_sha or len(guest_bytes)!=len(local_bytes):
                raise MediaOpsError("MEDIA_UPLOAD_READBACK_MISMATCH")
            return {
                "ok":True,"input":input_path,"output":output_path,
                "bytes":len(guest_bytes),"sha256":guest_sha,"probe":probe,
            }

    def run(self,payload:Mapping[str,Any])->dict[str,Any]:
        if not isinstance(payload,Mapping):
            raise MediaOpsError("MEDIA_OP_NOT_OBJECT")
        op=str(payload.get("operation") or "").strip().upper()
        a=payload.get("args",{})
        if not isinstance(a,Mapping):
            raise MediaOpsError("MEDIA_ARGS_NOT_OBJECT")

        if op=="PROBE":
            src=_path(a.get("input"))
            data=self._pull(src)
            with tempfile.TemporaryDirectory(prefix="brain-osw-probe-") as td:
                p=Path(td)/("input"+PurePosixPath(src).suffix)
                p.write_bytes(data)
                probe=self._probe_local(p)
            result={"ok":True,"input":src,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"probe":probe}

        elif op=="TRIM":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            start=_number(a.get("start_s"),"START",0,86400)
            end=_number(a.get("end_s"),"END",0,86400)
            if end<=start: raise MediaOpsError("TRIM_RANGE_INVALID")
            result=self._transform(src,dst,["-ss",str(start),"-i","{input}","-t",str(end-start)])

        elif op=="RESIZE":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            w=_integer(a.get("width"),"WIDTH",1,8192); h=_integer(a.get("height"),"HEIGHT",1,8192)
            result=self._transform(src,dst,["-i","{input}","-vf",f"scale={w}:{h}"])

        elif op=="CROP":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            w=_integer(a.get("width"),"WIDTH",1,8192); h=_integer(a.get("height"),"HEIGHT",1,8192)
            x=_integer(a.get("x"),"X",0,8192); y=_integer(a.get("y"),"Y",0,8192)
            result=self._transform(src,dst,["-i","{input}","-vf",f"crop={w}:{h}:{x}:{y}"])

        elif op=="ROTATE":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            deg=_integer(a.get("degrees"),"DEGREES",0,360)
            filters={90:"transpose=1",180:"hflip,vflip",270:"transpose=2"}
            if deg not in filters: raise MediaOpsError("ROTATION_UNSUPPORTED")
            result=self._transform(src,dst,["-i","{input}","-vf",filters[deg]])

        elif op=="EXTRACT_AUDIO":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            suffix=PurePosixPath(dst).suffix.casefold()
            codec={".wav":["-c:a","pcm_s16le"],".mp3":["-c:a","libmp3lame"],".m4a":["-c:a","aac"]}.get(suffix,[])
            result=self._transform(src,dst,["-i","{input}","-vn",*codec])

        elif op=="SET_VOLUME":
            src=_path(a.get("input")); dst=_path(a.get("output"))
            factor=_number(a.get("factor"),"VOLUME_FACTOR",0,10)
            result=self._transform(src,dst,["-i","{input}","-af",f"volume={factor}"])

        else:
            raise MediaOpsError("MEDIA_OPERATION_NOT_ALLOWED:"+op)

        return {"type":"MEDIA_OP","ok":result.get("ok") is True,"operation":op,"result":result}
