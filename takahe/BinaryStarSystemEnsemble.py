from takahe import BinaryStarSystem

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

    def add(self, binary_star):
        """Add a BSS to the current ensemble.

        Arguments:
            binary_star {BinaryStarSystem} -- The BSS to add.

        Raises:
            TypeError -- If the Binary Star System is not an instance of
                         BinaryStarSystem.BinaryStarSystem.
        """
        if type(binary_star) != BinaryStarSystem.BinaryStarSystem:
            raise TypeError("binary_star must be an instance of BinaryStarSystem!")

        self.__ensemble.append(binary_star)
        self.__count += 1

    def merge_rate(self, t_merge, return_as="rel"):
        """COmputes the merge rate for this ensemble.

        Computes the merge rate for this system in a given timespan.
        Merge rate is defined as the number of systems that merge in
        some timespan t_merge (possibly relative to the number of
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
            flaot -- The merge rate of the ensemble.

        Raises:
            ValueError -- if return_as is anything other than "abs" or
                          "rel".
        """
        count = 0

        if return_as.lower() not in ['abs', 'rel']:
            raise ValueError("return_as must be either abs or rel")

        for i in range(self.__count):
            binary_star = self.__ensemble[i]
            valid = (binary_star.coalescence_time() <= t_merge)
            if valid:
                count += 1

        if return_as == 'abs':
            return count
        elif return_as == 'rel':
            return count / self.__count

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
