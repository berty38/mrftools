"""BeliefPropagator class."""
try:
    import autograd.numpy as np
    from autograd.numpy.numpy_grads import make_grad_dot
    from autograd.core import primitive
    from autograd.core import getval
except ImportError:
    import numpy as np
    def primitive(func):
        return func

from scipy.misc import logsumexp
from MarkovNet import MarkovNet
from Inference import Inference


class MatrixBeliefPropagator(Inference):
    """Object that can run belief propagation on a MarkovNet."""

    def __init__(self, markov_net, labels):
        """Initialize belief propagator for markov_net."""
        self.mn = markov_net
        self.var_beliefs = dict()
        self.pair_beliefs = dict()
        self.labels = labels
        self.temp = 1

        if not self.mn.matrix_mode:
            self.mn.create_matrices()

        self.previously_initialized = False
        self.initialize_messages()

        self.belief_mat = np.zeros((self.mn.max_states, len(self.mn.variables)))
        self.pair_belief_tensor = np.zeros((self.mn.max_states, self.mn.max_states, self.mn.num_edges))
        self.conditioning_mat = np.zeros((self.mn.max_states, len(self.mn.variables)))
        self.lables_mat = np.zeros((self.mn.max_states, len(self.mn.variables)))
        self.max_iter = 300000
        self.fully_conditioned = False
        self.conditioned = np.zeros(len(self.mn.variables), dtype=bool)

        self.disallow_impossible_states()
        if labels:
            self.build_lables_mat()

    def build_labels_mat(self):
        for var, label in self.labels.items():
            i = self.mn.var_index[var]
            self.lables_mat[label, i] = 1

    def set_max_iter(self, max_iter):
        self.max_iter = max_iter

    def initialize_messages(self):
        self.message_mat = np.zeros((self.mn.max_states, 2 * self.mn.num_edges))
        return self.message_mat

    def condition(self, var, state):
        i = self.mn.var_index[var]
        self.conditioning_mat[:, i] = -np.inf
        self.conditioning_mat[state, i] = 0
        if isinstance(state, int):
            self.conditioned[i] = True

        if np.all(self.conditioned):
            # compute beliefs and set flag to never recompute them
            self.compute_beliefs(self.mn.unary_mat, self.message_mat)
            self.compute_pairwise_beliefs()
            self.fully_conditioned = True

    def disallow_impossible_states(self):
        """ force variables to only allow nonzero probability on their possible states """
        for var, num_states in self.mn.num_states.items():
            self.condition(var, range(num_states))

    def compute_beliefs(self):
        """Compute unary beliefs based on current messages."""
        if not self.fully_conditioned:
            self.belief_mat = self.mn.unary_mat + self.conditioning_mat
            self.belief_mat += sparse_dot(self.message_mat, self.mn.message_to_map)
            #self.belief_mat += self.mn.message_to_map.T.dot(self.message_mat.T).T

            self.belief_mat -= logsumexp(self.belief_mat, 0)

    def compute_pairwise_beliefs(self):
        """Compute pairwise beliefs based on current messages."""
        if not self.fully_conditioned:
            adjusted_message_prod = self.belief_mat[:, self.mn.message_from] \
                                    - np.hstack((self.message_mat[:, self.mn.num_edges:],
                                                               self.message_mat[:, :self.mn.num_edges]))

            to_messages = adjusted_message_prod[:, :self.mn.num_edges].reshape((self.mn.max_states, 1, self.mn.num_edges))
            from_messages = adjusted_message_prod[:, self.mn.num_edges:].reshape((1, self.mn.max_states, self.mn.num_edges))

            beliefs = self.mn.edge_pot_tensor[:, :, self.mn.num_edges:] + to_messages + from_messages

            beliefs -= logsumexp(beliefs, (0, 1))

            self.pair_belief_tensor = beliefs

    def update_messages(self):
        """Update all messages between variables using belief division. Return the change in messages from previous iteration."""
        self.compute_beliefs()

        adjusted_message_prod = self.mn.edge_pot_tensor - np.hstack((self.message_mat[:, self.mn.num_edges:],
                                                                     self.message_mat[:, :self.mn.num_edges]))
        adjusted_message_prod += self.belief_mat[:, self.mn.message_from]

        messages = np.squeeze(logsumexp(adjusted_message_prod, 1))
        messages = np.nan_to_num(messages - messages.max(0))

        change = np.sum(np.abs(messages - self.message_mat))

        self.message_mat = messages

        return change

    def _compute_inconsistency_vector(self):
        expanded_beliefs = np.exp(self.belief_mat[:, self.mn.message_to])

        pairwise_beliefs = np.hstack((np.sum(np.exp(self.pair_belief_tensor), axis = 0),
                                      np.sum(np.exp(self.pair_belief_tensor), axis = 1)))

        return expanded_beliefs - pairwise_beliefs

    def compute_inconsistency(self):
        """Return the total disagreement between each unary belief and its pairwise beliefs."""
        disagreement = np.sum(np.abs(self._compute_inconsistency_vector()))

        return disagreement

    def infer(self, unary_mat, edge_pot_tensor, tolerance = 1e-8, display = 'iter'):
        """Run belief propagation until messages change less than tolerance."""
        change = np.inf
        iteration = 0
        message_mat = self.initialize_messages()
        while change > tolerance and iteration < self.max_iter:
            change, message_mat = self.update_messages(unary_mat, edge_pot_tensor, message_mat)
            if display == "full":
                energy_func = self.compute_energy_functional()
                disagreement = self.compute_inconsistency()
                dual_obj = self.compute_dual_objective()
                if self.temp == 1:
                    # print type(energy_func)
                    # print type(disagreement)
                    # print type(dual_obj)
                    print("Iteration %d, change in messages %f. Calibration disagreement: %f, energy functional: %f, dual obj: %f" % (iteration, change, disagreement, energy_func, dual_obj))
                    self.temp += 1
                else:
                    # energy_func = energy_func.value
                    # print type(dual_obj)
                    # dual_obj = dual_obj.value
                    # print type(dual_obj)
                    # print dual_obj
                    # # change = change.value
                    # # disagreement = disagreement.value
                    # print type(energy_func)
                    # print energy_func
                    # # print type(disagreement)
                    #
                    # # print type(iteration)
                    # print type(change)
                    # print change
                    print(
                    "Iteration %d, change in messages %s. Calibration disagreement: %s, energy functional: %s, dual obj: %s" % (
                    iteration, change, disagreement, energy_func, dual_obj))

            elif display == "iter":
                print("Iteration %d, change in messages %f." % (iteration, change))
            iteration += 1
        if display == 'final' or display == 'full' or display == 'iter':
            print("Belief propagation finished in %d iterations." % iteration)

        return message_mat

    def load_beliefs(self, unary_mat, message_mat):
        self.compute_beliefs(unary_mat, message_mat)
        self.compute_pairwise_beliefs()

        for (var, i) in self.mn.var_index.items():
            self.var_beliefs[var] = self.belief_mat[:len(self.mn.unary_potentials[var]), i]

        for edge, i in self.mn.edge_index.items():
            (var, neighbor) = edge

            belief = self.pair_belief_tensor[:len(self.mn.unary_potentials[var]),
                     :len(self.mn.unary_potentials[neighbor]), i]

            self.pair_beliefs[(var, neighbor)] = belief

            self.pair_beliefs[(neighbor, var)] = belief.T

    def compute_bethe_entropy(self):
        """Compute Bethe entropy from current beliefs. Assume that the beliefs have been computed and are fresh."""
        if self.fully_conditioned:
            entropy = 0
        else:
            entropy = - np.sum(np.nan_to_num(self.pair_belief_tensor) * np.exp(self.pair_belief_tensor)) \
                      - np.sum((1 - self.mn.degrees) * (np.nan_to_num(self.belief_mat) * np.exp(self.belief_mat)))

        return entropy

    def compute_energy(self):
        """Compute the log-linear energy. Assume that the beliefs have been computed and are fresh."""
        energy = np.sum(np.nan_to_num(self.mn.edge_pot_tensor[:, :, self.mn.num_edges:]) * np.exp(self.pair_belief_tensor)) + \
                 np.sum(np.nan_to_num(self.mn.unary_mat) * np.exp(self.belief_mat))
        # print self.belief_mat

        return energy

    def get_feature_expectations(self, unary_mat, message_mat):
        self.compute_beliefs(unary_mat, message_mat)
        self.compute_pairwise_beliefs()

        summed_features = np.dot(self.mn.feature_mat, np.exp(self.belief_mat).T)

        summed_pair_features = np.dot(self.mn.edge_feature_mat, np.exp(self.pair_belief_tensor).reshape(
            (self.mn.max_states**2, self.mn.num_edges)).T)

        marginals = np.append(summed_features.reshape(-1), summed_pair_features.reshape(-1))

        return marginals

    def compute_energy_functional(self):
        """Compute the energy functional."""
        self.compute_beliefs(self.mn.unary_mat, self.message_mat)
        self.compute_pairwise_beliefs()
        return self.compute_energy() + self.compute_bethe_entropy()

    def compute_dual_objective(self):
        """Compute the value of the BP Lagrangian."""
        objective = self.compute_energy_functional() + \
                    np.sum(self.message_mat * self._compute_inconsistency_vector())

        return objective

    def set_messages(self, messages):
        assert(np.all(self.message_mat.shape == messages.shape))
        self.message_mat = messages

