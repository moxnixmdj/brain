"""Immutable create-once store backed by GitHub branch refs."""
import hashlib,json,re
from urllib.parse import quote
class StoreUnavailable(RuntimeError): pass
class RateLimited(StoreUnavailable): pass

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)
def _sha(v): return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{40}",v)
class GitHubRefStore:
    PREFIX="BRAIN_EXECUTION_GUARD_RECORD_V1\n"
    def __init__(self,request,repository,base_commit_sha,base_tree_sha,namespace="live-v1"):
        if not callable(request): raise ValueError("REQUEST_TRANSPORT_REQUIRED")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repository or ""): raise ValueError("INVALID_REPOSITORY")
        if not _sha(base_commit_sha) or not _sha(base_tree_sha): raise ValueError("INVALID_BASE_SHA")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}",namespace or ""): raise ValueError("INVALID_NAMESPACE")
        self.request=request; self.repository=repository; self.base_commit_sha=base_commit_sha; self.base_tree_sha=base_tree_sha; self.namespace=namespace
    def _request(self,method,path,payload=None):
        try: status,body,headers=self.request(method,path,payload)
        except Exception as exc: raise StoreUnavailable("TRANSPORT_UNCERTAIN_NO_RETRY") from exc
        if type(status) is not int or not isinstance(headers,dict): raise StoreUnavailable("MALFORMED_HTTP_REPLY")
        h={str(k).lower():v for k,v in headers.items()}; msg=str(body.get("message","")) if isinstance(body,dict) else ""
        if status==429 or (status==403 and (str(h.get("x-ratelimit-remaining"))=="0" or "rate limit" in msg.lower())): raise RateLimited("GITHUB_RATE_LIMIT_NO_RETRY")
        return status,body
    def _ref(self,key):
        if not isinstance(key,str) or not key or len(key)>4096: raise ValueError("INVALID_RECORD_KEY")
        d=hashlib.sha256(key.encode()).hexdigest(); short=f"execution-guard/{self.namespace}/{d}"; return short,"refs/heads/"+short
    def create(self,key,value):
        if not isinstance(value,dict): raise ValueError("RECORD_OBJECT_REQUIRED")
        rec=_canon(value)
        if len(rec.encode())>65536: raise ValueError("RECORD_TOO_LARGE")
        env={"schema":"BRAIN_GIT_REF_STORE_RECORD_V1","key":key,"record_sha256":hashlib.sha256(rec.encode()).hexdigest(),"record":value}
        _,full=self._ref(key)
        st,b=self._request("POST",f"/repos/{self.repository}/git/commits",{"message":self.PREFIX+_canon(env),"tree":self.base_tree_sha,"parents":[self.base_commit_sha]})
        if st!=201 or not isinstance(b,dict) or not _sha(b.get("sha")): raise StoreUnavailable("COMMIT_CREATE_NOT_CONFIRMED")
        commit=b["sha"]
        st,b=self._request("POST",f"/repos/{self.repository}/git/refs",{"ref":full,"sha":commit})
        if st==422: return False
        if st!=201 or not isinstance(b,dict) or b.get("ref")!=full or (b.get("object") or {}).get("sha")!=commit: raise StoreUnavailable("REF_CREATE_NOT_CONFIRMED")
        return True
    def read(self,key):
        short,_=self._ref(key)
        st,b=self._request("GET",f"/repos/{self.repository}/git/ref/heads/{quote(short,safe='/')}")
        if st==404: return None
        commit=(b.get("object") or {}).get("sha") if isinstance(b,dict) else None
        if st!=200 or not _sha(commit): raise StoreUnavailable("REF_READ_NOT_CONFIRMED")
        st,c=self._request("GET",f"/repos/{self.repository}/git/commits/{commit}")
        msg=c.get("message") if st==200 and isinstance(c,dict) else None
        if not isinstance(msg,str) or not msg.startswith(self.PREFIX): raise StoreUnavailable("RECORD_COMMIT_INVALID")
        try:
            env=json.loads(msg[len(self.PREFIX):]); record=env["record"]
            if env.get("schema")!="BRAIN_GIT_REF_STORE_RECORD_V1" or env.get("key")!=key or not isinstance(record,dict): raise ValueError
            if env.get("record_sha256")!=hashlib.sha256(_canon(record).encode()).hexdigest(): raise ValueError
        except Exception as exc: raise StoreUnavailable("MALFORMED_OR_CORRUPT_RECORD") from exc
        return record
