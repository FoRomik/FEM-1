import Finite_Element_Method as FEM
import Plotter as Pl
import numpy as np
import Error as Er
import math


def func_x2(ex):
    return ex**2.


def func_p2(ex, h):
    return 10.*(h**3.)


def linear(a, c, p):

    if a == 1:
        n = 0.5 * (1 - c)

    else:
        n = 0.5 * (1 + c)

    return n


def bern(a, gc, p):
    f1 = (1/(2**float(p)))
    f2 = (math.factorial(p)/(math.factorial(a-1)*math.factorial(p-a+1)))
    f3 = ((1.-gc)**(p-float(a)+1.))
    f4 = ((1.+gc)**(float(a)-1.))

    return f1*float(f2)*f3*f4


def d_bern(a, gc, p):
    f1 = (1 / (2 ** float(p)))
    f2 = (math.factorial(p) / (math.factorial(a - 1) * math.factorial(p - a + 1)))
    f3 = ((1. - gc) ** (p - float(a)))
    f4 = ((1. + gc) ** (float(a) - 2.))
    f5 = (2. * float(a) - float(p) * gc - float(p) - 2.)

    return f1*float(f2)*f3*f4*f5


def dd_bern(a, gc, p):
    f1 = (1 / (2 ** float(p)))
    f2 = (math.factorial(p) / (math.factorial(a - 1) * math.factorial(p - a + 1)))
    f3 = ((1. - gc) ** (p - float(a) - 1.))
    f4 = ((1. + gc) ** (float(a) - 3.))
    f5 = (4.*(float(a)**2.)-4.*float(a)*(float(p)*(gc+1.)-gc+2.) +
          (float(p)**2.)*((gc + 1.)**2.)+float(p)*(-gc-1.)*(gc-3.)-4.*(gc-1.))

    return f1 * float(f2) * f3 * f4 * f5


def eq_x2(ex, g=0, h=0):
    return (-1. / 12.0) * (ex**4.0 - 1.0) - h*ex + g + h


def beam_theory(ex, h):
    w = func_p2(ex, h)
    b = 0.005
    mod_e = 1000000.
    pol_i = b * (h ** 3.) / 12.
    l = 1.

    return w*(ex**4 - 4*(l**3)*ex + 3*l**4)/(24*mod_e*pol_i)


def plot_errors(ns, funcs, eqs):

    dhs = []

    for func in funcs:
        dh_f = []
        for n in ns:
            model = FEM.FEM(n, linear, func)
            uh, xh, dh = model.solve()
            dh_f.append(dh)
        dhs.append(dh_f)

    e = []
    for i in xrange(len(funcs)):
        e_f = []
        for j in xrange(len(ns)):
            he = [1.0 / float(ns[j])] * ns[j]
            e_f.append(Er.calc_error(he, dhs[i][j], linear, eqs[i]))
        e.append(e_f)

    hs = []
    for n in ns:
        hs.append(1. / n)

    for e_func in e:
        for e_n in e_func:
            print e_n

    Pl.plt_error(hs, e, 'Error')


def plot_solutions(ps, l, hs, bounds):

    b = 0.005
    mod_e = 1000000.
    row = .1
    pol_i = b * (hs ** 3.) / 12.

    freq = [float(n)*math.pi*math.sqrt(mod_e/row)/l for n in xrange(1, 1001)]
    # freq = [(float(n)-.5)*math.pi*math.sqrt(mod_e/row)/l for n in xrange(1, 1001)]
    n_m_n = np.linspace(1./1000., 1., 1000)

    freq_e_list = []
    n_m_n_list = []

    for j, p in enumerate(ps):
        fp = []
        n_m_n_p = []
        n_adj = 1000-p
        model = FEM.FEM(n_adj, [bern, d_bern, dd_bern], func_p2, l=l, p=p, prop=(pol_i, mod_e, row), h=hs, bc=bounds)
        uh, xh, d, xga, m_u_list, f_list = model.solve()
        # Pl.plot_modes(xh, m_u_list)
        # Pl.animation_plot(xh.flatten(), m_u_list[2].flatten())
        for i, f in enumerate(f_list):
            fp.append(f/freq[i])
            n_m_n_p.append(n_m_n[i])
        freq_e_list.append(fp)
        n_m_n_list.append(n_m_n_p)

    Pl.plot_errors(n_m_n_list, freq_e_list)

p_list = [1, 2, 3]
length = 1.
h_list = .005
bc = ((-2, 0), (-1, 0))
# bc = ((0, 0), (1, 0), (-2, 0), (-1, 0))

plot_solutions(p_list, length, h_list, bc)