@primitive
def logsumexp(matrix, dim = None):
    """Compute log(sum(exp(matrix), dim)) in a numerically stable way."""
    try:
        with np.errstate(over='raise', under='raise'):
            return np.log(np.sum(np.exp(matrix), dim, keepdims=True))

    except:
        max_val = np.nan_to_num(matrix.max(axis=dim, keepdims=True))
        with np.errstate(under='ignore', divide='ignore'):
            return np.log(np.sum(np.exp(matrix - max_val), dim, keepdims=True)) + max_val


def make_grad_logsumexp(ans, matrix, dim):
    def gradient_product(g):
        return np.full(matrix.shape, g) * np.exp(matrix - np.full(matrix.shape, ans))
    return gradient_product

@primitive
def sparse_dot(full_matrix, sparse_matrix):
    return sparse_matrix.T.dot(full_matrix.T).T

def make_grad_sparse_dot(ans, full_matrix, sparse_matrix):
    def gradient_product(g):
        return sparse_matrix.dot(g.T).T
    return gradient_product


try:
    # sparse_dot.defgrad(lambda ans, full_matrix, sparse_matrix : make_grad_dot(0, ans, full_matrix, sparse_matrix.todense()))
    sparse_dot.defgrad(make_grad_sparse_dot)
    logsumexp.defgrad(make_grad_logsumexp)
except AttributeError:
    pass
