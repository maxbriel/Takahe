import numpy as np
from numba import njit

@njit
def _dadt(t, a, e, beta):
    """
    Auxiliary function to compute Equation 3.

    Params:
        t [ndarray] A vector of times.
        e [float] The current eccentricity
        a [float] The current semimajor axis

    Output:
        The quantity da/dt - how the semimajor axis is changing
                             with time.
    """

    initial_term = (-beta / (a**3 * (1-e**2)**(7/2)))

    da = initial_term * (1 + 73/24 * e**2 + 37 / 96 * e ** 4)
    # Units: km/s

    return da

@njit
def _dedt(t, a, e, beta):
    """
    Auxiliary function to compute Equation 4.

    Params:
        t [ndarray] A vector of times.
        e [float] The current eccentricity
        a [float] The current semimajor axis

    Output:
        The quantity de/dt - how the eccentricity is changing
                             with time.
    """

    initial_term = (-19/12 * beta / (a**4*(1-e**2)**(5/2)))

    de = initial_term * (e + 121/304 * e ** 3) # Units: s^-1

    return de

@njit
def _coupled_eqs(t, p, beta):
    """
    Primary workhorse function. Computes the vector
    [da/dt, de/dt] for use in our integrator.

    Params:
        t [ndarray] A vector of times
        p [list] A list or 2-tuple of arguments. Must take
                      the form [a, e]

    Output:
        A list containing da/dt and de/dt
    """

    return np.array([_dadt(t, p[0], p[1], beta), _dedt(t, p[0], p[1], beta)])

@njit
def integrate(t_eval, a0, e0, beta):
    """
    Auxilary function which uses an RKF45 integrator to
        integrate the system of ODEs

    Arguments:
        t_eval {ndarray} -- An array of timesteps to compute
                            the integrals over

    Returns:
        evolve_over {ndarray} -- An array representing the time
                                 integrated over (in gigayears)
        a_arr {ndarray} -- An array representing the SMA of the
                           binary orbit (in solar radii)
        e_arr {ndarray} -- An array representing the
                           eccentricity of the binary orbit
    """

    h = t_eval[1] - t_eval[0]
    a, e = a0, e0

    a_arr = []
    e_arr = []

    # Implement the RKF45 algorithm.
    yk = np.array([a, e])

    for t in t_eval:
        c1 = _coupled_eqs(t, yk, beta)
        k1 = h * c1
        k2 = h * _coupled_eqs(t + 1/4 * h, yk + 1/4 * k1, beta)

        k3 = h * _coupled_eqs(t + 3/8 * h, yk + 3/32 * k1 \
                                             + 9/32 * k2, beta)

        k4 = h * _coupled_eqs(t+12/13 * h, yk + 1932/2197 * k1 \
                                             - 7200/2197 * k2 \
                                             + 7293/2197 * k3, beta)

        k5 = h * _coupled_eqs(t + h, yk + 439/216 * k1 \
                                       - 8*k2 \
                                       + 3680/513 * k3
                                       - 845/4104*k4, beta)

        k6 = h * _coupled_eqs(t + 1/2 * h, yk - 8/27*k1 \
                                             + 2*k2 \
                                             - 3544/2565*k3 \
                                             + 1859/4104 * k4 \
                                             - 11/40 * k5, beta)

        if e >= 1 or a <= 0:
            # runaway integration, we should kill it
            # t_eval = (t_eval[0], t_eval[-1], len(e_arr))
            break

        a_arr.append(yk[0])
        e_arr.append(yk[1])

        yk = yk + 25/216 * k1 + 1408/2565*k3 + 2197/4101 * k4 - 1/5 * k5

    return np.array(a_arr), np.array(e_arr)
