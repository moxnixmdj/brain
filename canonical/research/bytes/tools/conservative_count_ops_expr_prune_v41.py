from pathlib import Path
import ast, hashlib, json

BASE = "f6c950d49791f05fbfc1e8985fde4c1b623b8087b62f89fc7d4a30f78e39e97a"
TARGET = "975445352f47077530dadacab2e387c227a9787b4b693678c740c3e3b080af38"

NEW = '''def count_ops(expr, visual=False):
    from sympy.integrals.integrals import Integral
    from sympy.concrete.summations import Sum
    from sympy.simplify.radsimp import fraction
    expr = sympify(expr)
    if not isinstance(expr, Expr) or expr.is_Relational:
        raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    ops = []
    args = [expr]
    NEG = Symbol('NEG'); DIV = Symbol('DIV'); SUB = Symbol('SUB'); ADD = Symbol('ADD'); EXP = Symbol('EXP')
    while args:
        a = args.pop()
        if a.is_Rational:
            if a is not S.One:
                if a.p < 0: ops.append(NEG)
                if a.q != 1: ops.append(DIV)
                continue
        elif a.is_Mul or a.is_MatMul:
            if _coeff_isneg(a):
                ops.append(NEG)
                if a.args[0] is S.NegativeOne: a = a.as_two_terms()[1]
                else: a = -a
            n, d = fraction(a)
            if n.is_Integer:
                ops.append(DIV)
                if n < 0: ops.append(NEG)
                args.append(d); continue
            elif d is not S.One:
                if not d.is_Integer: args.append(d)
                ops.append(DIV); args.append(n); continue
        elif a.is_Add or a.is_MatAdd:
            aargs = list(a.args); negs = 0
            for i, ai in enumerate(aargs):
                if _coeff_isneg(ai):
                    negs += 1; args.append(-ai)
                    if i > 0: ops.append(SUB)
                else:
                    args.append(ai)
                    if i > 0: ops.append(ADD)
            if negs == len(aargs): ops.append(NEG)
            elif _coeff_isneg(aargs[0]): ops.append(SUB - ADD)
            continue
        if a.is_Pow and a.exp is S.NegativeOne:
            ops.append(DIV); args.append(a.base); continue
        if a == S.Exp1:
            ops.append(EXP); continue
        if a.is_Pow and a.base == S.Exp1:
            ops.append(EXP); args.append(a.exp); continue
        if a.is_Mul or isinstance(a, LatticeOp):
            ops.append(Symbol(a.func.__name__.upper()) * (len(a.args) - 1))
        elif a.args and (a.is_Pow or a.is_Function or isinstance(a, (Derivative, Integral, Sum))):
            if isinstance(a.func, UndefinedFunction): o = Symbol('FUNC_' + a.func.__name__.upper())
            else: o = Symbol(a.func.__name__.upper())
            ops.append(o)
        if not a.is_Symbol: args.extend(a.args)
    if not ops: return S.Zero if visual else 0
    ops = Add(*ops)
    if visual: return ops
    if ops.is_Number: return int(ops)
    return sum((int((z.args or [1])[0]) for z in Add.make_args(ops)))
'''

def manifest(root):
    root = Path(root); items = []
    for p in sorted(root.rglob("*.py")):
        b = p.read_bytes()
        items.append({"path": p.relative_to(root).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    mb = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(mb).hexdigest(), items, mb

def apply(root):
    root = Path(root)
    before, _, _ = manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    p = root / "sympy/core/function.py"
    text = p.read_text(); lines = text.splitlines(True); tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "count_ops"]
    if len(nodes) != 1:
        raise RuntimeError("count_ops identity not unique")
    n = nodes[0]; a = n.lineno - 1; b = n.end_lineno
    old = "".join(lines[a:b]); lines[a:b] = [NEW]
    out = "".join(lines); compile(out, str(p), "exec"); p.write_text(out)
    after, items, mb = manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    (root / "BRAIN_SLICE_MANIFEST.json").write_bytes(mb + b"\n")
    return {"manifest": after, "saved": len(old.encode()) - len(NEW.encode()), "raw_python_source_bytes": sum(x["bytes"] for x in items)}

if __name__ == "__main__":
    import sys
    print(json.dumps(apply(sys.argv[1]), indent=2))
