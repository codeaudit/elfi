import elfi
import numpy as np

from functools import partial

from elfi.core import simulator_operation
from elfi.core import normalize_data
from elfi.core import Node
from elfi.core import ObservedMixin

from mocks import MockSimulator, MockSequentialSimulator
from mocks import MockSummary, MockSequentialSummary
from mocks import MockDiscrepancy, MockSequentialDiscrepancy

class TestSimulatorOperation():

    def test_normal_use(self):
        ret1 = np.array([5])
        ret2 = np.array([6])
        mock = MockSimulator([ret1, ret2])
        prng = np.random.RandomState(1234)
        input_dict = {
                "n": 2,
                "data": [np.atleast_2d([[1], [2]]),
                         np.atleast_2d([[3], [4]])],
                "random_state": prng.get_state()
                }
        output_dict = simulator_operation(mock, True, input_dict)
        prng.rand()
        print(output_dict)
        assert mock.n_calls == 1
        assert output_dict["n"] == 2
        assert np.array_equal(output_dict["data"], np.vstack((ret1, ret2)))
        new_state = prng.get_state()
        assert output_dict["random_state"][0] == new_state[0]
        assert np.array_equal(output_dict["random_state"][1], new_state[1])
        assert output_dict["random_state"][2] == new_state[2]
        assert output_dict["random_state"][3] == new_state[3]
        assert output_dict["random_state"][4] == new_state[4]


class Test_vectorization():
    """Test operation vectorization
    """

    def test_as_vectorized_simulator(self):
        ret1 = np.array([5])
        ret2 = np.array([6])
        mock_seq = partial(elfi.core.vectorize_simulator, MockSequentialSimulator([ret1, ret2]))
        mock_vec = MockSimulator([ret1, ret2])
        input_data = [np.atleast_2d([[1], [2]]), np.atleast_2d([[3], [4]])]
        output_seq = mock_seq(*input_data, n_sim=2)
        output_vec = mock_vec(*input_data, n_sim=2)
        assert np.array_equal(output_seq, output_vec)

    def test_as_vectorized_summary(self):
        ret1 = np.array([5])
        ret2 = np.array([6])
        mock_seq = partial(elfi.core.vectorize_summary, MockSequentialSummary([ret1, ret2]))
        mock_vec = MockSummary([ret1, ret2])
        input_data = [np.atleast_2d([[1], [2]]), np.atleast_2d([[3], [4]])]
        output_seq = mock_seq(*input_data)
        output_vec = mock_vec(*input_data)
        assert np.array_equal(output_seq, output_vec)

    def test_as_vectorized_discrepancy(self):
        ret1 = np.array([5])
        ret2 = np.array([6])
        mock_seq = partial(elfi.core.vectorize_discrepancy, MockSequentialDiscrepancy([ret1, ret2]))
        mock_vec = MockDiscrepancy([ret1, ret2])
        x = (np.atleast_2d([[1], [2]]), np.atleast_2d([[3], [4]]))
        y = (np.atleast_2d([[5]]), np.atleast_2d([[6]]))
        output_seq = mock_seq(x, y)
        output_vec = mock_vec(x, y)
        assert np.array_equal(output_seq, output_vec)


def test_node_data_sub_slicing():
    mu = elfi.Prior('mu', 'uniform', 0, 4)
    ar1 = mu.acquire(10).compute()
    ar2 = mu.acquire(5).compute()
    assert np.array_equal(ar1[0:5], ar2)

    ar3 = mu.acquire(20).compute()
    assert np.array_equal(ar1, ar3[0:10])


def test_generate_vs_acquire():
    mu = elfi.Prior('mu', 'uniform', 0, 4)
    ar1 = mu.acquire(10).compute()
    ar2 = mu.generate(5).compute()
    ar12 = mu.acquire(15).compute()
    assert np.array_equal(np.vstack((ar1, ar2)), ar12)


