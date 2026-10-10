import importlib, types, shutil, sys, os, json
from pathlib import Path
SRC=Path('/opt/pyvenv/lib/python3.13/site-packages')
DST=Path('/mnt/data/bytes_successor/cand_lazy')
if DST.exists(): shutil.rmtree(DST)
DST.mkdir(parents=True)
for pkg in ['sympy','mpmath']:
    shutil.copytree(SRC/pkg,DST/pkg)
for p in list(DST.rglob('__pycache__')): shutil.rmtree(p, ignore_errors=True)
for p in sorted(list(DST.rglob('tests')), reverse=True):
    if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
for p in list(DST.rglob('test_*.py')):
    try:p.unlink()
    except:pass

pkgs=['sympy','sympy.functions','sympy.polys','sympy.printing','sympy.matrices','sympy.solvers','sympy.integrals','sympy.series','sympy.utilities','sympy.calculus','sympy.polys.domains','sympy.polys.numberfields','sympy.tensor.array']

def replace_once(path, old, new):
    t=path.read_text()
    if old not in t:
        raise RuntimeError(f'missing patch target in {path}: {old[:80]}')
    path.write_text(t.replace(old,new,1))

p=DST/'mpmath/ctx_mp.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, '''        # XXX: automate
        try:
            ctx.bernoulli.im_func.func_doc = function_docs.bernoulli
            ctx.primepi.im_func.func_doc = function_docs.primepi
            ctx.psi.im_func.func_doc = function_docs.psi
            ctx.atan2.im_func.func_doc = function_docs.atan2
        except AttributeError:
            # python 3
            ctx.bernoulli.__func__.func_doc = function_docs.bernoulli
            ctx.primepi.__func__.func_doc = function_docs.primepi
            ctx.psi.__func__.func_doc = function_docs.psi
            ctx.atan2.__func__.func_doc = function_docs.atan2

        ctx.digamma.func_doc = function_docs.digamma
        ctx.cospi.func_doc = function_docs.cospi
        ctx.sinpi.func_doc = function_docs.sinpi
