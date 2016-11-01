
from MarkovNet import MarkovNet
import numpy as np
from ApproxMaxLikelihood import ApproxMaxLikelihood
from scipy.optimize import minimize, check_grad
import matplotlib.pyplot as plt
import time
from grafting_util import   initialize_priority_queue, update_grafting_metrics, update_mod_grafting_metrics, setup_learner_1, reset_unary_factors, reset_edge_factors, strcutured_priority_mean_gradient_test, new_strcutured_priority_mean_gradient_test, new_strcutured_priority_mean_gradient_test_3
from graph_mining_util import make_graph, select_edge_to_inject
import copy
import operator
from graph_mining_util import draw_graph, make_graph


def new_strcutured_priority_graft( variables, num_states, data, l1_coeff, l2_coeff, var_reg, edge_reg, max_iter_graft, max_num_states, verbose, num_edges, edges, list_order):
    """
    Main Script for priority graft algorithm.
    Reference: To be added.
    """
    # INITIALIZE VARIABLES
    recall, precision = list(), list()
    suff_stats_list = list()
    iterations = list()
    timing = list()
    priority_reassignements, num_injection, num_success, num_edges_reassigned = 0, 0, 0, 0
    graph_edges_reassigned, naive_edges_reassigned, graph_edges_reassigned,edges_reassigned, map_weights_to_variables, map_weights_to_edges, active_set = [], [], [], [], [], [], []
    edge_regularizers, var_regularizers = dict(), dict()
    np.random.seed(0)
    vector_length_per_var = max_num_states
    vector_length_per_edge = max_num_states ** 2
    mn = MarkovNet()
    map_weights_to_variables = mn.initialize_unary_factors(variables, num_states)
    search_space = mn.search_space
    search_space = [ search_space[i] for i in list_order]

    reassignment = len(active_set)+1
    # GET DATA EXPECTATION
    sufficient_stats, padded_sufficient_stats = mn.get_unary_sufficient_stats(data, max_num_states)
    # INITIALIZE PRIORITY QUEUE
    pq = initialize_priority_queue(search_space)
    aml_optimize = setup_learner_1(mn, l1_coeff, l2_coeff, var_reg, edge_reg, padded_sufficient_stats,  len(data), active_set)
    # START GRAFTING
    weights_opt = aml_optimize.learn(np.random.randn(aml_optimize.weight_dim), max_iter_graft, edge_regularizers, var_regularizers)
    ## GRADIENT TEST
    is_activated_edge, activated_edge, curr_edges_reassigned, curr_graph_edges_reassigned, iter_number = new_strcutured_priority_mean_gradient_test_3(aml_optimize.belief_propagators, search_space, pq, data, l1_coeff, reassignment,  sufficient_stats, padded_sufficient_stats, max_num_states)
    if iter_number:
        iterations.append(iter_number)
    if curr_edges_reassigned:
        naive_edges_reassigned.extend(curr_edges_reassigned)
        graph_edges_reassigned.extend(curr_graph_edges_reassigned)
    outer_loop = 0
    t = time.time()
    while is_activated_edge and len(active_set) < num_edges:
        while ((len(pq) > 0) and is_activated_edge) and len(active_set) < num_edges: # Stop if all edges are added or no edge is added at the previous iteration
            # reassignment = len(active_set)+1
            active_set.append(activated_edge)
            if verbose:
                print('ACTIVATED EDGE')
                print(activated_edge)
                print('CURRENT ACTIVE SPACE')
                print(active_set)
            # draw_graph(active_set, variables)
            recall.append(float(len([x for x in active_set if x in edges]))/len(edges))
            precision.append(float(len([x for x in edges if x in active_set]))/len(active_set))
            suff_stats_list.append(100 * (len(sufficient_stats) - len(variables))/(len(variables) ** 2 - len(variables)) / 2)
            timing.append(time.time() - t)
            mn.set_edge_factor(activated_edge, np.zeros((len(mn.unary_potentials[activated_edge[0]]), len(mn.unary_potentials[activated_edge[1]]))))
            t11 = time.time()
            aml_optimize = setup_learner_1(mn, l1_coeff, l2_coeff, var_reg, edge_reg, padded_sufficient_stats, len(data), active_set)
            #OPTIMIZE
            tmp_weights_opt = np.concatenate((weights_opt, np.random.randn(vector_length_per_edge)))
            weights_opt = aml_optimize.learn(tmp_weights_opt, max_iter_graft, edge_regularizers, var_regularizers)
            # print(time.time() - t11) 
            ## GRADIENT TEST
            is_activated_edge, activated_edge, curr_edges_reassigned, curr_graph_edges_reassigned, iter_number = new_strcutured_priority_mean_gradient_test_3(aml_optimize.belief_propagators, search_space, pq, data, l1_coeff, reassignment, sufficient_stats, padded_sufficient_stats, max_num_states)
            if iter_number:
                iterations.append(iter_number)
            if curr_edges_reassigned:
                naive_edges_reassigned.extend(curr_edges_reassigned)
                graph_edges_reassigned.extend(curr_graph_edges_reassigned)

        aml_optimize = setup_learner_1(mn, l1_coeff, l2_coeff, var_reg, edge_reg, padded_sufficient_stats, len(data), active_set)
        weights_opt = aml_optimize.learn(np.zeros(aml_optimize.weight_dim), 2500, edge_regularizers, var_regularizers)
        is_activated_edge, activated_edge, curr_edges_reassigned, curr_graph_edges_reassigned, iter_number = new_strcutured_priority_mean_gradient_test_3(aml_optimize.belief_propagators, search_space, pq, data, l1_coeff, reassignment, sufficient_stats, padded_sufficient_stats, max_num_states)

    recall.append(float(len([x for x in active_set if x in edges]))/len(edges))
    precision.append(float(len([x for x in edges if x in active_set]))/len(active_set))
    suff_stats_list.append(100 * (len(sufficient_stats) - len(variables))/(len(variables) ** 2 - len(variables)) / 2)
    timing.append(time.time() - t)
    # REMOVE NON RELEVANT EDGES
    aml_optimize.belief_propagators[0].mn.update_edge_tensor()
    unary_indices, pairwise_indices = aml_optimize.belief_propagators[0].mn.get_weight_factor_index()

    final_active_set = []
    edge_mean_weights = list()
    for edge in active_set:
        i = aml_optimize.belief_propagators[0].mn.edge_index[edge]
        edge_weights = aml_optimize.belief_propagators[0].mn.edge_pot_tensor[:aml_optimize.belief_propagators[0].mn.num_states[edge[1]], :aml_optimize.belief_propagators[0].mn.num_states[edge[0]], i].flatten()
        edge_mean_weights.append((edge,edge_weights.dot(edge_weights) / len(edge_weights)))
        if edge_weights.dot(edge_weights) / len(edge_weights) > .05:
            final_active_set.append(edge)

    # draw_graph(active_set, variables)

    # print('Cleaned Active set')
    # print(final_active_set)

    # # LEARN FINAL MRF
    # mn_old = mn
    # mn = MarkovNet()
    # reset_unary_factors(mn, mn_old)
    # reset_edge_factors(mn, mn_old, final_active_set)

    # # aml_optimize = setup_learner_1(mn, l1_coeff, l2_coeff, var_reg, edge_reg, padded_sufficient_stats, len(data), final_active_set)
    
    # # for edge in final_active_set:
    # #     i = aml_optimize.belief_propagators[0].mn.edge_index[edge]
    # #     edge_regularizers[edge] = pairwise_indices[:, :, i]
    # # weights_opt = aml_optimize.learn(np.zeros(aml_optimize.weight_dim), 2500, edge_regularizers, var_regularizers)



    learned_mn = aml_optimize.belief_propagators[0].mn
    learned_mn.load_factors_from_matrices()

    print('Naive edge reassignments')
    naive_edges_reassigned = list(set(naive_edges_reassigned))
    print(len(naive_edges_reassigned))
    if naive_edges_reassigned:
        naive_reassignment_success_rate = float(len([x for x in naive_edges_reassigned if x not in active_set])) / float(len(naive_edges_reassigned))
        print('Naive reassignment success rate')
        print(naive_reassignment_success_rate)

    print('Graph edge reassignments')
    graph_edges_reassigned = list(set(graph_edges_reassigned))
    print(len(graph_edges_reassigned))
    if graph_edges_reassigned:
        graph_reassignment_success_rate = float(len([x for x in graph_edges_reassigned if x not in active_set])) / float(len(graph_edges_reassigned))
        print('Graph reassignment success rate')
        print(graph_reassignment_success_rate)
    print('Average Selection iterations')
    print(float(sum(iterations))/len(iterations))

    # plt.plot(range(1,len(iterations) + 1, 1), iterations)
    # plt.savefig('Iter_number/Structured_' + str(len(variables)) +'Nodes_MRF.png') 
    # plt.close()

    # plt.plot(suff_stats_list, recall)
    # plt.savefig('Recall_Precision/Structured_recall_' + str(len(variables)) +'Nodes_MRF.png') 
    # plt.close()

    # plt.plot(suff_stats_list, precision)
    # plt.savefig('Recall_Precision/Structured_precision_' + str(len(variables)) +'Nodes_MRF.png') 
    # plt.close()

    print('SUFFICIENT STATS')
    print(len(sufficient_stats)- len(variables))
    # print('outer_loop')
    # print(outer_loop)

    print(iterations)

    return learned_mn, final_active_set, suff_stats_list, recall, precision, timing