class TestNode():
    def test_construction1(self):
        a = Node('a')
        assert a.name == 'a'
        assert a.parents == []
        assert a.children == []
        assert a.is_root()
        assert a.is_leaf()

    def test_construction(self):
        a = Node('a')
        b = Node('b')
        c = Node('c', b)
        d = Node('d', a, c)
        e = Node('e', d)
        f = Node('f', d, c)
        g = Node('g', e, f)
        assert b.is_root()
        assert c.parents == [b]
        assert d.parents == [a, c]
        assert g.parents == [e, f]
        assert b.children == [c]
        assert c.children == [d, f]
        assert g.is_leaf()

    def test_construction_add(self):
        b = Node('b')
        c = Node('c')
        d = Node('d')
        c.add_parent(b)
        assert c.parents == [b]
        assert b.children == [c]
        b._add_child(d)
        assert b.children == [c, d]
        assert d.parents == []  # _add_child doesn't call add_parent

    def test_construction_unique(self):
        b = Node('b')
        c = Node('c', b)
        c.add_parent(b)
        assert c.parents == [b]
        assert b.children == [c]

    def test_construction_add_index(self):
        b = Node('b')
        c = Node('c', b)
        d = Node('d')
        e = Node('e')
        c.add_parent(d, index=0, index_child=0)
        assert c.parents == [d, b]
        assert b.children == [c]
        assert d.children == [c]
        b._add_child(e, index=0)
        assert b.children == [e, c]
        assert e.parents == []  # _add_child doesn't call add_parent

    def test_construction_index_out_of_bounds(self):
        b = Node('b')
        c = Node('c')
        try:
            c.add_parent(b, index=13)
            b._add_child(c, index=13)
            assert False
        except ValueError:
            assert True

    def test_construction_acyclic(self):
        a = Node('a')
        b = Node('b', a)
        c = Node('c', b)
        try:
            a.add_parent(c)
            assert False
        except ValueError:
            assert True

    def test_family_tree(self):
        a = Node('a')
        b = Node('b')
        c = Node('c', b)
        d = Node('d', a, c)
        e = Node('e', d)
        f = Node('f', d, c)
        g = Node('g', e, f)
        assert a.descendants == [d, e, f, g]
        assert e.descendants == [g]
        assert g.descendants == []
        assert g.ancestors == [e, f, d, a, c, b]
        assert c.ancestors == [b]
        assert a.ancestors == []
        assert d.neighbours == [e, f, a, c]

    def test_component(self):
        a = Node('a')
        b = Node('b')
        c = Node('c', b)
        d = Node('d', a, c)
        e = Node('e', d)
        f = Node('f', d, c)
        g = Node('g', e, f)
        assert c.component == [c, b, d, f, e, g]
        assert g.component == [g, e, f, d, a, c, b]

    def test_remove_parent(self):
        a = Node('a')
        b = Node('b', a)
        c = Node('c', b)
        c.remove_parent(0)
        assert c.parents == []
        assert b.children == []
        b.remove_parent(a)
        assert b.parents == []
        assert a.children == []

    def test_remove(self):
        a = Node('a')
        b = Node('b')
        c = Node('c', a, b)
        d = Node('d', c)
        e = Node('e', c)
        c.remove(keep_parents=False, keep_children=False)
        assert c.children == []
        assert c.parents == []
        assert b.children == []
        assert e.parents == []

    def test_change_to(self):
        a = Node('a')
        b = Node('b')
        c = Node('c', a, b)
        d = Node('d', c)
        e = Node('e', c)
        f = Node('f')
        c_new = Node('c_new', a, f)
        c = c.change_to(c_new, transfer_parents=False, transfer_children=True)
        assert c.parents == [a, f]
        assert c.children == [d, e]
        c_new2 = Node('c_new2', a)
        c = c.change_to(c_new2, transfer_parents=True, transfer_children=False)
        assert c.parents == [a, f]
        assert c.children == []

    def test_none_parent(self):
        a = Node('a', None)
        assert a.parents == []


