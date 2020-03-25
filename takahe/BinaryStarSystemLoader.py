import numpy as np
from scipy.constants import c, G
from scipy.integrate import solve_ivp
from hoki import load
import pandas as pd

from takahe import BinaryStarSystem, BinaryStarSystemEnsemble

Solar_Mass = 1.989e30

def from_data(data):
    """
    Loads a binary star system from a dictionary of data.

    Arguments:
        data {dict} -- A dictionary containing the 4 elements necessary
        to solve the two body problem:
                       - M1 (mass of primary star)
                       - M2 (mass of secondary star)
                       - e0 (current eccentricity)
                       - a0/T (current semimajor axis / Period)
                    Peroid takes precedence over the SMA, so if one is provided, we use Kepler's law
                    to compute the SMA.

    Returns:
        BinaryStarSystem -- An ADT to represent the BSS.

    Raises:
        KeyError -- if data is not well-formed.
    """

    set_of_data_keys = set(data.keys())
    if not set_of_data_keys.issubset({'M1', 'M2', 'e0', 'a0', 'T'}):
        raise KeyError("data must contain definitions for M1, M2, e0, \
                        and a0/T!")

    if 'T' in data.keys():
        first_term = (G * (data['M1'] + data['M2']))/(4*np.pi**2)
        data['a0'] = (first_term * data['T'] ** 2) ** (1/3)

    return BinaryStarSystem.BinaryStarSystem(data['M1'],
                                             data['M2'],
                                             data['a0'],
                                             data['e0']
                                             )

def from_list(data_list):
    """Creates a binary star system ensemble from a list of configs

    Arguments:
        data_list {list} -- A list of config values. Each item in the
                            list must be acceptable by from_data; i.e.,
                            must contain M1, M2, e0, and a0/T.

    Returns:
        BinaryStarSystemEnsemble -- an ensemble representing the
                                    collection of Binary Star System
                                    objects.
    """
    ensemble = BinaryStarSystem.BinaryStarSystemEnsemble()

    for data in data_list:
        binary_star = from_data(data)
        ensemble.add(binary_star)

    return ensemble


def from_bpass(bpass_from, mass_fraction, a0_range=(0, 10)):
    """Loads a binary star system from the BPASS dataset.

    Opens the BPASS file you wish to use, uses hoki to load it into a
    dataframe, and returns a list of BSS objects.

    Arguments:
        bpass_from {str} -- the filename of the BPASS file to use

    Keyword Arguments:
        mass_fraction {int} -- If not None, assumes that
                               M1 = mass_fraction * M2 and uses this
                               to compute the masses. (default: {None})

        data {dict} -- A dictionary of data for the BSS.
                       Keywords used are M1 (primary mass),
                       M2 (secondary mass), e0 (initial eccentricity),
                       and a0 (initial SMA) or T (period).
                       (default: empty)

    Returns:
        [mixed] -- A list of BinaryStarSystem objects (if BPASS data is
                   used). A singular BinaryStarSystem object (if BPASS
                   data is NOT used).
    Raises:
        TypeError -- if a0_range is not exactly a 2-tuple of
                     floats/ints.
    """

    data = load._stellar_masses(bpass_from)

    if type(a0_range) != tuple or len(a0_range) != 2:
        raise TypeError("a0_range must be a tuple of length 2!")

    if (type(a0_range[0]) not in [int, float] and
        type(a0_range[1]) not in [int, float]):

        raise TypeError("a0_range must be a 2-tuple of ints or floats!")

    star_systems = BinaryStarSystemEnsemble.BinaryStarSystemEnsemble()

    for mass in data['stellar_mass']:
        M1 = mass_fraction * mass
        M2 = mass - M1

        a0 = np.random.uniform(*a0_range)
        e0 = np.random.uniform(0, 1)

        BSS = BinaryStarSystem.BinaryStarSystem(M1, M2, a0, e0)

        star_systems.add(BSS)

    return star_systems

def from_file(fname, name_hints=[], n_stars=100, mass=1e6):
    """
    Loads the first n_stars in a given file into a pandas dataframe.

    General utility loader for most cases. Can be replaced with a more
    flexible one, such as from_bpass().

    Arguments:
        fname {string} -- the path to the file we wish to open.

    Keyword Arguments:
        name_hints {list} -- A list of column names for pandas.
                             (default: {[]})
        n_stars {number} -- The number of stars (rows in file) to load
                            (default: {100})
        mass {number} -- The total mass of the ensemble. This is used to
                         populate the ensemble with weight*mass stars of
                         a given stellar configuration (default: {1e6})
    """

    df = pd.read_csv(fname,
                     names=name_hints,
                     nrows=n_stars,
                     sep="   ",
                     engine='python')

    ensemble = BinaryStarSystemEnsemble.BinaryStarSystemEnsemble()

    for row in df.iterrows():
        number_of_stars_of_type = int(np.ceil(row[1]['weight'] * mass))

        for n in range(number_of_stars_of_type):
            extra_terms = {k:v for k,v in row[1].items()
                               if k not in ['m1', 'm2', 'a0', 'e0']
                          }

            star = BinaryStarSystem.BinaryStarSystem(row[1]['m1'],
                                                     row[1]['m2'],
                                                     row[1]['a0'],
                                                     row[1]['e0'],
                                                     extra_terms)

            ensemble.add(star)

    return ensemble



def random_from_file(fname, name_hints=[], n_stars=100, mass=1e6):
    """
    Loads a random sample of stars from a file.

    This code is particularly hacky. We should find a better way to
    accomplish this.

    Arguments:
        fname {string} -- The path to the file you want to load

    Keyword Arguments:
        limit {number} -- The number of stars to load (default: {10})
        n {number} -- The number of lines in the file (default: {1000})

    Returns:
        {BinaryStarSystemEnsemble} -- An ensemble object representing
                                      the ensemble of objects,
    """
    import mmap, linecache
    ensemble = BinaryStarSystemEnsemble.BinaryStarSystemEnsemble()

    # Determine the number of lines in the file requested.
    n_lines = 0
    f = open(fname, "r+")
    buf = mmap.mmap(f.fileno(), 0)
    readline = buf.readline
    while readline():
        n_lines += 1
    f.close()
    lines = np.random.randint(1, n_lines, n_stars)

    j = 0
    for line in lines:
        l = linecache.getline(fname, line).strip()
        m = l.strip()
        n = m.split("   ")

        star = list(map(float, n))

        for i in range(int(star[5] * mass)): # Add weight * mass stars
            binary_star = BinaryStarSystem.BinaryStarSystem(*star[0:4])
            ensemble.add(binary_star)

        print(f"{j/n_stars * 100}%\r")
        j += 1

    return ensemble
