import unittest
from MatrixBeliefPropagator import MatrixBeliefPropagator
from Learner import Learner
import numpy as np
from LogLinearModel import LogLinearModel
from EM import EM
from PairedDual import PairedDual
from scipy.optimize import check_grad, approx_fprime
import matplotlib.pyplot as plt

class TestLearner(unittest.TestCase):

    def set_up_learner(self, learner):
        d = 2
        num_states = 4

        np.random.seed(0)

        labels = [{0: 2,       2: 1},
                  {      1: 2, 2: 0},
                  {0: 2, 1: 3,     },
                  {0: 0, 1: 2, 2: 3}]

        models = []
        for i in range(len(labels)):
            m = self.create_random_model(num_states, d)
            models.append(m)

        for model, states in zip(models, labels):
            learner.add_data(states, model)

    def test_gradient(self):
        weights = np.zeros(24)
        learner = Learner(MatrixBeliefPropagator)
        self.set_up_learner(learner)
        learner.set_regularization(0.0, 1.0)
        gradient_error = check_grad(learner.subgrad_obj, learner.subgrad_grad, weights)

        # numerical_grad = approx_fprime(weights, learner.subgrad_obj, 1e-4)
        # analytical_grad = learner.subgrad_grad(weights)
        # plt.plot(numerical_grad, 'r')
        # plt.plot(analytical_grad, 'b')
        # plt.show()

        print("Gradient error: %f" % gradient_error)
        assert gradient_error < 1e-1, "Gradient is wrong"

    def test_m_step_gradient(self):
        weights = np.zeros(24)
        learner = EM(MatrixBeliefPropagator)
        self.set_up_learner(learner)
        learner.set_regularization(0.0, 1.0)
        learner.e_step(weights)
        gradient_error = check_grad(learner.objective, learner.gradient, weights)

        # numerical_grad = approx_fprime(weights, learner.objective, 1e-4)
        # analytical_grad = learner.gradient(weights)
        # plt.plot(numerical_grad, 'r')
        # plt.plot(analytical_grad, 'b')
        # plt.show()

        print("Gradient error: %f" % gradient_error)
        assert gradient_error < 1e-1, "Gradient is wrong"

    def test_learner(self):
        weights = np.zeros(24)
        learner = Learner(MatrixBeliefPropagator)
        self.set_up_learner(learner)

        learner.learn(weights)
        weight_record = learner.weight_record
        time_record = learner.time_record
        l = weight_record.shape[0]
        t = learner.time_record[0]
        old_obj = np.Inf
        for i in range(l):
            new_obj = learner.subgrad_obj(learner.weight_record[i,:])
            assert (new_obj <= old_obj), "subgradient objective is not decreasing"
            old_obj = new_obj

            assert new_obj >= 0, "Learner objective was not non-negative"

    def test_EM(self):
        weights = np.zeros(24)
        learner = EM(MatrixBeliefPropagator)
        self.set_up_learner(learner)

        learner.learn(weights)
        weight_record = learner.weight_record
        time_record = learner.time_record
        l = weight_record.shape[0]
        t = learner.time_record[0]
        old_obj = learner.subgrad_obj(learner.weight_record[0,:])
        new_obj = learner.subgrad_obj(learner.weight_record[-1,:])
        assert (new_obj <= old_obj), "EM objective did not decrease"

        for i in range(l):
            new_obj = learner.subgrad_obj(learner.weight_record[i, :])
            assert new_obj >= 0, "EM objective was not non-negative"

    def test_paired_dual(self):
        weights = np.zeros(24)
        learner = PairedDual(MatrixBeliefPropagator)
        self.set_up_learner(learner)

        learner.learn(weights)
        weight_record = learner.weight_record
        time_record = learner.time_record
        l = weight_record.shape[0]
        t = learner.time_record[0]

        old_obj = learner.subgrad_obj(learner.weight_record[0,:])
        new_obj = learner.subgrad_obj(learner.weight_record[-1,:])
        assert (new_obj <= old_obj), "paired dual objective did not decrease"

        for i in range(l):
            new_obj = learner.subgrad_obj(learner.weight_record[i, :])
            assert new_obj >= 0, "Paired dual objective was not non-negative"

    def create_random_model(self, num_states, d):
        model = LogLinearModel()

        model.declare_variable(0, num_states)
        model.declare_variable(1, num_states)
        model.declare_variable(2, num_states)

        model.set_unary_weights(0, np.random.randn(num_states, d))
        model.set_unary_weights(1, np.random.randn(num_states, d))
        model.set_unary_weights(2, np.random.randn(num_states, d))

        model.set_unary_features(0, np.random.randn(d))
        model.set_unary_features(1, np.random.randn(d))
        model.set_unary_features(2, np.random.randn(d))

        model.set_all_unary_factors()

        model.set_edge_factor((0, 1), np.zeros((num_states, num_states)))
        model.set_edge_factor((1, 2), np.zeros((num_states, num_states)))

        return model