''', '')

p=DST/'mpmath/ctx_fp.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, '        f_wrapped.__doc__ = function_docs.__dict__.get(name, f.__doc__)\n', '')

p=DST/'mpmath/ctx_mp_python.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, "        a.__doc__ = getattr(function_docs, docname, '')\n", '')
replace_once(p, '        f.__doc__ = function_docs.__dict__.get(name, "Computes the %s of x" % doc)\n', '')
replace_once(p, '        f_wrapped.__doc__ = function_docs.__dict__.get(name, f.__doc__)\n', '')
(DST/'mpmath/function_docs.py').unlink()

p=DST/'sympy/integrals/trigonometry.py'
replace_once(p, 'from .integrals import integrate\n', '')
replace_once(p, "def trigintegrate(f, x, conds='piecewise'):\n", "def trigintegrate(f, x, conds='piecewise'):\n    from .integrals import integrate\n")

p=DST/'sympy/core/add.py'
replace_once(p, '        from sympy.tensor.tensor import TensExpr, TensAdd\n', '')
replace_once(p, '            elif isinstance(o, TensExpr):\n                coeff = TensAdd(o, coeff).doit(deep=False)\n                continue\n', "            elif o.__class__.__module__.startswith('sympy.tensor.'):\n                from sympy.tensor.tensor import TensExpr, TensAdd\n                if isinstance(o, TensExpr):\n                    coeff = TensAdd(o, coeff).doit(deep=False)\n                    continue\n")

p=DST/'sympy/polys/polyroots.py'
replace_once(p, 'from sympy.polys.polyquinticconst import PolyQuintic\n', '')
replace_once(p, 'from sympy.polys.specialpolys import cyclotomic_poly\n', '')
replace_once(p, '    quintic = PolyQuintic(f)\n', '    from sympy.polys.polyquinticconst import PolyQuintic\n    quintic = PolyQuintic(f)\n')
replace_once(p, '        g = cyclotomic_poly(n, f.gen, polys=True)\n', '        from sympy.polys.specialpolys import cyclotomic_poly\n        g = cyclotomic_poly(n, f.gen, polys=True)\n')

p=DST/'sympy/simplify/simplify.py'
replace_once(p, '    from sympy.physics.units import Quantity\n\n    if expr.has(Quantity):\n        from sympy.physics.units.util import quantity_simplify\n        expr = quantity_simplify(expr)\n\n', '')

p=DST/'sympy/polys/polytools.py'
replace_once(p, 'from sympy.polys.fglmtools import matrix_fglm\n', '')
replace_once(p, 'from sympy.polys.groebnertools import groebner as _groebner\n', '')
replace_once(p, 'def groebner(F, *gens, **args):\n', 'def groebner(F, *gens, **args):\n    from sympy.polys.groebnertools import groebner as _groebner\n')
replace_once(p, '        G = matrix_fglm(polys, _ring, dst_order)\n', '        from sympy.polys.fglmtools import matrix_fglm\n        G = matrix_fglm(polys, _ring, dst_order)\n')

summary={}
for pn in pkgs:
    p=importlib.import_module(pn)
    names=list(getattr(p,'__all__',[])) or [n for n in vars(p) if not n.startswith('_')]
    mp={}; const={}; unm=[]
    for n in names:
        if not hasattr(p,n): continue
        o=getattr(p,n)
        if isinstance(o, types.ModuleType):
            mp[n]=(o.__name__,None); continue
        mod=getattr(o,'__module__',None)
        cand_attrs=[]
        oname=getattr(o,'__name__',None)
        if oname: cand_attrs.append(oname)
        cand_attrs.append(n)
        found=False
        if mod:
            try:
                m=importlib.import_module(mod)
                for an in cand_attrs:
                    if hasattr(m,an) and getattr(m,an) is o:
                        mp[n]=(mod,an); found=True; break
            except Exception: pass
        if found: continue
        if isinstance(o,(str,int,float,bool,type(None))): const[n]=o; continue
        unm.append(n)
    if pn in ('sympy','sympy.functions') and 'ln' in unm:
        mp['ln']=('sympy.functions.elementary.exponential','log'); unm.remove('ln')
    target=DST.joinpath(*pn.split('.'))/'__init__.py' if pn!='sympy' else DST/'sympy/__init__.py'
    lines=[]
    lines.append('"""Brain bounded lazy facade derived from SymPy 1.14.0 public bindings."""')
    lines.append('import importlib as _importlib')
    if pn=='sympy':
        lines.append('__version__ = "1.14.0"')
        lines.append('SYMPY_DEBUG = False')
    for k,v in const.items():
        if k!='__version__': lines.append(f'{k} = {v!r}')
    lines.append('_BRAIN_LAZY_MAP = ' + repr(mp))
    lines.append('__all__ = ' + repr([n for n in names if n in mp or n in const]))
    lines.append('def __getattr__(name):')
    lines.append('    spec = _BRAIN_LAZY_MAP.get(name)')
    lines.append('    if spec is None: raise AttributeError(name)')
    lines.append('    mod, attr = spec')
    lines.append('    obj = _importlib.import_module(mod) if attr is None else getattr(_importlib.import_module(mod), attr)')
    lines.append('    globals()[name] = obj')
    lines.append('    return obj')
    target.write_text('\n'.join(lines)+'\n')
    summary[pn]={'mapped':len(mp),'unmapped':unm}
print(json.dumps(summary,indent=2))

_mpmath_root = '''"""Brain bounded mpmath facade for exact-symbolic route."""
__version__ = "1.3.0"
from contextlib import contextmanager
from .ctx_mp_python import PythonMPContext
from .libmp import finf, fninf, fnan, fzero, fone
class MPContext(PythonMPContext):
    def __init__(self):
        super().__init__()
        self.default()
        self.types = [self.mpf, self.mpc, self.constant]
        self.pretty = False
        self.zero = self.make_mpf(fzero)
        self.one = self.make_mpf(fone)
        self.inf = self.make_mpf(finf)
        self.ninf = self.make_mpf(fninf)
        self.nan = self.make_mpf(fnan)
        self._mp = self
    @contextmanager
    def workprec(self, n, normalize_output=False):
        old = self.prec
        self.prec = n
        try:
            yield self
        finally:
            self.prec = old
