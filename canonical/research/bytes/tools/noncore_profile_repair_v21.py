from pathlib import Path
import ast,json,hashlib
BASE="45adf82ebe04814cdb5827821ee9d079f48dbc5f58d35f8b7a4a6d4e512deacb"
TARGET="0fa7fd19f6a674e493954d48f7438285dbab4fd9eefe559a3d537ca9834c6022"
SELECT=set(tuple(x) for x in [('sympy/core/kind.py', 'KindDispatcher.__doc__'), ('sympy/core/function.py', 'Lambda.__new__'), ('sympy/polys/polyroots.py', 'roots_quintic'), ('sympy/simplify/simplify.py', 'nc_simplify'), ('sympy/utilities/lambdify.py', 'lambdify'), ('sympy/utilities/iterables.py', 'multiset_derangements'), ('sympy/simplify/hyperexpand.py', 'add_formulae'), ('sympy/simplify/hyperexpand.py', 'add_meijerg_formulae'), ('sympy/simplify/hyperexpand.py', 'try_lerchphi'), ('sympy/simplify/hyperexpand.py', '_hyperexpand'), ('sympy/simplify/hyperexpand.py', '_meijergexpand'), ('sympy/integrals/meijerint.py', '_rewrite_single'), ('sympy/integrals/meijerint.py', 'meijerint_definite'), ('sympy/integrals/meijerint.py', '_meijerint_definite_4')])
RESTORE={'sympy/core/numbers.py|Number.__divmod__': "    def __divmod__(self, other):\n        from sympy.functions.elementary.complexes import sign\n\n        try:\n            other = Number(other)\n            if self.is_infinite or S.NaN in (self, other):\n                return (S.NaN, S.NaN)\n        except TypeError:\n            return NotImplemented\n        if not other:\n            raise ZeroDivisionError('modulo by zero')\n        if self.is_Integer and other.is_Integer:\n            return Tuple(*divmod(self.p, other.p))\n        elif isinstance(other, Float):\n            rat = self/Rational(other)\n        else:\n            rat = self/other\n        if other.is_finite:\n            w = int(rat) if rat >= 0 else int(rat) - 1\n            r = self - other*w\n            if r == Float(other):\n                w += 1\n                r = 0\n            if isinstance(self, Float) or isinstance(other, Float):\n                r = Float(r)  # in case w or r is 0\n        else:\n            w = 0 if not self or (sign(self) == sign(other)) else -1\n            r = other if w else self\n        return Tuple(w, r)\n", 'sympy/core/intfunc.py|num_digits': 'def num_digits(n, base=10):\n    """Return the number of digits needed to express n in give base.\n\n    Examples\n    ========\n\n    >>> from sympy.core.intfunc import num_digits\n    >>> num_digits(10)\n    2\n    >>> num_digits(10, 2)  # 1010 -> 4 digits\n    4\n    >>> num_digits(-100, 16)  # -64 -> 2 digits\n    2\n\n\n    Parameters\n    ==========\n\n    n: integer\n        The number whose digits are counted.\n\n    b: integer\n        The base in which digits are computed.\n\n    See Also\n    ========\n    sympy.ntheory.digits.digits, sympy.ntheory.digits.count_digits\n    """\n    if base < 0:\n        raise ValueError(\'base must be int greater than 1\')\n    if not n:\n        return 1\n    e, t = integer_log(abs(n), base)\n    return 1 + e\n', 'sympy/core/intfunc.py|integer_log': 'def integer_log(n, b):\n    r"""\n    Returns ``(e, bool)`` where e is the largest nonnegative integer\n    such that :math:`|n| \\geq |b^e|` and ``bool`` is True if $n = b^e$.\n\n    Examples\n    ========\n\n    >>> from sympy import integer_log\n    >>> integer_log(125, 5)\n    (3, True)\n    >>> integer_log(17, 9)\n    (1, False)\n\n    If the base is positive and the number negative the\n    return value will always be the same except for 2:\n\n    >>> integer_log(-4, 2)\n    (2, False)\n    >>> integer_log(-16, 4)\n    (0, False)\n\n    When the base is negative, the returned value\n    will only be True if the parity of the exponent is\n    correct for the sign of the base:\n\n    >>> integer_log(4, -2)\n    (2, True)\n    >>> integer_log(8, -2)\n    (3, False)\n    >>> integer_log(-8, -2)\n    (3, True)\n    >>> integer_log(-4, -2)\n    (2, False)\n\n    See Also\n    ========\n    integer_nthroot\n    sympy.ntheory.primetest.is_square\n    sympy.ntheory.factor_.multiplicity\n    sympy.ntheory.factor_.perfect_power\n    """\n    n = as_int(n)\n    b = as_int(b)\n\n    if b < 0:\n        e, t = integer_log(abs(n), -b)\n        # (-2)**3 == -8\n        # (-2)**2 = 4\n        t = t and e % 2 == (n < 0)\n        return e, t\n    if b <= 1:\n        raise ValueError(\'base must be 2 or more\')\n    if n < 0:\n        if b != 2:\n            return 0, False\n        e, t = integer_log(-n, b)\n        return e, False\n    if n == 0:\n        raise ValueError(\'n cannot be 0\')\n\n    if n < b:\n        return 0, n == 1\n    if b == 2:\n        e = n.bit_length() - 1\n        return e, trailing(n) == e\n    t = trailing(b)\n    if 2**t == b:\n        e = int(n.bit_length() - 1)//t\n        n_ = 1 << (t*e)\n        return e, n_ == n\n\n    d = math.floor(math.log10(n) / math.log10(b))\n    n_ = b ** d\n    while n_ <= n:  # this will iterate 0, 1 or 2 times\n        d += 1\n        n_ *= b\n    return d - (n_ > n), (n_ == n or n_//b == n)\n', 'mpmath/libmp/libmpc.py|mpc_square': 'def mpc_square(z, prec, rnd=round_fast):\n    # (a+b*I)**2 == a**2 - b**2 + 2*I*a*b\n    a, b = z\n    p = mpf_mul(a,a)\n    q = mpf_mul(b,b)\n    r = mpf_mul(a,b, prec, rnd)\n    re = mpf_sub(p, q, prec, rnd)\n    im = mpf_shift(r, 1)\n    return re, im\n'}
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob("*.py")):
  b=p.read_bytes();items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode();return hashlib.sha256(mb).hexdigest()
