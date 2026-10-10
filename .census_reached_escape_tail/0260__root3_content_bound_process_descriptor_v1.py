from __future__ import annotations
import hashlib,json,os,pathlib,re,threading
from collections.abc import Mapping
from typing import Any
SCHEMA="PROJECT_BRAIN_ROOT3_CONTENT_BOUND_PROCESS_DESCRIPTOR_V1"
PROFILE="REPOSITORY_TEST_EXECUTION"
SNAPSHOT_MODE="GIT_COMMIT_ARCHIVE_TO_PRIVATE_NAMESPACE_TMPFS"
SHA256_RE=re.compile(r"^[0-9a-f]{64}$"); SHA1_RE=re.compile(r"^[0-9a-f]{40}$")
SUPPORTED={
 ("canonical/runtime/astra_runtime.py",1215,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/python_test_audit.py",50,"subprocess.run"),
}
class ProcessDescriptorError(ValueError): pass
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha256(raw): return hashlib.sha256(raw).hexdigest()
def _file_binding(path):
    if path.is_symlink() or not path.is_file(): raise ProcessDescriptorError("BOUND_FILE_NOT_REGULAR_OR_IS_SYMLINK:"+str(path))
    raw=path.read_bytes(); return {"sha256":_sha256(raw),"bytes":len(raw)}
def _git_dir(root):
    marker=root/".git"
    if marker.is_dir(): return marker.resolve()
    if marker.is_file():
        text=marker.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"): raise ProcessDescriptorError("GITDIR_FILE_INVALID")
        raw=text.split(":",1)[1].strip()
        gd=(root/raw).resolve() if not os.path.isabs(raw) else pathlib.Path(raw).resolve()
        if not gd.is_dir(): raise ProcessDescriptorError("GITDIR_TARGET_MISSING")
        return gd
    raise ProcessDescriptorError("GIT_METADATA_MISSING")
def resolve_head_commit(repo_root):
    root=pathlib.Path(repo_root).resolve(); gd=_git_dir(root)
    head=(gd/"HEAD").read_text(encoding="utf-8").strip()
    if SHA1_RE.fullmatch(head): return head
    if not head.startswith("ref: "): raise ProcessDescriptorError("GIT_HEAD_INVALID")
    ref=head[5:].strip()
    if not ref or ref.startswith("/") or ".." in pathlib.PurePosixPath(ref).parts: raise ProcessDescriptorError("GIT_HEAD_REF_INVALID")
    loose=gd.joinpath(*pathlib.PurePosixPath(ref).parts)
    if loose.is_file():
        val=loose.read_text(encoding="utf-8").strip()
        if SHA1_RE.fullmatch(val): return val
        raise ProcessDescriptorError("GIT_LOOSE_REF_INVALID")
    packed=gd/"packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"): continue
            try: val,name=line.split(" ",1)
            except ValueError: continue
            if name==ref:
                if not SHA1_RE.fullmatch(val): raise ProcessDescriptorError("GIT_PACKED_REF_INVALID")
                return val
    raise ProcessDescriptorError("GIT_HEAD_REF_UNRESOLVED:"+ref)
def _argv_strings(req):
    command=req.get("command")
    if not isinstance(command,Mapping) or command.get("kind")!="ARGV": raise ProcessDescriptorError("COMMAND_NOT_ARGV")
    items=command.get("items")
    if not isinstance(items,list) or len(items)!=2: raise ProcessDescriptorError("REPOSITORY_TEST_ARGV_MUST_HAVE_EXACTLY_TWO_ITEMS")
    out=[]
    for item in items:
        if not isinstance(item,Mapping) or item.get("kind")!="STRING": raise ProcessDescriptorError("REPOSITORY_TEST_ARGV_ITEM_NOT_STRING")
        value=item.get("value")
        if not isinstance(value,str) or not value or chr(0) in value: raise ProcessDescriptorError("REPOSITORY_TEST_ARGV_STRING_INVALID")
        out.append(value)
    return out
def _inside(root,raw,label):
    p=pathlib.Path(raw); p=p.resolve() if p.is_absolute() else (root/p).resolve()
    try: rel=p.relative_to(root)
    except ValueError as exc: raise ProcessDescriptorError(label+"_OUTSIDE_REPOSITORY") from exc
    return p,rel.as_posix()