class TestObservedMixin():

    def test_numpy_array_observation(self):
        np.random.seed(21273632)
        for i in range(20):
            n_dims = np.random.randint(1,5)
            dims = [np.random.randint(1,5) for i in range(n_dims)]
            dims[0] = max(2, dims[0])
            dims = tuple(dims)
            obs = np.zeros(dims)
            o = ObservedMixin("o", lambda x: x, None, observed=obs)
            assert o.observed.shape == (1, ) + dims
            assert o.observed.dtype == obs.dtype
            np.testing.assert_array_equal(o.observed[0], obs)

    def test_list_observation(self):
        # if list or tuple is passed as observation, it will be auto-converted to numpy array
        class MockClass():
            pass
        for obs, dtype, shape in [
                ([False], bool, (1,)),
                ((1, 2, 3), int, (3,)),
                ([1.2, 2.3], float, (2,)),
                ([(1,2), (2.3,3.4)], float, (2,2)),
                ([set((1,2))], object, (1,)),
                ([{1:2}, {2:4}], object, (2,)),
                ([1, MockClass()], object, (2,)),
                           ]:
            o = ObservedMixin("o", lambda x: x, None, observed=obs)
            assert o.observed.shape == (1,) + shape
            assert o.observed.dtype == dtype
            np.testing.assert_array_equal(o.observed[0], obs)

    def test_value_observation(self):
        # raw types are converted to at least 2d arrays
        class MockClass():
            pass
        for obs, dtype in [
                (123, int),
                (123.0, float),
                (False, bool),
                ({3:4}, object),
                (set((5,6)), object),
                (MockClass(), object),
                ("string", object),
                    ]:
            o = ObservedMixin("o", lambda x: x, None, observed=obs)
            assert o.observed.shape == (1,1)
            assert o.observed.dtype == dtype
            assert o.observed[0] == obs


class TestNumpyInterfaces():

    def test_simulator_summary_input_dimensions(self):
        np.random.seed(438763)
        for i in range(20):
            # dimensions
            n_samples = np.random.randint(1,5)
            n_in_dims = np.random.randint(1,5)
            in_dims = [np.random.randint(1,5) for i in range(n_in_dims)]
            in_dims[0] = max(2, in_dims[0])
            in_dims = tuple(in_dims)
            n_out_dims = np.random.randint(1,5)
            out_dims = tuple([np.random.randint(1,5) for i in range(n_out_dims)])
            # data
            ret = np.zeros((n_samples, ) + in_dims)
            obs = ret[0]
            # summary
            def mock_summary(x):
                exp_in_dims = in_dims
                if len(exp_in_dims) == 0:
                    exp_in_dims = (1,)
                if x.shape == (n_samples, ) + exp_in_dims:
                    # simulation data
                    return np.zeros((n_samples,) + out_dims)
                elif x.shape == (1,) + exp_in_dims:
                    # observation data
                    return np.zeros((1,) + out_dims)
                assert False
            # model
            mock = MockSimulator(ret)
            si = elfi.Simulator("si", mock, None, observed=obs)
            su = elfi.Summary("su", mock_summary, si)
            res = su.generate(n_samples).compute()
            exp_out_dims = out_dims
            if len(exp_out_dims) == 0:
                exp_out_dims = (1,)
            assert res.shape == (n_samples,) + exp_out_dims

    def test_summary_discrepancy_input_dimensions(self):
        np.random.seed(23876123)
        for i in range(20):
            # dimensions
            n_samples = np.random.randint(1,5)
            n_sum = np.random.randint(1,5)
            n_dims = [np.random.randint(1,5) for i in range(n_sum)]
            dims = [tuple([np.random.randint(1,5) for j in range(n_dims[i])]) for i in range(n_sum)]
            # data
            ret = np.zeros((n_samples, 1))
            obs = ret[0]
            # summary
            def mock_summary(i, x):
                return np.zeros((x.shape[0], ) + dims[i])
            # discrepancy
            def mock_discrepancy(x, y):
                assert len(x) == len(y) == n_sum
                for i in range(n_sum):
                    exp_dims = dims[i]
                    if len(exp_dims) == 0:
                        exp_dims = (1,)
                    assert y[i].shape == (1,) + exp_dims
                    assert x[i].shape == (n_samples,) + exp_dims
                return np.zeros((n_samples, 1))
            # model
            mock = MockSimulator(ret)
            si = elfi.Simulator("si", mock, None, observed=obs)
            su = [elfi.Summary("su{}".format(i), partial(mock_summary, i), si) for i in range(n_sum)]
            di = elfi.Discrepancy("di", mock_discrepancy, *su)
            res = di.generate(n_samples).compute()
            assert res.shape == (n_samples, 1)