mp = MPContext()
mpf = mp.mpf
mpc = mp.mpc
make_mpf = mp.make_mpf
make_mpc = mp.make_mpc
workprec = mp.workprec
inf = mp.inf
nan = mp.nan
def _unsupported(*args, **kwargs):
    raise NotImplementedError("mpmath operation outside Brain bounded exact-symbolic contract")
mpi = findroot = besseljzero = nsum = quadts = quadosc = sqrt = _unsupported
def __getattr__(name):
    if hasattr(mp, name):
        return getattr(mp, name)
    if name.startswith("_"):
        raise AttributeError(name)
    return _unsupported
'''
(DST/'mpmath/__init__.py').write_text(_mpmath_root)

p = DST/'sympy/matrices/immutable.py'
replace_once(p, 'from mpmath.matrices.matrices import _matrix\n\n', '')
replace_once(p,
'''def sympify_mpmath_matrix(arg):
    mat = [_sympify(x) for x in arg]
    return ImmutableDenseMatrix(arg.rows, arg.cols, mat)


sympify_converter[_matrix] = sympify_mpmath_matrix


''', '')


# Successor polys cut: finite-extension machinery is needed only by
# algebraic eigenvector construction, not by the bounded exact-symbolic
# matrix solve/determinant route. Keep the donor branch, but move its import
# to the exact decision site so the AGCA closure is absent unless invoked.
p = DST/'sympy/polys/matrices/eigen.py'
replace_once(p, 'from ..agca.extensions import FiniteExtension\n', '')
replace_once(
    p,
    '            minpoly = Poly.from_list(base, l, domain=domain)\n',
    '            minpoly = Poly.from_list(base, l, domain=domain)\n'
    '            from ..agca.extensions import FiniteExtension\n'
)


# V3 successor cut: special-polynomial machinery is not reached by the bounded
# exact-symbolic route. Preserve donor behavior by deferring only the imports
# to the exact branches that require them.
p = DST/'sympy/functions/elementary/trigonometric.py'
replace_once(p, 'from sympy.polys.specialpolys import symmetric_poly\n', '')
replace_once(p,
'                p[1 - i % 2] += symmetric_poly(i, Y)*(-1)**((i % 4)//2)\n',
'                from sympy.polys.specialpolys import symmetric_poly\n'
'                p[1 - i % 2] += symmetric_poly(i, Y)*(-1)**((i % 4)//2)\n')
replace_once(p,
'                p[(n - i) % 2] += symmetric_poly(i, Y)*(-1)**(((n - i) % 4)//2)\n',
'                from sympy.polys.specialpolys import symmetric_poly\n'
'                p[(n - i) % 2] += symmetric_poly(i, Y)*(-1)**(((n - i) % 4)//2)\n')

p = DST/'sympy/functions/elementary/hyperbolic.py'
replace_once(p, 'from sympy.polys.specialpolys import symmetric_poly\n', '')
replace_once(p,
'                p[i % 2] += symmetric_poly(i, TX)\n',
'                from sympy.polys.specialpolys import symmetric_poly\n'
'                p[i % 2] += symmetric_poly(i, TX)\n')
replace_once(p,
'                p[(n - i) % 2].append(symmetric_poly(i, CX))\n',
'                from sympy.polys.specialpolys import symmetric_poly\n'
'                p[(n - i) % 2].append(symmetric_poly(i, CX))\n')

p = DST/'sympy/polys/polyfuncs.py'
replace_once(p, 'from sympy.polys.specialpolys import (\n    symmetric_poly, interpolating_poly)\n', '')
replace_once(p,
'    try:\n        return interpolating_poly(n, x, X, Y).expand()\n',
'    from sympy.polys.specialpolys import interpolating_poly\n'
'    try:\n        return interpolating_poly(n, x, X, Y).expand()\n')
replace_once(p,
'    for i, coeff in enumerate(coeffs[1:]):\n        poly = symmetric_poly(i + 1, roots)\n',
'    from sympy.polys.specialpolys import symmetric_poly\n'
'    for i, coeff in enumerate(coeffs[1:]):\n        poly = symmetric_poly(i + 1, roots)\n')

p = DST/'sympy/polys/numberfields/minpoly.py'
replace_once(p, 'from sympy.polys.specialpolys import cyclotomic_poly\n', '')
replace_once(p,
'            factors = [cyclotomic_poly(i, x) for i in divisors(2*q)]\n',
'            from sympy.polys.specialpolys import cyclotomic_poly\n'
'            factors = [cyclotomic_poly(i, x) for i in divisors(2*q)]\n')


# V4 coverage repair: a fresh quartic-root case exposed that the bounded mpmath
# facade omitted atan, which SymPy uses for low-precision sign heuristics.
# Expose only the low-level real/complex atan already present in libmp.
p = DST/'mpmath/__init__.py'
replace_once(p,
    'from .libmp import finf, fninf, fnan, fzero, fone\n',
    'from .libmp import finf, fninf, fnan, fzero, fone, mpf_atan, mpc_atan\n')
replace_once(p,
    '        self._mp = self\n',
    '        self._mp = self\n'
    '        self.atan = self._wrap_libmp_function(mpf_atan, mpc_atan)\n')

# V4 polys cut: rs_compose_add is needed only by the additive-composition
# minimal-polynomial branch. Defer the import to that branch so ring_series
# and its puiseux dependency are absent from routes that never invoke it.
p = DST/'sympy/polys/numberfields/minpoly.py'
replace_once(p, 'from sympy.polys.ring_series import rs_compose_add\n', '')
replace_once(p,
    '        r = rs_compose_add(p1, p2)\n',
    '        from sympy.polys.ring_series import rs_compose_add\n'
    '        r = rs_compose_add(p1, p2)\n')


# V5 polys cut: PolyRing's IPolys inheritance is a broad dense/sparse
# compatibility facade. The bounded exact-symbolic route constructs and uses
# PolyRing/PolyElement directly but does not invoke IPolys methods. Remove the
# mixin edge so compatibility.py is absent from the physical closure.
p = DST/'sympy/polys/rings.py'
replace_once(p, 'from sympy.polys.compatibility import IPolys\n', '')
replace_once(p, 'class PolyRing(DefaultPrinting, IPolys):', 'class PolyRing(DefaultPrinting):')


# V6 polys/domain cut: Gaussian domains need AlgebraicField only when the
# explicit as_AlgebraicField conversion branch is invoked. Defer the import to
# that branch so algebraicfield.py is absent from the bounded exact route.
p = DST/'sympy/polys/domains/gaussiandomains.py'
replace_once(p, 'from sympy.polys.domains.algebraicfield import AlgebraicField\n', '')
replace_once(
    p,
    '        return AlgebraicField(self.dom, I)\n',
    '        from sympy.polys.domains.algebraicfield import AlgebraicField\n        return AlgebraicField(self.dom, I)\n'
)


# V7 matrix cut: the bounded route uses sparse DomainMatrix/SDM paths. DDM and
# dense kernels executed zero functions across spent profiling. Preserve all
# dense/list/Bird branches by moving DDM/dense imports to the exact branches.
p = DST/'sympy/polys/matrices/sdm.py'
replace_once(p, 'from .ddm import DDM\n', '')
replace_once(p,
    '        return DDM(M.to_list(), M.shape, M.domain)\n',
    '        from .ddm import DDM\n        return DDM(M.to_list(), M.shape, M.domain)\n')

p = DST/'sympy/polys/matrices/rref.py'
replace_once(p, 'from sympy.polys.matrices.ddm import DDM\n', '')
replace_once(p, 'from sympy.polys.matrices.dense import ddm_irref, ddm_irref_den\n', '')
replace_once(p,
    'def _dm_rref_GJ_dense(M):\n    """Compute RREF using dense Gauss-Jordan elimination with division."""\n    partial_pivot = M.domain.is_RR or M.domain.is_CC\n',
    'def _dm_rref_GJ_dense(M):\n    """Compute RREF using dense Gauss-Jordan elimination with division."""\n    from sympy.polys.matrices.ddm import DDM\n    from sympy.polys.matrices.dense import ddm_irref\n    partial_pivot = M.domain.is_RR or M.domain.is_CC\n')
replace_once(p,
    'def _dm_rref_den_FF_dense(M):\n    """Compute RREF using sparse fraction-free Gauss-Jordan elimination."""\n    ddm = M.rep.to_ddm().copy()\n',
    'def _dm_rref_den_FF_dense(M):\n    """Compute RREF using sparse fraction-free Gauss-Jordan elimination."""\n    from sympy.polys.matrices.ddm import DDM\n    from sympy.polys.matrices.dense import ddm_irref_den\n    ddm = M.rep.to_ddm().copy()\n')

p = DST/'sympy/polys/matrices/domainmatrix.py'
replace_once(p, 'from .ddm import DDM\n', '')
replace_once(p,
    '        if isinstance(rows, (DDM, SDM, DFM)):\n            raise TypeError("Use from_rep to initialise from SDM/DDM")\n        elif isinstance(rows, list):\n            rep = DDM(rows, shape, domain)\n',
    '        if rows.__class__.__module__ == "sympy.polys.matrices.ddm" or isinstance(rows, (SDM, DFM)):\n            raise TypeError("Use from_rep to initialise from SDM/DDM")\n        elif isinstance(rows, list):\n            from .ddm import DDM\n            rep = DDM(rows, shape, domain)\n')
replace_once(p,
    '        if not (isinstance(rep, (DDM, SDM)) or (DFM is not None and isinstance(rep, DFM))):\n            raise TypeError("rep should be of type DDM or SDM")\n',
    '        is_ddm = rep.__class__.__module__ == "sympy.polys.matrices.ddm"\n        if not (is_ddm or isinstance(rep, SDM) or (DFM is not None and isinstance(rep, DFM))):\n            raise TypeError("rep should be of type DDM or SDM")\n')
replace_once(p,
    '        ddm = DDM.from_list_flat(elements, shape, domain)\n',
    '        from .ddm import DDM\n        ddm = DDM.from_list_flat(elements, shape, domain)\n')
replace_once(p,
    '        return cls.from_rep(DDM.ones(shape, domain).to_dfm_or_ddm())\n',
    '        from .ddm import DDM\n        return cls.from_rep(DDM.ones(shape, domain).to_dfm_or_ddm())\n')

p = DST/'sympy/matrices/determinant.py'
replace_once(p, 'from sympy.polys.matrices.ddm import DDM\n', '')
replace_once(p,
    '    def mu(X):\n',
    '    from sympy.polys.matrices.ddm import DDM\n    def mu(X):\n')


# V8 minpoly cut: simplify and Expr positivity imported the full minimal-
# polynomial module before their rare fallback branches were actually needed.
# Defer those imports to the exact nthroot/surd and low-significance algebraic
# fallback sites. The bounded route preserves the donor branches but does not
# load minpoly in the qualified closure.
p = DST/'sympy/simplify/simplify.py'
replace_once(p, 'from sympy.polys.numberfields.minpoly import _is_sum_surds, _minimal_polynomial_sq\n', '')
replace_once(
    p,
    '    f = _minimal_polynomial_sq(p, n, x)\n',
    '    from sympy.polys.numberfields.minpoly import _minimal_polynomial_sq\n    f = _minimal_polynomial_sq(p, n, x)\n'
)
replace_once(
    p,
    '    if not _is_sum_surds(expr):\n',
    '    from sympy.polys.numberfields.minpoly import _is_sum_surds\n    if not _is_sum_surds(expr):\n'
)

p = DST/'sympy/core/expr.py'
replace_once(
    p,
    '        from sympy.polys.numberfields import minimal_polynomial\n        from sympy.polys.polyerrors import NotAlgebraic\n',
    ''
)
replace_once(
    p,
    '            elif r._prec == 1 and (not i or i._prec == 1) and \\\n                    self._eval_is_algebraic() and not self.has(Function):\n                try:\n',
    '            elif r._prec == 1 and (not i or i._prec == 1) and \\\n                    self._eval_is_algebraic() and not self.has(Function):\n                from sympy.polys.numberfields import minimal_polynomial\n                from sympy.polys.polyerrors import NotAlgebraic\n                try:\n'
)


# V9 joint lazy-import bundle.
# Every change below preserves the donor branch and delays only a dependency
# whose implementation is not needed until that branch is actually selected.

# Partial fractions are needed only by summation rational-decomposition branches.
p = DST/'sympy/concrete/summations.py'
replace_once(p, 'from sympy.polys.partfrac import apart\n', '')
replace_once(p,
    '    try:\n        expr = apart(expr, i)  # see if it becomes an Add\n',
    '    from sympy.polys.partfrac import apart\n    try:\n        expr = apart(expr, i)  # see if it becomes an Add\n')
replace_once(p,
    '    try:\n        f = apart(f, i)\n',
    '    from sympy.polys.partfrac import apart\n    try:\n        f = apart(f, i)\n')

# Appell polynomial helpers are needed only by explicit polynomial rewrites.
p = DST/'sympy/functions/combinatorial/numbers.py'
replace_once(p, 'from sympy.polys.appellseqs import bernoulli_poly, euler_poly, genocchi_poly\n', '')
replace_once(p,
    '        elif n.is_Number:\n            return bernoulli_poly(n, x)\n',
    '        elif n.is_Number:\n            from sympy.polys.appellseqs import bernoulli_poly\n            return bernoulli_poly(n, x)\n')
replace_once(p,
    '            return euler_poly(n, x)\n',
    '            from sympy.polys.appellseqs import euler_poly\n            return euler_poly(n, x)\n')
replace_once(p,
    '        elif n.is_Number:\n            return genocchi_poly(n, x)\n',
    '        elif n.is_Number:\n            from sympy.polys.appellseqs import genocchi_poly\n            return genocchi_poly(n, x)\n')

# polyfuncs is needed only by ComplexRootOf rational-function transformation.
p = DST/'sympy/polys/rootoftools.py'
replace_once(p, 'from sympy.polys.polyfuncs import symmetrize, viete\n', '')
replace_once(p,
    '        coeffs, mapping = symmetrize(p_coeff + q_coeff, formal=True)\n',
    '        from sympy.polys.polyfuncs import symmetrize, viete\n        coeffs, mapping = symmetrize(p_coeff + q_coeff, formal=True)\n')

# hyperexpand needs apart only inside the partial-fraction path.
p = DST/'sympy/simplify/hyperexpand.py'
replace_once(p, 'from sympy.polys import apart, poly, Poly\n', 'from sympy.polys import poly, Poly\n')
replace_once(p,
    '    part = apart(numer/denom, t)\n',
    '    from sympy.polys import apart\n    part = apart(numer/denom, t)\n')

# FiniteField is needed only by explicit Poly.set_modulus.
p = DST/'sympy/polys/polytools.py'
replace_once(p, 'from sympy.polys.domains import FF, QQ, ZZ\n', 'from sympy.polys.domains import QQ, ZZ\n')
replace_once(p,
    '        return f.set_domain(FF(modulus))\n',
    '        from sympy.polys.domains import FF\n        return f.set_domain(FF(modulus))\n')

# Real/complex float domains are needed only when float-like coefficients exist.
p = DST/'sympy/polys/constructor.py'
replace_once(p, 'from sympy.polys.domains.complexfield import ComplexField\n', '')
replace_once(p, 'from sympy.polys.domains.realfield import RealField\n', '')
replace_once(p,
    '            domain = ComplexField(prec=max_prec)\n',
    '            from sympy.polys.domains.complexfield import ComplexField\n            domain = ComplexField(prec=max_prec)\n')
replace_once(p,
    '            domain = RealField(prec=max_prec)\n',
    '            from sympy.polys.domains.realfield import RealField\n            domain = RealField(prec=max_prec)\n')
replace_once(p,
    '        ground = ComplexField(prec=max_prec)\n',
    '        from sympy.polys.domains.complexfield import ComplexField\n        ground = ComplexField(prec=max_prec)\n')
replace_once(p,
    '        ground = RealField(prec=max_prec)\n',
    '        from sympy.polys.domains.realfield import RealField\n        ground = RealField(prec=max_prec)\n')
replace_once(p, 'from sympy.polys.domains import ZZ, QQ, ZZ_I, QQ_I, EX\n',
                'from sympy.polys.domains import ZZ, QQ, ZZ_I, QQ_I\n')
replace_once(p,
    'def _construct_expression(coeffs, opt):\n    """The last resort case, i.e. use the expression domain. """\n    domain, result = EX, []\n',
    'def _construct_expression(coeffs, opt):\n    """The last resort case, i.e. use the expression domain. """\n    from sympy.polys.domains import EX\n    domain, result = EX, []\n')

# Sparse-ring heuristic gcd is needed only by the explicit ZZ gcd branch.
p = DST/'sympy/polys/rings.py'
replace_once(p, 'from sympy.polys.heuristicgcd import heugcd\n', '')
replace_once(p,
    '    def _gcd_ZZ(f, g):\n        return heugcd(f, g)\n',
    '    def _gcd_ZZ(f, g):\n        from sympy.polys.heuristicgcd import heugcd\n        return heugcd(f, g)\n')

# PolynomialRing is needed only for polynomial-domain branches. Preserve
# isinstance/subclass semantics by importing it only when the domain advertises
# that family.
p = DST/'sympy/polys/rings.py'
replace_once(p, 'from sympy.polys.domains.polynomialring import PolynomialRing\n', '')
replace_once(p,
    'from sympy.printing.defaults import DefaultPrinting\n',
    'from sympy.printing.defaults import DefaultPrinting\n\n'
    'def _is_polynomial_ring_domain(domain):\n'
    '    if getattr(domain, "is_PolynomialRing", False):\n'
    '        from sympy.polys.domains.polynomialring import PolynomialRing\n'
    '        return isinstance(domain, PolynomialRing)\n'
    '    return False\n')
replace_once(p,
    '        return PolynomialRing(self)\n',
    '        from sympy.polys.domains.polynomialring import PolynomialRing\n        return PolynomialRing(self)\n')
t = p.read_text()
t = t.replace('isinstance(self.domain, PolynomialRing)', '_is_polynomial_ring_domain(self.domain)')
t = t.replace('isinstance(ring.domain, PolynomialRing)', '_is_polynomial_ring_domain(ring.domain)')
t = t.replace('isinstance(p2.ring.domain, PolynomialRing)', '_is_polynomial_ring_domain(p2.ring.domain)')
p.write_text(t)

# FiniteField for matrices is needed only by inv_mod.
p = DST/'sympy/matrices/repmatrix.py'
replace_once(p, 'from sympy.polys.domains import ZZ, QQ, GF, EXRAW\n',
                'from sympy.polys.domains import ZZ, QQ, EXRAW\n')
replace_once(p,
    '        K = GF(m, symmetric=False)\n',
    '        from sympy.polys.domains import GF\n        K = GF(m, symmetric=False)\n')

# Float/complex conversion classes are needed only after matching a float-like
# input, not on every Domain.convert call.
p = DST/'sympy/polys/domains/domain.py'
replace_once(p, '        from sympy.polys.domains import ZZ, QQ, RealField, ComplexField\n',
                '        from sympy.polys.domains import ZZ, QQ\n')
replace_once(p,
    '        if isinstance(element, float):\n            parent = RealField()\n',
    '        if isinstance(element, float):\n            from sympy.polys.domains import RealField\n            parent = RealField()\n')
replace_once(p,
    '        if isinstance(element, complex):\n            parent = ComplexField()\n',
    '        if isinstance(element, complex):\n            from sympy.polys.domains import ComplexField\n            parent = ComplexField()\n')
replace_once(p,
    "        if type(element).__name__ == 'mpf':\n            parent = RealField()\n",
    "        if type(element).__name__ == 'mpf':\n            from sympy.polys.domains import RealField\n            parent = RealField()\n")
replace_once(p,
    "        if type(element).__name__ == 'mpc':\n            parent = ComplexField()\n",
    "        if type(element).__name__ == 'mpc':\n            from sympy.polys.domains import ComplexField\n            parent = ComplexField()\n")

# ModularInteger is needed only if such a factor is actually sorted.
p = DST/'sympy/polys/polyutils.py'
replace_once(p,
'''else:
    from sympy.polys.domains.modularinteger import ModularInteger
    flint = None
    _GF_types = (ModularInteger,)
