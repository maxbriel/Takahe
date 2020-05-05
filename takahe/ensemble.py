import numpy as np
import matplotlib.pyplot as plt

import takahe
from takahe.constants import *
from kea.hist import BPASS_hist, histogram

def create():
    """Creates a BinaryStarSystemEnsemble object (i.e., a collection of
    binary star systems).

    Wrapper for BinaryStarSystemEnsemble()

    Returns:
        BinaryStarSystemEnsemble -- The ensemble object.
    """
    return BinaryStarSystemEnsemble()

class BinaryStarSystemEnsemble:
    """Represents a collection of binary star systems.

    Represents a group of binary star system objects. Will be
    generated if the loader encounters a group of BSS objects (e.g.,
    from BPASS).
    """

    def __init__(self):
        self.__ensemble = []
        self.__count = 0
        self.__pointer = 0
        self.__min_lifetime = np.infty
        self.__max_lifetime = 0
        self.__total_mass = 0

    def track_through_phase_space(self, in_range=(0, 0)):
        """Tracks an entire ensemble as each star evolves through phase
        space.

        Given an ensemble of stars, propagates them through time and
        uses the track_evolution() method of the BinaryStarSystem class
        to create a 3D phase-space plot of the ensemble.

        Keyword Arguments:
            in_range {tuple} -- The range you would like all coalescences
                                in the resultant ensemble to be. Leave
                                as (0, 0) to consider all coalescences.
                                (default: {(0, 0)})

        Returns:
            {matplotlib.axes3D} -- The axis object generated by the method.
        """
        if in_range != (0, 0):
            ensemble = self.find_coalescence_between(in_range,
                                                     find_all=True)
        else:
            ensemble = self

        ax = None

        for star in ensemble:
            ax = star.track_evolution(ax=ax)

        return ax

    def get(self, key):
        """Fetches a given parameter of the binary system.

        Allowed parameters are:
            mass: The total mass of the ensemble (in Solar Masses)
            size: The size of the ensemble (same as self.size())
            lifetime: A 2-tuple representing (youngest, oldest) for the
                      ages of stars in the system (in gigayears)

        Arguments:
            key {string} -- The key to look up.
        """
        return {'mass': self.__total_mass / Solar_Mass,
                'size': self.size(),
                'lifetime': (self.__min_lifetime, self.__max_lifetime)
                }[key]

    def find_coalescence_between(self, in_range, find_all=False):
        """Find a system that coalesces within a range of time.

        Searches through the ensemble to find a coalescence time within
        the open interval (low, high) and returns the first encountered.

        Arguments:
            in_range {tuple/list} -- The open interval to search for a
                                     coalescence between.

        Keyword Arguments:
            find_all {bool} -- True if you want to return *all*
                               coalescences in the interval, False
                               otherwise.

        Returns:
            {tuple} -- A 2-tuple, the first element is the index the
                       BSS was found at, and the second is the BSS found.
                       Only returned if find_all is False, and a system
                       was found.

            {BinaryStarSystemEnsemble} -- an ensemble containing all
                                          suitable coalescences.

        Raises:
            LookupError -- if the finder could not find a suitable BSS
        """
        i = 0

        high = max(in_range)
        low = min(in_range)

        found = takahe.ensemble.create()

        for star in self:
            if star.coalescence_time() < high and star.coalescence_time() > low:
                if not find_all:
                    return i, star
                found.add(star)
            i += 1

        if found.size() > 0:
            return found

        raise LookupError("A suitable star system was not found!")

    def add(self, binary_star):
        """Add a BSS to the current ensemble.

        Arguments:
            binary_star {BinaryStarSystem} -- The BSS to add.

        Raises:
            TypeError -- If the Binary Star System is not an instance of
                         BinaryStarSystem.
        """
        if not isinstance(binary_star, takahe.BSS.BinaryStarSystem):
            raise TypeError("binary_star must be an instance \
                             of BinaryStarSystem!")

        lifetime = binary_star.lifetime()

        if lifetime > self.__max_lifetime:
            self.__max_lifetime = lifetime
        elif lifetime < self.__min_lifetime:
            self.__min_lifetime = lifetime

        self.__ensemble.append(binary_star)
        self.__count += 1
        self.__total_mass += binary_star.get('m1') + binary_star.get('m2')

    def average_coalescence_time(self):
        """Computes the average coalescence time for the binary star
        system.

        Returns:
            float -- The average over all the coalescence times in the
                     ensemble.
        """

        running_sum = 0

        for binary_star in self.__ensemble:
            running_sum += binary_star.coalescence_time()

        return running_sum / self.size()

    def get_cts(self):
        cts = []
        for star in self:
            cts.append(star.coalescence_time())

        return cts

    def merge_rate(self, t_merge, return_as="rel"):
        """Computes the merge rate for this ensemble.

        Computes the merge rate for this system in a given timespan.
        Merge rate is defined as the number of systems that merge in
        some timespan t_merge (optionally relative to the number of
        systems in the ensemble).

        Arguments:
            t_merge {float} -- The timespan under consideration. Must be
                               in gigayears; no conversion is
                               performed before comparison.

        Keyword Arguments:
            return_as {str} -- "abs" or "rel" depending on whether the
                               merge rate should be returned as an
                               absolute count or relative count
                               (to the number of BSS in the ensemble).
                               If defined as relative, then the merge
                               rate is constrained to be in the interval
                               [0, 1]. (default: {"rel"})

        Returns:
            float -- The merge rate of the ensemble.

        Raises:
            ValueError -- if return_as is anything other than "abs" or
                          "rel".
        """
        count = 0

        if return_as.lower() not in ['abs', 'rel']:
            raise ValueError("return_as must be either abs or rel")

        for i in range(self.__count):
            binary_star = self.__ensemble[i]
            valid = (binary_star.lifetime() <= t_merge)
            if valid:
                count += 1

        if return_as == 'abs':
            return count
        elif return_as == 'rel':
            return count / self.__count

    def compute_existence_time_distribution(self, *argv, **kwargs):
        hist = BPASS_hist()
        edges = hist.getLinEdges()

        old_mr = 0
        for bin in range(0, hist.getNBins()-1):
            mr = self.merge_rate(edges[bin+1], return_as='abs')
            this_mr = (mr - old_mr)
            plt_mr = self.size() - this_mr
            hist.Fill(edges[bin], plt_mr, ty="lin")
            old_mr += this_mr

        bin_widths = [hist.getBinWidth(i) for i in range(0,hist.getNBins())]
        hist = hist / 1e6 / bin_widths

        hist.plotLog(*argv, **kwargs)

        return hist

    def legacy_compute_delay_time_distribution(self, *argv, **kwargs):
        """Generates the event rate plot for this ensemble.

        LEGACY FUNCTION, this is here as it is of potential use for
        those using the BPASS time bins, however it's unlikely to be
        developed further, and may be removed in a future release.

        Computes the instantaneous delay-time distribution for this
        ensemble. Returns the histogram generated, however the histogram
        is saved internally in Kea as a matplotlib plot.

        Thus, given an ensemble called ens, one may use

        >>> ens.compute_delay_time_distribution()
        >>> plt.show()

        to render it.

        Note that the binning is logarithmic so bin size does vary
        across the plot.

        Thanks to Max Briel (https://github.com/maxbriel/) for his
        assistance in writing this function.

        Returns:
            hist -- the (kea-generated) histogram object.
        """

        hist = BPASS_hist()
        old_mr = 0
        edges = hist.getLinEdges()

        for bin in range(0, hist.getNBins()-1):
            mr = self.merge_rate(edges[bin+1], return_as='abs')
            this_mr = mr - old_mr
            hist.Fill(edges[bin], this_mr, ty="lin")
            old_mr += this_mr

        bin_widths = [hist.getBinWidth(i) for i in range(0,hist.getNBins())]
        hist = hist / 1e6 / bin_widths

        if 'space' in kwargs.keys():
            plotting_method = kwargs['space']
            del kwargs['space']
        else:
            plotting_method = 'log'

        if plotting_method == 'lin':
            hist.plotLin(*argv, **kwargs)
        else:
            hist.plotLog(*argv, **kwargs)

        plt.yscale('log')

        return hist

    def size(self):
        """Get the size of the ensemble.

        Returns:
            int -- The number of BSS in the ensemble.
        """
        return self.__count

    """
    Magic methods, in order to be able to compute the size of the
    ensemble, and iterate over it, for example. These are uninteresting
    and therefore do not contain any docstrings.
    """
    def __getitem__(self, key):
        return self.__ensemble[key]

    def __len__(self):
        return self.size()

    def __iter__(self):
        return self

    def __next__(self):
        if self.__pointer >= self.__count:
            raise StopIteration
        else:
            self.__pointer += 1
            return self.__ensemble[self.__pointer - 1]
