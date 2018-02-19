"""Optimization utility class containing various optimizers and utility objects for callback functions"""
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import save_load_weights
import os.path as osp
import numpy as np
from scipy.optimize import minimize


def sgd(func, grad, x, output_dir, args={}, callback=None):
    """
    Stochastic gradient descent with a linear rate decay
    :param func: function to be minimized (used here only to update the gradient)
    :param grad: gradient function that returns the gradient of the function to be minimized
    :param x: vector initial value of value being optimized over
    :param args: arguments with optimizer options and for the func and grad functions
    :param callback: function to be called with the current iterate each iteration
    :return: optimized solution
    """
    t = 0
    if not args:
        args = {}
    tolerance = args.get('tolerance', 1e-6)
    max_iter = args.get('max_iter', 10000)
    change = np.inf

    while change > tolerance and t < max_iter:
        old_x = x
        print "iteration: %d"%t
        g = grad(x, args)
        #lr = pow(t, -0.5)
        lr = 0.5
        x = x - lr * g
        #x = x - 0.5 * g / t
        change = np.sum(np.abs(x - old_x))
        # if t % 100 == 0:
        #     path = osp.join(output_dir, "weights_%d.txt"%t)
        #     save_load_weights.save_weights(x, path)
        #     ob_path = osp.join(output_dir, "objective.txt")
        #     with open(ob_path, "a") as f:
        #         f.write(str(func(x, args)))
        #         f.write("\n")

        if callback:
            callback(x, output_dir)
        t += 1

    return x


def ada_grad(func, grad, x, output_dir, args={}, callback=None):
    """
    Adagrad adaptive gradient optimizer
    
    :param func: function to be minimized (used here only to update the gradient)
    :param grad: gradient function that returns the gradient of the function to be minimized
    :param x: vector initial value of value being optimized over
    :param args: arguments with optimizer options and for the func and grad functions
    :param callback: function to be called with the current iterate each iteration
    :return: optimized solution
    """

    t = 1
    if not args:
        args = {}
    x_tol = args.get('x_tol', 1e-6)
    g_tol = args.get('g_tol', 0.01)
    eta = args.get('eta', 0.1)
    offset = args.get('offset', 1.0)
    max_iter = args.get('max_iter', 2000)

    grad_norm = np.inf
    x_change = np.inf

    grad_sum = 0
    while grad_norm > g_tol and x_change > x_tol and t < max_iter:
    #while t < max_iter:
        #print "iteration: %d"%t
        if callback:
            callback(x)
        func(x, args)
        g = grad(x, args)
        grad_sum += g * g
        change = eta * g / (np.sqrt(grad_sum) + offset)
        x = x - change

        grad_norm = np.sqrt(g.dot(g))
        x_change = np.sqrt(change.dot(change))

        # grad_norm = np.sqrt(g.dot(g))

        t += 1
    print "end at iteration %d"%t

    if callback:
        callback(x)
    return x


def rms_prop(func, grad, x, args={}, callback=None):
    """
    RMSProp adaptive gradient optimizer
    
    :param func: function to be minimized (used here only to update the gradient)
    :param grad: gradient function that returns the gradient of the function to be minimized
    :param x: vector initial value of value being optimized over
    :param args: arguments with optimizer options and for the func and grad functions
    :param callback: function to be called with the current iterate each iteration
    :return: optimized solution
    """

    t = 1

    if not args:
        args = {}
    x_tol = args.get('x_tol', 0.02)
    g_tol = args.get('g_tol', 1e-6)
    eta = args.get('eta', 0.1)
    gamma = args.get('gamma', 0.1)
    eps = args.get('eps', 1e-8)
    max_iter = args.get('max_iter', 10000)

    grad_norm = np.inf
    x_change = np.inf

    avg_sq_grad = np.zeros(len(x))
    grad_sum = 0
    while grad_norm > g_tol and x_change > x_tol and t < max_iter:
        if callback:
            callback(x)
        func(x, args)
        g = grad(x, args)

        avg_sq_grad = avg_sq_grad * gamma + g ** 2 * (1 - gamma)
        change = eta * g / (np.sqrt(avg_sq_grad) + eps)
        x = x - change

        grad_norm = np.sqrt(g.dot(g))
        x_change = np.sqrt(change.dot(change))
        # grad_norm = np.sqrt(g.dot(g))

        t += 1

    if callback:
        callback(x)
    return x


