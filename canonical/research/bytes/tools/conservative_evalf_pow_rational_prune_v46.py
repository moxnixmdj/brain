from pathlib import Path
import ast, hashlib, json
BASE='3d7c21fdebe1db363cc3e4c5fdf57a2ddb76c5219cd832c34eab9a99d60f9576'
TARGET='92056a1de7d8c4a109dd6aca9bf295a9e3956a42a5f7672b321faf75aa842a9b'
PATH='sympy/core/evalf.py'; QUAL='evalf_pow'
NEW='''def evalf_pow(v, prec, options):\n    target_prec = prec\n    base, exp = v.args\n    if exp.is_Integer:\n        p = exp.p\n        if not p:\n            return (fone, None, prec, None)\n        prec += int(math.log2(abs(p)))\n        result = evalf(base, prec + 5, options)\n        if result is S.ComplexInfinity:\n            if p < 0:\n                return (None, None, None, None)\n            return result\n        re, im, re_acc, im_acc = result\n        if re and (not im):\n            return (mpf_pow_int(re, p, target_prec), None, target_prec, None)\n        if im and (not re):\n            z = mpf_pow_int(im, p, target_prec)\n            case = p % 4\n            if case == 0:\n                return (z, None, target_prec, None)\n            if case == 1:\n                return (None, z, None, target_prec)\n            if case == 2:\n                return (mpf_neg(z), None, target_prec, None)\n            return (None, mpf_neg(z), None, target_prec)\n        if not re:\n            if p < 0:\n                return S.ComplexInfinity\n            return (None, None, None, None)\n        re, im = libmp.mpc_pow_int((re, im), p, prec)\n        return finalize_complex(re, im, target_prec)\n    if not exp.is_Rational:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    result = evalf(base, prec + 5, options)\n    if result is S.ComplexInfinity:\n        if exp < 0:\n            return (None, None, None, None)\n        return result\n    if exp is S.Half:\n        xre, xim, _, _ = result\n        if xim:\n            re, im = libmp.mpc_sqrt((xre or fzero, xim), prec)\n            return finalize_complex(re, im, prec)\n        if not xre:\n            return (None, None, None, None)\n        if mpf_lt(xre, fzero):\n            return (None, mpf_sqrt(mpf_neg(xre), prec), None, prec)\n        return (mpf_sqrt(xre, prec), None, prec, None)\n    prec += 10\n    yre, yim, _, _ = evalf(exp, prec, options)\n    if yim or not yre:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    ysize = fastlog(yre)\n    if ysize > 5:\n        prec += ysize\n        yre, yim, _, _ = evalf(exp, prec, options)\n        if yim or not yre:\n            raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    if base is S.Exp1:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    xre, xim, _, _ = evalf(base, prec + 5, options)\n    if not (xre or xim):\n        if yre[0] == 1:\n            return S.ComplexInfinity\n        return (None, None, None, None)\n    if xim:\n        re, im = libmp.mpc_pow_mpf((xre or fzero, xim), yre, target_prec)\n        return finalize_complex(re, im, target_prec)\n    if mpf_lt(xre, fzero):\n        re, im = libmp.mpc_pow_mpf((xre, fzero), yre, target_prec)\n        return finalize_complex(re, im, target_prec)\n    return (mpf_pow(xre, yre, target_prec), None, target_prec, None)\n'''
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode(); return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    p=root/PATH; text=p.read_text(); tree=ast.parse(text); hits=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==QUAL]
    if len(hits)!=1: raise RuntimeError(f'{QUAL} identity count: {len(hits)}')
    n=hits[0]; lines=text.splitlines(True); old=''.join(lines[n.lineno-1:n.end_lineno]); lines[n.lineno-1:n.end_lineno]=[NEW]
    out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':len(old.encode())-len(NEW.encode()),'raw_python_source_bytes':sum(x['bytes'] for x in items),'changed':[[PATH,QUAL]]}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