def build_repository_test_descriptor(req,repo_root):
    if not isinstance(req,Mapping): raise ProcessDescriptorError("MEDIATOR_REQUEST_INVALID")
    req_sha=req.get("request_sha256")
    if not isinstance(req_sha,str) or SHA256_RE.fullmatch(req_sha) is None: raise ProcessDescriptorError("MEDIATOR_REQUEST_SHA256_INVALID")
    cs=req.get("callsite")
    if not isinstance(cs,Mapping): raise ProcessDescriptorError("CALLSITE_MISSING")
    key=(str(cs.get("module_path") or ""),int(cs.get("lineno") or 0),str(cs.get("process_api") or ""))
    if key not in SUPPORTED: raise ProcessDescriptorError("CALLSITE_NOT_REPOSITORY_TEST_PROFILE:"+repr(key))
    if cs.get("effect_class")!="BOUND_CHILD_CODE_EXECUTION": raise ProcessDescriptorError("EFFECT_CLASS_MISMATCH")
    if req.get("api")!="subprocess.run": raise ProcessDescriptorError("PROCESS_API_MISMATCH")
    if req.get("shell") is not False: raise ProcessDescriptorError("SHELL_FORBIDDEN")
    if req.get("capture_output") is not True or req.get("text") is not True: raise ProcessDescriptorError("TEXT_CAPTURE_REQUIRED")
    if req.get("env") is not None or req.get("input") is not None: raise ProcessDescriptorError("CUSTOM_ENV_OR_INPUT_FORBIDDEN")
    root=pathlib.Path(repo_root).resolve()
    if not root.is_dir(): raise ProcessDescriptorError("REPOSITORY_ROOT_MISSING")
    cwd=req.get("cwd")
    if not isinstance(cwd,str) or pathlib.Path(cwd).resolve()!=root: raise ProcessDescriptorError("CWD_MUST_EQUAL_REPOSITORY_ROOT")
    interpreter_raw,test_raw=_argv_strings(req)
    interpreter=pathlib.Path(interpreter_raw).resolve()
    if not interpreter.is_absolute() or not (str(interpreter).startswith("/usr/") or str(interpreter).startswith("/bin/")): raise ProcessDescriptorError("INTERPRETER_NOT_SYSTEM_PATH")
    ib=_file_binding(interpreter)
    test_path,test_rel=_inside(root,test_raw,"TEST_PATH")
    if test_path.suffix!=".py": raise ProcessDescriptorError("TEST_PATH_NOT_PYTHON")
    tb=_file_binding(test_path)
    timeout=req.get("timeout")
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not (0<float(timeout)<=600): raise ProcessDescriptorError("TIMEOUT_INVALID")
    core={"schema":SCHEMA,"profile":PROFILE,"snapshot_mode":SNAPSHOT_MODE,"mediator_request_sha256":req_sha,
          "callsite":{"module_path":key[0],"lineno":key[1],"process_api":key[2]},
          "repository_head_commit_sha1":resolve_head_commit(root),"test_path":test_rel,"test_sha256":tb["sha256"],"test_bytes":tb["bytes"],
          "interpreter_path":str(interpreter),"interpreter_sha256":ib["sha256"],"interpreter_bytes":ib["bytes"],
          "timeout_seconds":float(timeout),"material_child_commit":"DENY","network":"PRIVATE_NAMESPACE_ONLY"}
    return {**core,"descriptor_sha256":_sha256(_canon(core))}
def verify_repository_test_descriptor(desc,req,repo_root):
    expected=build_repository_test_descriptor(req,repo_root)
    if not isinstance(desc,Mapping) or dict(desc)!=expected: raise ProcessDescriptorError("DESCRIPTOR_CONTENT_OR_HASH_MISMATCH")
    return expected
class AuthorizedDescriptorStore:
    def __init__(self): self._lock=threading.RLock(); self._items={}
    def put_once(self,k,d):
        if not isinstance(k,str) or SHA256_RE.fullmatch(k) is None: raise ProcessDescriptorError("STORE_REQUEST_SHA256_INVALID")
        if not isinstance(d,Mapping): raise ProcessDescriptorError("STORE_DESCRIPTOR_INVALID")
        with self._lock:
            if k in self._items: raise ProcessDescriptorError("STORE_DUPLICATE_REQUEST")
            self._items[k]=dict(d)
    def consume(self,k):
        with self._lock: item=self._items.pop(k,None)
        if item is None: raise ProcessDescriptorError("STORE_BINDING_MISSING_OR_ALREADY_CONSUMED")
        return item
    def discard(self,k):
        with self._lock: self._items.pop(k,None)
    def __len__(self):
        with self._lock: return len(self._items)