def adam(func, grad, x, args={}, callback=None):
    """
    Adam adaptive gradient optimizer
    :param func: function to be minimized (used here only to update the gradient)
    :param grad: gradient function that returns the gradient of the function to be minimized
    :param x: vector initial value of value being optimized over
    :param args: arguments with optimizer options and for the func and grad functions
    :param callback: function to be called with the current iterate each iteration
    :return: optimized solution
    """

    t = 1
    if not args:
        args = {}
    x_tol = args.get('x_tol', 1e-3)
    g_tol = args.get('g_tol', 1e-3)
    eps = args.get('eps', 1e-8)
    b1 = args.get('b1', 0.9)
    b2 = args.get('b2', 0.999)
    step_size = args.get('step_size', 0.01)
    max_iter = args.get('max_iter', 1000)

    grad_norm = np.inf
    x_change = np.inf

    m = np.zeros(len(x))
    v = np.zeros(len(x))

    while grad_norm > g_tol and x_change > x_tol and t < max_iter:
        if callback:
            callback(x)
        func(x, args)
        g = grad(x, args)

        m = (1 - b1) * g + b1 * m
        v = (1 - b2) * (g ** 2) + b2 * v
        m_hat = m / (1 - b1 ** (t + 1))
        v_hat = v / (1 - b2 ** (t + 1))
        change = step_size * m_hat / (np.sqrt(v_hat) + eps)
        x = x - change

        grad_norm = np.sqrt(g.dot(g))
        x_change = np.sqrt(change.dot(change))

        t += 1
    if callback:
        callback(x)
    return x


def lbfgs(func, grad, x, args={}, callback=None):
    """
    Adapter for scipy's standard minimize function, which defaults to using the LBFGS-B optimizer
    
    :param func: function to be minimized (used here only to update the gradient)
    :param grad: gradient function that returns the gradient of the function to be minimized
    :param x: vector initial value of value being optimized over
    :param args: arguments with optimizer options and for the func and grad functions
    :param callback: function to be called with the current iterate each iteration
    :return: optimized solution
    """
    if callback:
        res = minimize(fun=func, x0=x, args=args, jac=grad, callback=callback)
    else:
        res = minimize(fun=func, x0=x, args=args, jac=grad)
    return res.x


class WeightRecord(object):
    """
    Class used to store solutions during optimization. Used to generate a callback function that will store the 
    solution passed in. Useful for diagnostics, but in production, usually suboptimal solutions don't need to be saved.
    """
    def __init__(self):
        self.weight_record = np.array([])
        self.time_record = np.array([])

    def callback(self, x):
        """
        Save x into the WeightRecord with a timestamp
        
        :param x: vector to be saved into the weight record
        :return: 
        """
        a = np.copy(x)
        if self.weight_record.size == 0:
            self.weight_record = a.reshape((1, a.size))
            self.time_record = np.array([time.time()])
        else:
            self.weight_record = np.vstack((self.weight_record, a))
            self.time_record = np.vstack((self.time_record, time.time()))


class ObjectivePlotter(object):
    """
    Class to generate a plot of the objective function during the callback
    """
    def __init__(self, func, grad=None):
        """
        Initializes the plotter with the function and gradient
        :param func: function being optimized
        :param grad: gradient of function
        """
        self.objectives = []
        self.func = func
        # plt.switch_backend("MacOSX")
        self.timer = time.time()
        self.interval = 2.0
        self.last_x = 0
        self.grad = grad
        self.t = 0
        self.iters = []
        self.time = []
        self.starttime = time.clock()

        if self.grad:
            print("Iter\tf(x)\t\t\tnorm(g)\t\t\tdx")

    def callback(self, x, output_dir):
        """
        Plot the current objectvie value and the current solution, and prints diagnostic information about
        the current solution, objective, and gradient, when available.
        :param x: current iterate
        :return: 
        """
        elapsed_time = time.time() - self.timer

        objective_value = None
        running_time = None


        if ((0 < self.t < 10) or self.t % 10 == 0):
            objective_value = self.func(x)
            if self.t < 1:
                self.starttime = time.clock()
            running_time = time.clock() - self.starttime
            weight_path = osp.join(output_dir, "weights_%d.txt"%self.t)
            save_load_weights.save_weights(x, weight_path)
            with open(osp.join(output_dir, "time.txt"), "a") as f_t:
                f_t.write(str(self.t) + "\t")
                f_t.write(str(running_time))
                f_t.write("\n")
            with open(osp.join(output_dir, "objective.txt"), "a") as f_o:
                f_o.write(str(objective_value))
                f_o.write("\n")


        if elapsed_time > self.interval or 0 < self.t < 10:
            if objective_value == None:
                objective_value = self.func(x)
                running_time = time.clock() - self.starttime

            self.objectives.append(objective_value)
            self.iters.append(self.t)
            self.time.append(running_time)

            plt.clf()

            plt.subplot(131)
            #plt.plot(self.iters, self.objectives)
            plt.plot(self.time, self.objectives)
            plt.ylabel('Objective')
            #plt.xlabel('Iteration')
            plt.xlabel("time")
            plt.title(self.objectives[-1])

            plt.subplot(132)
            plt.plot(self.iters[-50:], self.objectives[-50:])
            plt.ylabel('Objective')
            plt.xlabel('Iteration')
            plt.title("Zoom")

            plt.subplot(133)
            plt.plot(x)
            plt.title('Current solution')

            # print out diagnostic info
            if self.grad:
                g = self.grad(x)
                diff = x - self.last_x
                print("%d\t%e\t%e\t%e" % (
                    self.iters[-1], self.objectives[-1], np.sqrt(g.dot(g)), np.sqrt(diff.dot(diff))))

            plt.pause(1.0 / 120.0)

            self.timer = time.time()

        self.last_x = x
        self.t += 1



