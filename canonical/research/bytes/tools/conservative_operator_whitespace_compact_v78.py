from pathlib import Path
import tokenize, io, hashlib, json
BASE='b03d2329afd48ac7f66fa8c90bd52d1bd454cf15547b67e305fabb2e1fb3111a'
TARGET='e4e5e57c5c41f738ced105271d4e4bb907eaa1afe33e01788204009d49315f60'
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    gaps=saved=changed=0
    for p in sorted(root.rglob('*.py')):
        old=p.read_text(); lines=old.splitlines(True)
        toks=[t for t in tokenize.generate_tokens(io.StringIO(old).readline)
              if t.type not in (tokenize.ENCODING,tokenize.INDENT,tokenize.DEDENT,tokenize.NEWLINE,tokenize.NL,tokenize.ENDMARKER,tokenize.COMMENT)]
        edits={}
        for a,b in zip(toks,toks[1:]):
            if a.end[0]!=b.start[0]: continue
            row=a.end[0]; c1=a.end[1]; c2=b.start[1]
            if c2<=c1: continue
            gap=lines[row-1][c1:c2]
            if gap and gap.strip(' \t')=='' and (a.type==tokenize.OP or b.type==tokenize.OP):
                edits.setdefault(row,[]).append((c1,c2))
        for row,es in edits.items():
            ln=lines[row-1]
            for c1,c2 in sorted(es,reverse=True):
                gaps+=1; saved+=len(ln[c1:c2].encode()); ln=ln[:c1]+ln[c2:]
            lines[row-1]=ln
        out=''.join(lines); compile(out,str(p),'exec')
        if out!=old: changed+=1; p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':saved,'removed_whitespace_gaps':gaps,'changed_python_files':changed,'raw_python_source_bytes':sum(x['bytes'] for x in items)}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
