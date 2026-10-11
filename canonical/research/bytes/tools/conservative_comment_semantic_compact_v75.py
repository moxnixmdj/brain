from pathlib import Path
import ast, hashlib, io, json, re, tokenize, types
BASE = "b0b5024dbd831e104d25373dc2bc2c14feed5892624d3cae4d5100bfaa1eb18f"
TARGET = "42c3255fe51bc6e7c30afd912d3fd3aabc422742b4671eed1e7b7fc50ce290f9"

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes(); items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def _ast(s): return ast.dump(ast.parse(s,type_comments=True),include_attributes=False)
def _sig_tokens(s):
    out=[]
    for t in tokenize.generate_tokens(io.StringIO(s).readline):
        if t.type in (tokenize.COMMENT,tokenize.NL,tokenize.ENCODING,tokenize.ENDMARKER): continue
        out.append((t.type,t.string))
    return out
def _norm_const(x):
    if isinstance(x,types.CodeType): return _norm_code(x)
    if isinstance(x,tuple): return tuple(_norm_const(y) for y in x)
    if isinstance(x,frozenset): return ("frozenset",tuple(sorted(map(repr,x))))
    try: json.dumps(x); return x
    except Exception: return ("repr",repr(x))
def _norm_code(c):
    return (c.co_argcount,c.co_posonlyargcount,c.co_kwonlyargcount,c.co_nlocals,c.co_stacksize,c.co_flags,
            c.co_code,tuple(_norm_const(x) for x in c.co_consts),c.co_names,c.co_varnames,c.co_freevars,c.co_cellvars,
            getattr(c,"co_exceptiontable",b""))
def _candidate(text):
    lines=text.splitlines(keepends=True); comments={}
    for t in tokenize.generate_tokens(io.StringIO(text).readline):
        if t.type!=tokenize.COMMENT: continue
        ln,col=t.start
        if ln==1 and t.string.startswith("#!"): continue
        if ln<=2 and re.search(r"coding[:=]\s*[-\w.]+",t.string): continue
        comments.setdefault(ln,[]).append((col,t.end[1]))
    out=[]
    for i,line in enumerate(lines,1):
        if line.endswith("\r\n"): body,nl=line[:-2],"\r\n"
        elif line.endswith("\n") or line.endswith("\r"): body,nl=line[:-1],line[-1]
        else: body,nl=line,""
        for a,z in sorted(comments.get(i,()),reverse=True): body=body[:a]+body[z:]
        body=body.rstrip(" \t")
        if i in comments and not body.strip(): continue
        out.append(body+nl)
    return "".join(out)
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f"base manifest drift: {before}")
    changed=rejected=saved=0; details=[]
    for p in sorted(root.rglob("*.py")):
        old=p.read_text(encoding="utf-8"); new=_candidate(old)
        if new==old: continue
        try:
            ca=compile(old,str(p),"exec"); cb=compile(new,str(p),"exec")
            if _sig_tokens(old)!=_sig_tokens(new): raise ValueError("significant token drift")
            if _ast(old)!=_ast(new): raise ValueError("AST drift")
            if _norm_code(ca)!=_norm_code(cb): raise ValueError("recursive executable code drift")
        except Exception:
            rejected+=1; continue
        delta=len(old.encode())-len(new.encode())
        if delta<=0: continue
        p.write_text(new,encoding="utf-8",newline=""); changed+=1; saved+=delta; details.append((p.relative_to(root).as_posix(),delta))
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f"target manifest mismatch: {after}")
    (root/"BRAIN_SLICE_MANIFEST.json").write_bytes(mb+b"\n")
    return {"manifest":after,"changed_python_files":changed,"rejected_candidate_files":rejected,"saved_bytes":saved,"raw_python_source_bytes":sum(x["bytes"] for x in items),"details":details}
if __name__=="__main__":
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
