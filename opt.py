import numpy as np

def sgd(func, grad, x, args, callback):
    t = 1
    tolerance = 1e-8
    change = np.inf

    max_iter = 200

    while change > tolerance and t < max_iter:
        old_x = x
        g = grad(x, args)
        x = x - 0.1 * g / t
        change = np.sum(np.abs(x - old_x))
        t += 1
        callback(x)

    return x

def adagrad(func, grad, x, args, callback):
    t = 1
    tolerance = 1e-8
    max_iter = 500
    change = np.inf

    grad_sum = 0

    while change > tolerance and t < max_iter:
        old_x = x
        if args:
            g = grad(x, args)
        else:
            g = grad(x)
        grad_sum += g * g
        x = x - 1.0 * g / (np.sqrt(grad_sum) + 0.001)
        change = np.sum(np.abs(x - old_x))
        t += 1
        callback(x)
        # print func(x, args)
        # print change


    return x


import matplotlib.pyplot as plt
import time

class ObjectivePlotter(object):

    def __init__(self, func):
        self.objectives = []
        self.func = func
        plt.figure()
        self.timer = time.time()
        self.interval = 0.5

    def callback(self, x):
        self.objectives.append(self.func(x))

        elapsed_time = time.time() - self.timer

        if elapsed_time > self.interval:

            plt.clf()

            plt.subplot(211)

            plt.plot(self.objectives)

            plt.subplot(223)
            unary = plt.imshow(np.reshape(x[0:21 * 2], (21, 2)).T, interpolation='nearest', cmap=plt.get_cmap('gray'))
            plt.colorbar(unary)

            plt.subplot(224)
            pair = plt.imshow(np.reshape(x[21 * 2:], (2, 2)), interpolation='nearest', cmap=plt.get_cmap('gray'))
            plt.colorbar(pair)


            plt.pause(1e-16)

            self.timer = time.time()
