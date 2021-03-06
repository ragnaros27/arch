import timeit

import numpy as np
import pytest
from numpy.random import RandomState
from numpy.testing import assert_almost_equal
from scipy.special import gamma

import arch.univariate.recursions_python as recpy
from arch.compat.python import range

try:
    import arch.univariate.recursions as rec_cython

    missing_extension = False
except ImportError:
    missing_extension = True

if missing_extension:
    rec = recpy
else:
    rec = rec_cython

try:
    import numba  # noqa

    missing_numba = False
except ImportError:
    missing_numba = True


class Timer(object):
    def __init__(self, first, first_name, second, second_name, model_name,
                 setup, repeat=5, number=10):
        self.first_code = first
        self.second_code = second
        self.setup = setup
        self.first_name = first_name
        self.second_name = second_name
        self.model_name = model_name
        self.repeat = repeat
        self.number = number
        self._run = False
        self.times = []
        self._codes = [first, second]
        self.ratio = np.inf

    def display(self):
        if not self._run:
            self.time()
        self.ratio = self.times[0] / self.times[1]

        print(self.model_name + ' timing')
        print(self.first_name + ': ' + str(self.times[0]) + 's')
        print(self.second_name + ': ' + str(self.times[1]) + 's')
        print(self.first_name + '/' + self.second_name + ' Ratio: ' +
              str(self.ratio) + 's')
        print('\n')

    def time(self):
        self.times = []
        for code in self._codes:
            timer = timeit.Timer(code, setup=self.setup)
            self.times.append(min(timer.repeat(self.repeat, self.number)))
        return None


