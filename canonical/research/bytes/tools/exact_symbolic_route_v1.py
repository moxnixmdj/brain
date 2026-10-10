import math
from sympy.core.symbol import Symbol
from sympy.core.numbers import Rational, Integer, pi, oo
from sympy.core.add import Add
from sympy.core.mul import Mul
from sympy.core.power import Pow
from sympy.polys.polytools import Poly, factor
from sympy.polys.polyroots import roots
from sympy.functions.elementary.trigonometric import sin
from sympy.functions.combinatorial.factorials import binomial
from sympy.matrices.dense import MutableDenseMatrix
from sympy.series.limits import limit
from sympy.integrals.trigonometry import _sin_pow_integrate

x = Symbol('x')

def _canon_roots(d):
    # Avoid any printing dependency in the executable path.
    from sympy.core.sorting import default_sort_key
    return tuple((r, int(m)) for r, m in sorted(d.items(), key=lambda kv: default_sort_key(kv[0])))

def execute(case):
    op = case['op']
    p = case['p']
    if op == 'rat':
        a,b,c,d,e,f = p
        return Rational(a,b) + Rational(c,d) * Rational(e,f)
    if op == 'factor':
        # p = coefficient list, high to low
        expr = Add(*[Integer(c)*Pow(x, len(p)-1-i) for i,c in enumerate(p)])
        return factor(expr)
    if op == 'coeff':
        coeffs,k = p
        expr = Add(*[Integer(c)*Pow(x, len(coeffs)-1-i) for i,c in enumerate(coeffs)])
        return Poly(expr, x).nth(k)
    if op == 'roots':
        coeffs = p
        expr = Add(*[Integer(c)*Pow(x, len(coeffs)-1-i) for i,c in enumerate(coeffs)])
        return _canon_roots(roots(expr, x))
    if op == 'diff':
        terms,n = p
        expr = Add(*[Integer(c)*Pow(x,e) for c,e in terms])
        return expr.diff(x, n)
    if op == 'sin_even_integral':
        n = p[0]
        ant = _sin_pow_integrate(2*n, x)
        return (ant.subs(x, pi) - ant.subs(x, Integer(0))).expand()
    if op == 'hilbert_det':
        n = p[0]
        M = MutableDenseMatrix(n, n, lambda i,j: Rational(1, i+j+1))
        return M.det()
    if op == 'binomial_identity':
        n = p[0]
        return Add(*[binomial(n,k) for k in range(n+1)])
    if op == 'limit_poly_ratio':
        a,b,c,d,e = p
        expr = (a*x*x + b*x + c)/(d*x*x + e)
        return limit(expr, x, oo)
    if op == 'limit_sinx':
        k = p[0]
        return limit(sin(Integer(k)*x)/x, x, Integer(0))
    if op == 'linear_solve':
        # p = n, flattened A, b
        n, flat, vec = p
        A = MutableDenseMatrix(n,n,[Integer(v) for v in flat])
        b = MutableDenseMatrix(n,1,[Integer(v) for v in vec])
        return tuple(A.inv()*b)
    if op == 'series_coeff':
        coeffs,k = p
        expr = Pow(Integer(1) - x, Integer(-2)) * Add(*[Integer(c)*Pow(x,i) for i,c in enumerate(coeffs)])
        s = expr.series(x, Integer(0), k+1).removeO()
        return s.coeff(x,k)
    raise ValueError(op)
