import numpy as np
from takahe.constants import *

def create(primary_mass, secondary_mass, a0, e0, extra_terms=dict()):
    """Creates a given Binary Star System from provided data.

        Represents a binary star system in the Universe.

        All physical parameters are expected to be in Solar units. i.e.,
        - Mass in Solar Mass
        - a0 in Solar Radii

        Arguments:
            primary_mass {float} -- The mass of the primary star
            secondary_mass {float} -- The mass of the secondary star
            a0 {float} -- The semimajor axis (SMA) of the binary
            e0 {float} -- The eccentricity of the binary system.

        Keyword Arguments:
            extra_terms {dict} -- A dictionary of extra parameters for
                                  the system. Acceptable extra parameters
                                  are: weight, evolution_age,
                                  and rejuvenation_age
                                  (default: {empty dict})

        Raises:
            ValueError -- if e0 is not in the interval [0, 1]

        Returns:
            BinaryStarSystem
        """
    return BinaryStarSystem(primary_mass,
                            secondary_mass,
                            a0,
                            e0,
                            extra_terms)

class BinaryStarSystem:
    """Represents a binary star system."""

    def __init__(self, primary_mass, secondary_mass, a0, e0, extra_terms=dict()):

        if e0 > 1 or e0 < 0:
            raise ValueError("Eccentricity must be between 0 and 1.")

        self.m1 = primary_mass * Solar_Mass # Units: kg
        self.m2 = secondary_mass * Solar_Mass # Units: kg
        self.a0 = np.float128(a0 * Solar_Radii * 1000) # Units: km
        self.e0 = np.float128(e0) # Units: dimensionless

        extra_keys = ['weight', 'evolution_age', 'rejuvenation_age']

        self.extra_terms = {k: v for k, v in extra_terms.items()
                                 if k in extra_keys}

        for key in extra_keys:
            if key not in self.extra_terms.keys():
                self.extra_terms[key] = 0 if key != 'weight' else 1

        self.dadt_terms = None
        self.dedt_terms = None

        self.beta = (64/5) * (G**3*self.m1*self.m2*(self.m1+self.m2)) / (c**5)
        # units: km^4 s^-1

        self.__parameter_array = {
            'beta': self.beta,
            'm1': self.m1,
            'm2': self.m2,
            'a0': self.a0,
            'e0': self.e0,
            'weight': self.extra_terms['weight'],
            'evolution_age': self.extra_terms['evolution_age'],
            'rejuvenation_age': self.extra_terms['rejuvenation_age']
        }

    def coalescence_time(self):
        """Computes the coalescence time for the BSS in gigayears.

        Uses Eqn 10 from Nyadzani and Razzaque [1] to compute the
        coalescence time for the binary star system. Although this is
        strictly speaking an approximation, it converges on the
        result gained by numerically by Peters in 1964.

        [1] https://arxiv.org/pdf/1905.06086.pdf

        Returns:
            float -- the coalescence time for the binary star (units: ga).
        """

        circ = self.a0**4 / (4*self.beta)
        divisor = ((1-self.e0**(7/4))**(1/5)*(1+121/304 * self.e0**2))

        return (circ * (1-self.e0**2)**(7/2) / divisor) / 31557600000000000

    def specify_additional_term(self, da_or_de, func):
        """Adds additional terms to the RHS of the ODE governing evolution.

        Assumes that the signature of callable is callable(t, a, e).

        Arguments:
            da_or_de {string} -- Whether to modify da/dt or de/dt.
            func {function} -- A callable object to use to modify the ODE.

        Raises:
            ValueError -- If da_or_de is not 'da' or 'de'.
            TypeError -- if func is not a callable object.

        Returns:
            self -- an instance of itself, such that one may use
                    star.specify_addition_term().evolve_until() if
                    desired.
        """
        if da_or_de not in ['da', 'de']:
            raise ValueError("da_or_de must be either 'da' or 'de'!")

        if not callable(func):
            raise TypeError("func is not callable!")

        if da_or_de == 'da':
            self.dadt_terms = func
        else:
            self.dedt_terms = func

        return self

    def circularises(self):
        """Determines if the orbit in question circularises or not.

        This function is reasonably naive at present -- it assumes a BSS
        circularises if it's eccentricity becomes arbitrarily close to
        0 and it's final SMA is more than 2 solar radii (such that it
        does not merge).

        # Todo: Improve the logic here. Should the thresholds be customisable?

        Returns:
            bool -- True if the orbit circularises, False otherwise.
        """
        t, a, e = self.evolve_until_merger()

        if np.isclose(e[-1], 0.0) and a[-1] > 2*Solar_Radii:
            return True

        return False

    def evolve_until_merger(self):
        """Syntactic sugar for BSS.evolve_until(BSS.coalescence_time())

        Evolves a BSS in time until its coalescence time.

        Returns:
            mixed -- A 3-tuple containing the resultant time
                     array (in gigayears), and the resultant SMA (in
                     solar radii) and eccentricity arrays.
        """
        t_span = (0, self.coalescence_time() * 1e9 * 60 * 60 * 24 * 365.25)
        return self.evolve_until(t_span)

    def evolve_until(self, t_span):
        """Evolve the binary star system in time

        Uses a Runge-Kutta algorithm to evolve the binary star system
        over a specified range evolve_over.

        Arguments:
            t_span {tuple} -- A 2-tuple that corresponds to the start
                              and end points of integration.

        Returns:
            mixed -- A 3-tuple containing the resultant time
                     array (in gigayears), and the resultant SMA (in
                     solar radii) and eccentricity arrays.
        """

        def dadt(t, a, e):
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

            initial_term = (-self.beta / (a**3 * (1-e**2)**(7/2)))

            da = initial_term * (1 + 73/24 * e**2 + 37 / 96 * e ** 4)
            # Units: km/s

            if self.dadt_terms != None:
                da += self.dadt_terms(t, a, e)

            return da

        # Equation (4) from ibid
        def dedt(t, a, e):
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

            initial_term = (-19/12 * self.beta / (a**4*(1-e**2)**(5/2)))

            de = initial_term * (e + 121/304 * e ** 3) # Units: s^-1

            if self.dedt_terms != None:
                de += self.dedt_terms(t, a, e)

            return de

        def coupled_eqs(t, params):
            """
            Primary workhorse function. Computes the vector
            [da/dt, de/dt] for use in our integrator.

            Params:
                t [ndarray] A vector of times
                params [list] A list or 2-tuple of arguments. Must take
                              the form [a, e]

            Output:
                A list containing da/dt and de/dt
            """

            return np.array([dadt(t, *params), dedt(t, *params)])

        def integrate(t_eval):
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
            a, e = self.a0, self.e0

            a_arr = []
            e_arr = []

            yk = np.array([a, e])

            for t in t_eval:
                k1 = h * coupled_eqs(t, yk)
                k2 = h * coupled_eqs(t + 1/4 * h, yk + 1/4 * k1)

                k3 = h * coupled_eqs(t + 3/8 * h, yk + 3/32 * k1 \
                                                     + 9/32 * k2)

                k4 = h * coupled_eqs(t+12/13 * h, yk + 1932/2197 * k1 \
                                                     - 7200/2197 * k2 \
                                                     + 7293/2197 * k3)

                k5 = h * coupled_eqs(t + h, yk + 439/216 * k1 \
                                               - 8*k2 \
                                               + 3680/513 * k3
                                               - 845/4104*k4)

                k6 = h * coupled_eqs(t + 1/2 * h, yk - 8/27*k1 \
                                                     + 2*k2 \
                                                     - 3544/2565*k3 \
                                                     + 1859/4104 * k4 \
                                                     - 11/40 * k5)

                if e >= 1 or a <= 0:
                    # runaway integration, we should kill it
                    t_eval = (t_eval[0], t_eval[-1], len(e_arr))
                    break

                a_arr.append(yk[0])
                e_arr.append(yk[1])

                yk = yk + 25/216 * k1 + 1408/2565*k3 + 2197/4101 * k4 - 1/5 * k5

            return np.array(a_arr), np.array(e_arr)

        evolve_over = np.linspace(t_span[0], t_span[1], 10000)

        a, e = integrate(evolve_over)

        evolve_over /= 31557600000000000
        a /= (Solar_Radii * 1000)

        return evolve_over, a, e