class TestRecursions(object):
    @classmethod
    def setup_class(cls):
        cls.nobs = 1000
        cls.rng = RandomState(12345)
        cls.resids = cls.rng.standard_normal(cls.nobs)
        cls.sigma2 = np.zeros_like(cls.resids)
        var = cls.resids.var()
        var_bounds = np.array([var / 1000000.0, var * 1000000.0])
        cls.var_bounds = np.ones((cls.nobs, 2)) * var_bounds
        cls.backcast = 1.0
        cls.timer_setup = """
import numpy as np
import arch.univariate.recursions as rec
import arch.univariate.recursions_python as recpy
from arch.compat.python import range

nobs = 10000
resids = np.random.standard_normal(nobs)
sigma2 = np.zeros_like(resids)
var = resids.var()
backcast = 1.0
var_bounds = np.array([var / 1000000.0, var * 1000000.0])
var_bounds = np.ones((nobs, 2)) * var_bounds
"""

    def test_garch(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 1, 1, nobs, backcast, self.var_bounds)
        sigma2_numba = sigma2.copy()
        recpy.garch_recursion_python(parameters, fresids, sresids, sigma2, 1,
                                     1, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_numba, sigma2)
        assert_almost_equal(sigma2_python, sigma2)

        parameters = np.array([.1, -.4, .3, .2])
        recpy.garch_recursion_python(parameters, fresids, sresids, sigma2, 1,
                                     1, 1, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, .4, 3, 2])
        recpy.garch_recursion_python(parameters, fresids, sresids, sigma2, 1,
                                     1, 1, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, .4, .3, .2])
        mod_fresids = fresids.copy()
        mod_fresids[:1] = np.inf
        recpy.garch_recursion_python(parameters, mod_fresids, sresids, sigma2, 1,
                                     1, 1, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])
        rec.garch_recursion(parameters, mod_fresids, sresids, sigma2, 1,
                            1, 1, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

    def test_harch(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        lags = np.array([1, 5, 22], dtype=np.int32)
        recpy.harch_recursion_python(parameters, resids, sigma2, lags, nobs,
                                     backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        recpy.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                              self.var_bounds)
        sigma2_numba = sigma2.copy()
        rec.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                            self.var_bounds)
        assert_almost_equal(sigma2_numba, sigma2)
        assert_almost_equal(sigma2_python, sigma2)

        parameters = np.array([-.1, -.4, .3, .2])
        recpy.harch_recursion_python(parameters, resids, sigma2, lags, nobs,
                                     backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, 4e8, 3, 2])
        recpy.harch_recursion_python(parameters, resids, sigma2, lags, nobs,
                                     backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, 4e8, 3, 2])
        mod_resids = resids.copy()
        mod_resids[:10] = np.inf
        recpy.harch_recursion_python(parameters, mod_resids, sigma2, lags, nobs,
                                     backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])
        rec.harch_recursion(parameters, mod_resids, sigma2, lags, nobs, backcast,
                            self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

    def test_arch(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        p = 3

        recpy.arch_recursion_python(parameters, resids, sigma2, p, nobs,
                                    backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        recpy.arch_recursion(parameters, resids, sigma2, p, nobs,
                             backcast, self.var_bounds)
        sigma2_numba = sigma2.copy()
        rec.arch_recursion(parameters, resids, sigma2, p, nobs, backcast,
                           self.var_bounds)
        assert_almost_equal(sigma2_numba, sigma2)
        assert_almost_equal(sigma2_python, sigma2)

        parameters = np.array([-.1, -.4, .3, .2])
        recpy.arch_recursion_python(parameters, resids, sigma2, p, nobs,
                                    backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, 4e8, 3, 2])
        recpy.arch_recursion_python(parameters, resids, sigma2, p, nobs,
                                    backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        mod_resids = resids.copy()
        mod_resids[:10] = np.inf
        recpy.arch_recursion_python(parameters, mod_resids, sigma2, p, nobs,
                                    backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])
        rec.arch_recursion(parameters, mod_resids, sigma2, p, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

    def test_garch_power_1(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        fresids = np.abs(resids) ** 1.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 1, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)

    def test_garch_direct(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        fresids = np.abs(resids) ** 2.0
        sresids = np.sign(resids)

        for t in range(nobs):
            if t == 0:
                sigma2[t] = parameters.dot(
                    np.array([1.0, backcast, 0.5 * backcast, backcast]))
            else:
                var = np.array([1.0,
                                resids[t - 1] ** 2.0,
                                resids[t - 1] ** 2.0 * (resids[t - 1] < 0),
                                sigma2[t - 1]])
                sigma2[t] = parameters.dot(var)

        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)

    def test_garch_no_q(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 1, 0, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            0, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)

    def test_garch_no_p(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              0, 1, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 0, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)

    def test_garch_no_o(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, .4, .3, .2])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 0, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 0,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)

    def test_garch_arch(self):
        backcast = self.backcast
        nobs, resids, sigma2 = self.nobs, self.resids, self.sigma2

        parameters = np.array([.1, .4, .3, .2])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        rec.garch_recursion(parameters, fresids, sresids, sigma2,
                            3, 0, 0, nobs, backcast, self.var_bounds)
        sigma2_garch = sigma2.copy()
        rec.arch_recursion(parameters, resids, sigma2, 3, nobs, backcast,
                           self.var_bounds)

        assert_almost_equal(sigma2_garch, sigma2)

    def test_bounds(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([1e100, .4, .3, .2])
        lags = np.array([1, 5, 22], dtype=np.int32)
        recpy.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                              self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                            self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([-1e100, .4, .3, .2])
        recpy.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                              self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
                            self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert_almost_equal(sigma2, self.var_bounds[:, 0])

        parameters = np.array([1e100, .4, .3, .2])
        fresids = resids ** 2.0
        sresids = np.sign(resids)

        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 1, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([-1e100, .4, .3, .2])
        recpy.garch_recursion(parameters, fresids, sresids, sigma2,
                              1, 1, 1, nobs, backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1,
                            1, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert_almost_equal(sigma2, self.var_bounds[:, 0])

        parameters = np.array([1e100, .4, .3, .2])
        recpy.arch_recursion(parameters, resids, sigma2, 3, nobs, backcast,
                             self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.arch_recursion(parameters, resids, sigma2, 3, nobs, backcast,
                           self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([-1e100, .4, .3, .2])
        recpy.arch_recursion(parameters, resids, sigma2, 3, nobs, backcast,
                             self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.arch_recursion(parameters, resids, sigma2, 3, nobs, backcast,
                           self.var_bounds)
        assert_almost_equal(sigma2_python, sigma2)
        assert_almost_equal(sigma2, self.var_bounds[:, 0])

    def test_egarch(self):
        nobs = self.nobs
        parameters = np.array([0.0, 0.1, -0.1, 0.95])
        resids, sigma2 = self.resids, self.sigma2
        p = o = q = 1
        backcast = 0.0
        var_bounds = self.var_bounds
        lnsigma2 = np.empty_like(sigma2)
        std_resids = np.empty_like(sigma2)
        abs_std_resids = np.empty_like(sigma2)
        recpy.egarch_recursion(parameters, resids, sigma2, p, o, q, nobs,
                               backcast, var_bounds, lnsigma2, std_resids,
                               abs_std_resids)
        sigma2_numba = sigma2.copy()
        recpy.egarch_recursion_python(parameters, resids, sigma2, p, o, q,
                                      nobs, backcast, var_bounds, lnsigma2,
                                      std_resids, abs_std_resids)
        sigma2_python = sigma2.copy()
        rec.egarch_recursion(parameters, resids, sigma2, p, o, q, nobs,
                             backcast, var_bounds, lnsigma2, std_resids,
                             abs_std_resids)
        assert_almost_equal(sigma2_numba, sigma2)
        assert_almost_equal(sigma2_python, sigma2)

        norm_const = np.sqrt(2 / np.pi)
        for t in range(nobs):
            lnsigma2[t] = parameters[0]
            if t == 0:
                lnsigma2[t] += parameters[3] * backcast
            else:
                stdresid = resids[t - 1] / np.sqrt(sigma2[t - 1])
                lnsigma2[t] += parameters[1] * (np.abs(stdresid) - norm_const)
                lnsigma2[t] += parameters[2] * stdresid
                lnsigma2[t] += parameters[3] * lnsigma2[t - 1]
            sigma2[t] = np.exp(lnsigma2[t])
        assert_almost_equal(sigma2_python, sigma2)

        parameters = np.array([-100.0, 0.1, -0.1, 0.95])
        recpy.egarch_recursion_python(parameters, resids, sigma2, p, o, q,
                                      nobs, backcast, var_bounds, lnsigma2,
                                      std_resids, abs_std_resids)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([0.0, 0.1, -0.1, 9.5])
        recpy.egarch_recursion_python(parameters, resids, sigma2, p, o, q,
                                      nobs, backcast, var_bounds, lnsigma2,
                                      std_resids, abs_std_resids)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([0.0, 0.1, -0.1, 0.95])
        mod_resids = resids.copy()
        mod_resids[:1] = np.inf
        recpy.egarch_recursion_python(parameters, resids, sigma2, p, o, q,
                                      nobs, backcast, var_bounds, lnsigma2,
                                      std_resids, abs_std_resids)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

    def test_midas_hyperbolic(self):
        nobs, resids, = self.nobs, self.resids
        sigma2, backcast = self.sigma2, self.backcast

        parameters = np.array([.1, 0.8, 0])
        j = np.arange(1, 22+1)
        weights = gamma(j+0.6) / (gamma(j+1) * gamma(0.6))
        weights = weights / weights.sum()
        recpy.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, self.var_bounds)
        sigma2_numba = sigma2.copy()
        recpy.midas_recursion_python(parameters, weights, resids, sigma2, nobs,
                                     backcast, self.var_bounds)
        sigma2_python = sigma2.copy()
        rec.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, self.var_bounds)
        assert_almost_equal(sigma2_numba, sigma2)
        assert_almost_equal(sigma2_python, sigma2)

        mod_resids = resids.copy()
        mod_resids[:10] = np.inf
        recpy.midas_recursion_python(parameters, weights, mod_resids, sigma2, nobs, backcast,
                                     self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, 10e10, 0])
        j = np.arange(1, 22+1)
        weights = gamma(j+0.6) / (gamma(j+1) * gamma(0.6))
        weights = weights / weights.sum()
        recpy.midas_recursion_python(parameters, weights, resids, sigma2, nobs, backcast,
                                     self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])
        rec.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

        parameters = np.array([.1, -0.4, 0])
        recpy.midas_recursion_python(parameters, weights, resids, sigma2, nobs, backcast,
                                     self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])
        rec.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, self.var_bounds)
        assert np.all(sigma2 >= self.var_bounds[:, 0])
        assert np.all(sigma2 <= 2 * self.var_bounds[:, 1])

    @pytest.mark.skipif(missing_numba or missing_extension, reason='numba not installed')
    def test_garch_performance(self):
        garch_setup = """
parameters = np.array([.1, .4, .3, .2])
fresids = resids ** 2.0
sresids = np.sign(resids)
        """

        garch_first = """
recpy.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1, 1, nobs,
backcast, var_bounds)
        """
        garch_second = """
rec.garch_recursion(parameters, fresids, sresids, sigma2, 1, 1, 1, nobs, backcast,
var_bounds)
        """
        timer = Timer(garch_first, 'Numba', garch_second, 'Cython', 'GARCH',
                      self.timer_setup + garch_setup)
        timer.display()
        assert timer.ratio < 10.0

    @pytest.mark.skipif(missing_numba or missing_extension, reason='numba not installed')
    def test_harch_performance(self):
        harch_setup = """
parameters = np.array([.1, .4, .3, .2])
lags = np.array([1, 5, 22], dtype=np.int32)
        """

        harch_first = """
recpy.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast,
var_bounds)
        """

        harch_second = """
rec.harch_recursion(parameters, resids, sigma2, lags, nobs, backcast, var_bounds)
        """

        timer = Timer(harch_first, 'Numba', harch_second, 'Cython', 'HARCH',
                      self.timer_setup + harch_setup)
        timer.display()
        assert timer.ratio < 10.0

    @pytest.mark.skipif(missing_numba or missing_extension, reason='numba not installed')
    def test_egarch_performance(self):
        egarch_setup = """
parameters = np.array([0.0, 0.1, -0.1, 0.95])
p = o = q = 1
backcast = 0.0
lnsigma2 = np.empty_like(sigma2)
std_resids = np.empty_like(sigma2)
abs_std_resids = np.empty_like(sigma2)
        """

        egarch_first = """
rec.egarch_recursion(parameters, resids, sigma2, p, o, q, nobs, backcast,
var_bounds, lnsigma2, std_resids, abs_std_resids)
"""

        egarch_second = """
recpy.egarch_recursion(parameters, resids, sigma2, p, o, q, nobs, backcast,
var_bounds, lnsigma2, std_resids, abs_std_resids)
"""
        timer = Timer(egarch_first, 'Numba', egarch_second, 'Cython', 'EGARCH',
                      self.timer_setup + egarch_setup)
        timer.display()

    @pytest.mark.skipif(missing_numba or missing_extension, reason='numba not installed')
    def test_midas_performance(self):
        midas_setup = """
from scipy.special import gamma
parameters = np.array([.1, 0.8, 0])
j = np.arange(1,22+1)
weights = gamma(j+0.6) / (gamma(j+1) * gamma(0.6))
weights = weights / weights.sum()
"""

        midas_first = """
recpy.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, var_bounds)
                """
        midas_second = """
rec.midas_recursion(parameters, weights, resids, sigma2, nobs, backcast, var_bounds)
"""
        timer = Timer(midas_first, 'Numba', midas_second, 'Cython', 'GARCH',
                      self.timer_setup + midas_setup)
        timer.display()
        assert timer.ratio < 10.0


def test_bounds_check():
    var_bounds = np.array([.1, 10])
    assert_almost_equal(recpy.bounds_check_python(-1.0, var_bounds), .1)
    assert_almost_equal(recpy.bounds_check_python(20.0, var_bounds), 10 + np.log(20.0 / 10.0))
    assert_almost_equal(recpy.bounds_check_python(np.inf, var_bounds), 1010.0)
