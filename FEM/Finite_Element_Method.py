import numpy as np
import math
import scipy.linalg as la


class FEM(object):

    def __init__(self, n, basis, fun, l=None, p=1, prop=(1., 1., 1.), bc=((-1, 0), (-2, 0), (0, 0), (1, 0)), h=None):

        self.n = n  # number of elements
        self.p = p  # degree
        self.num_nodes = p + n  # number of nodes
        self.num_basis = n - p - 1  # number of basis functions
        self.n_int = p + 1  # number of quadratures / basis per element
        self.num_bc = len(bc)  # number of boundary conditions

        self.fun = fun  # forcing function
        self.basis = basis  # basis function
        self.bc = bc  # boundary conditions

        self.g_i = prop[0]  # polar moment of inertia (I)
        self.m_e = prop[1]  # Modulus of Elasticity (E)
        self.row = prop[2]  # density

        if l is None:
            self.l = float(n)
        else:
            self.l = l  # length of system

        self.knot_vector = self._get_knot_vector()  # knot vector
        self.xga = self._xga()  # global locations of the nodes
        self.id_array = self._construct_id()  # id array for location matrix
        self.qs, self.ws = self._get_quadratures()  # quadrature points and weighting values
        self.h = h

    def solve(self):

        d_n, e_val, e_vectors = self._solve_d()  # solve for displacements of non-zero nodes
        xc = np.linspace(-.99, .99, 3)  # list of xc values for which to solve

        d = np.zeros((len(self.xga), 1))  # place zero value nodes in d
        d_m = np.zeros((len(self.xga), len(e_vectors)))  # place zero value nodes in d
        e_vectors = np.swapaxes(e_vectors, 0, 1)
        for a in xrange(1, len(self.xga)+1):
            g = self._id(a)
            if g != 0:
                d[g-1] = d_n[g-1]
                d_m[g-1] = e_vectors[g-1]

        u = np.zeros((self.n, len(xc)))  # list of u for each element
        x = np.empty((self.n, len(xc)))  # list of matching x values
        m_u_list = np.zeros((len(e_vectors[0]), self.n, len(xc)))  # list of u for each element

        for e in xrange(1, self.n+1):  # loop over elements

            for i in xrange(len(xc)):  # loop over each xc value

                dnx, ddnx, jac, x_pos, ne, dne = self._basis_x(e, xc[i])  # get basis and x
                x[e-1][i] = x_pos

                for a in xrange(1, self.p + 2):
                    u[e-1][i] += ne[a-1]*d[self._ien(e, a)-1]

                    for q in xrange(len(e_vectors[0])):
                        m_u_list[q][e-1][i] += ne[a - 1] * d_m[self._ien(e, a) - 1][q]

        freq = []
        for e in e_val:
            freq.append(math.sqrt(e))

        return u, x, d, self.xga, m_u_list, freq

    def _solve_d(self):

        k = np.zeros((self.num_nodes - self.num_bc, self.num_nodes - self.num_bc), dtype=float)  # global K
        mass = np.zeros((self.num_nodes - self.num_bc, self.num_nodes - self.num_bc), dtype=float)  # global M
        f = np.zeros((self.num_nodes - self.num_bc, 1), dtype=float)  # global F

        for e in xrange(1, self.n + 1):  # loop over elements
            for j in xrange(1, self.n_int + 1):  # loop over quadrature points
                dnx, ddnx, jac, x, ne, dne = self._basis_x(e, self.qs[j - 1])  # get values of global basis, x, and jac
                for a in xrange(1, self.p + 2):  # loop to place element k, f into global K, F
                    i = self._lm(a, e)
                    if i != 0:
                        for b in xrange(1, self.p + 2):  # loop to place element k into global K
                            m = self._lm(b, e)
                            if m != 0:
                                k[i-1][m-1] += ddnx[a-1]*self.m_e*self.g_i*ddnx[b-1]*jac*self.ws[j-1]
                                mass[i-1][m-1] += ne[a-1]*self.row*ne[b-1]*jac*self.ws[j-1]
                        f[i-1] += ne[a-1]*self._fa(x)*jac*self.ws[j-1]

        e_vals, e_vecs = la.eig(k, b=mass)
        order = np.argsort(e_vals)

        eig_vals = []
        for e in e_vals:
            eig_vals.append(np.real(e))

        k = np.asmatrix(k)

        e_values = []
        e_vectors = []
        for o in order:
            e_values.append(eig_vals[o])
            e_vectors.append(e_vecs[:, o])

        return np.asarray(k.I * f), e_values, e_vectors[:10]

    def _basis_x(self, e, xc):

        b_s = []  # collection of values for the basis functions at xc
        db_s = []  # collection of values for the derivative of the basis functions at xc
        ddb_s = []  # collection of the values for the double derivative of the basis functions at xc

        for a in xrange(1, self.n_int + 1):  # loop over the local basis
            basis = self._local_b(xc, a)
            b_s.append(basis[0])
            db_s.append(basis[1])
            ddb_s.append(basis[2])

        ce = self._get_c_e(e)
        b_s = np.asarray(b_s)
        db_s = np.asarray(db_s)
        ddb_s = np.asarray(ddb_s)

        ne, dne, ddne = self._local_n(b_s, db_s, ddb_s, ce)  # get local basis

        dnx, ddnx, jac, x = self._global(ne, dne, ddne, self.xga[e - 1:e + self.p + 2])  # convert local to global

        dnx = np.asarray(dnx).flatten()
        ddnx = np.asarray(ddnx).flatten()
        jac = np.asarray(jac)[0][0]
        x = np.asarray(x).flatten()

        return dnx, ddnx, jac, x, ne, dne

    def _get_knot_vector(self):
        knot_vector = np.array(np.zeros(self.p + 1))
        knot_vector = np.insert(knot_vector, len(knot_vector), np.arange(self.l/self.n, self.l, self.l/self.n))
        knot_vector = np.insert(knot_vector, len(knot_vector), np.zeros(self.p + 1) + self.l)

        return knot_vector

    def _get_quadratures(self):

        if self.n_int == 1:
            q_points = [0.]
            weights = [2]
        elif self.n_int == 2:
            q_points = [-1./math.sqrt(3.), 1./math.sqrt(3.)]
            weights = [1, 1]
        elif self.n_int == 3:
            q_points = [-math.sqrt(3./5.), 0., math.sqrt(3./5.)]
            weights = [5./9., 8./9., 5./9.]
        elif self.n_int == 4:
            q_points = [-0.8611363115940526, -0.3399810435848563, 0.3399810435848563, 0.8611363115940526]
            weights = [0.3478548451374538, 0.6521451548625461, 0.6521451548625461, 0.3478548451374538]
        else:
            q_points = None
            weights = None

        return q_points, weights

    def _xga(self):
        x_a = np.empty(self.n+self.p)
        for a in xrange(1, self.n+self.p+1):
            x_a_sum = 0.
            for j in xrange(a+1, self.p+a+1):
                x_a_sum += self.knot_vector[j-1]
            x_a[a-1] = float(x_a_sum)/float(self.p)
        return x_a

    def _get_c_e(self, e):

        if self.p == 1:
            return np.asarray([[1., 0.], [0., 1.]])

        elif self.p == 2:
            if self.n == 1:
                return np.asarray([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
            elif e == 1:
                return np.asarray([[1., 0., 0.], [0., 1., .5], [0., 0., .5]])
            elif e == self.n:
                return np.asarray([[.5, 0., 0.], [.5, 1., 0.], [0., 0., 1.]])
            else:
                return np.asarray([[.5, 0., 0.], [.5, 1., .5], [0., 0., .5]])

        elif self.p == 3:
            if self.n == 1:
                return np.asarray([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
            elif e == 1:
                return np.asarray([[1., 0., 0., 0.], [0., 1., .5, .25],
                                   [0., 0., .5, 7./12.], [0., 0., 0., 1./6.]])
            elif e == 2:
                return np.asarray([[.25, 0., 0., 0.], [7./12., 2./3., 1./3., 1./6.],
                                   [1./6., 1./3., 2./3., 2./3.], [0., 0., 0., 1./6.]])
            elif e == self.n - 1:
                return np.asarray([[1./6., 0., 0., 0], [2./3., 2./3., 1./3., 1./6.],
                                   [1./6., 1./3., 2./3., 7./12.], [0., 0., 0., .25]])
            elif e == self.n:
                return np.asarray([[1./6., 0., 0., 0.], [7./12., .5, 0., 0.],
                                   [.25, .5, 1., 0.], [0., 0., 0., 1.]])
            else:
                return np.asarray([[1./6., 0., 0., 0.], [2./3., 2./3., 1./3., 1./6.],
                                   [1./6., 1./3., 2./3., 2./3.], [0., 0., 0., 1./6.]])

    def _local_b(self, gc, a):

        b = self.basis[0](a, gc, self.p)
        db = self.basis[1](a, gc, self.p)
        ddb = self.basis[2](a, gc, self.p)

        return b, db, ddb

    def _local_n(self, b, db, ddb, ce):

        ce = np.matrix(ce)
        b = np.matrix(b)
        db = np.matrix(db)
        ddb = np.matrix(ddb)

        n = ce*b.T
        dn = ce*db.T
        ddn = ce*ddb.T

        return np.asarray(n), np.asarray(dn), np.asarray(ddn)

    def _global(self, n, dn, ddn, xae):

        xe_c = 0.
        dxe_c = 0.
        ddxe_c = 0.

        for i in xrange(1, self.p+2):
            xe_c += xae[i-1]*n[i-1]
            dxe_c += xae[i-1]*dn[i-1]
            ddxe_c += xae[i-1]*ddn[i-1]

        dxe_c_s = dxe_c**2
        dxe_c_s = np.matrix(dxe_c_s)

        dn = np.matrix(dn)
        dxe_c = np.matrix(dxe_c)

        ddn = np.matrix(ddn)
        ddxe_c = np.matrix(ddxe_c)

        dnx = dn*dxe_c.I
        ddnx = (ddn - dnx*ddxe_c)*dxe_c_s.I
        j = dxe_c

        return dnx, ddnx, j, xe_c

    def _fa(self,  x):

        return self.fun(x, self.h)

    def _lm(self, a, e):

        global_a = self._ien(e, a)
        return self._id(global_a)

    def _ien(self, e, a):
        return e + a - 1

    def _id(self, global_a):
        return self.id_array[global_a-1]

    def _construct_id(self):
        id_array = np.zeros(self.num_nodes, dtype=int)
        num_eq = 0
        for i in xrange(self.num_nodes):
            skip = False
            for bc in self.bc:
                if bc[0] == i:
                    skip = True
            if not skip:
                num_eq += 1
                id_array[i] = num_eq
        for bc in self.bc:
            id_array[bc[0]] = 0
        return id_array