def _find(text,qual):
 tree=ast.parse(text);cur=tree.body
 for part in qual.split('.'):
  n=next((x for x in cur if isinstance(x,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==part),None)
  if n is None:raise KeyError(qual)
  cur=getattr(n,"body",[])
 return n
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f"base manifest drift: {before}")
 by={}
 for r,q in SELECT:by.setdefault(r,set()).add(q)
 for rel,qs in by.items():
  p=root/rel;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);stack=[];reps=[]
  class V(ast.NodeVisitor):
   def visit_ClassDef(self,n):stack.append(n.name);self.generic_visit(n);stack.pop()
   def visit_FunctionDef(self,n):
    q=".".join(stack+[n.name])
    if q in qs:
     a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=" "*n.body[0].col_offset;reps.append((a,b,ind+"raise NotImplementedError(\"outside Brain bounded exact-symbolic contract\")\n",q));return
    stack.append(n.name);self.generic_visit(n);stack.pop()
   visit_AsyncFunctionDef=visit_FunctionDef
  V().visit(tree);found={x[3] for x in reps}
  if found!=qs:raise RuntimeError((rel,qs,found))
  for a,b,new,q in sorted(reps,reverse=True):lines[a:b]=[new]
  out="".join(lines);compile(out,str(p),"exec");p.write_text(out)
 for key,pay in RESTORE.items():
  rel,qual=key.split("|",1);p=root/rel;text=p.read_text();n=_find(text,qual);lines=text.splitlines(True);lines[n.lineno-1:n.end_lineno]=pay.splitlines(True);out="".join(lines);compile(out,str(p),"exec");p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f"target manifest mismatch: {after}")
 return after