''',
'''else:
    flint = None
    _GF_types = ()

def _is_GF_type(value):
    if _GF_types and isinstance(value, _GF_types):
        return True
    if GROUND_TYPES != 'flint' and value.__class__.__module__ == 'sympy.polys.domains.modularinteger':
        from sympy.polys.domains.modularinteger import ModularInteger
        return isinstance(value, ModularInteger)
    return False
''')
replace_once(p, '        if isinstance(factor, _GF_types):\n',
                '        if _is_GF_type(factor):\n')

# EX conversion in polyroots is only needed by the Gaussian-domain branch.
p = DST/'sympy/polys/polyroots.py'
replace_once(p, 'from sympy.polys.domains import EX\n', '')
replace_once(p,
    '        f = f.per(f.rep.convert(EX))\n',
    '        from sympy.polys.domains import EX\n        f = f.per(f.rep.convert(EX))\n')

# Polynomial eigenvector machinery and EX are needed only by _eigenvects_DOM.
p = DST/'sympy/matrices/eigen.py'
replace_once(p, 'from sympy.polys import roots, CRootOf, ZZ, QQ, EX\n',
                'from sympy.polys import roots, CRootOf, ZZ, QQ\n')
replace_once(p, 'from sympy.polys.matrices.eigen import dom_eigenvects, dom_eigenvects_to_sympy\n', '')
replace_once(p,
    'def _eigenvects_DOM(M, **kwargs):\n    DOM = DomainMatrix.from_Matrix(M, field=True, extension=True)\n',
    'def _eigenvects_DOM(M, **kwargs):\n'
    '    from sympy.polys import EX\n'
    '    from sympy.polys.matrices.eigen import dom_eigenvects, dom_eigenvects_to_sympy\n'
    '    DOM = DomainMatrix.from_Matrix(M, field=True, extension=True)\n')
