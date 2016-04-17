#
# Use Bayesian parameter estimation to figure out what the thermal looks like
#

import numpy as np
import pymc3 as pm
import scipy as sp
import theano
import theano.tensor as t
from scipy.stats import kde

import matplotlib.pyplot as plt
import matplotlib.cm as cm

from data import boundsFromPath

# For reproducibility
#random.seed(126)
#np.random.seed(123)

# Vertical velocity as function of the thermal's position and width
def deterministicVelocity(path, measurements,
                          thermal_position_x, thermal_position_y,
                          thermal_amplitude, thermal_sd):
    # Fix "Cannot compute test value" error, see: http://stackoverflow.com/a/30241668
    #theano.config.compute_test_value = 'ignore'

    # Create the function but already plug in some values we want to test with
    # See: https://www.quora.com/What-is-the-meaning-and-benefit-of-shared-variables-in-Theano
    x = theano.shared(np.array([x for x,y in path]))
    y = theano.shared(np.array([y for x,y in path]))

    # These functions now refer to the shared variables
    # Do not compile here, see: http://stackoverflow.com/q/30426216
    def gaussianTheano(xo, yo, amplitude, sigma_x, sigma_y):
        #xo = float(xo)
        #yo = float(yo)
        theta = offset = 0 # for now
        a = (pm.cos(theta)**2)/(2*sigma_x**2) + (pm.sin(theta)**2)/(2*sigma_y**2)
        b = -(pm.sin(2*theta))/(4*sigma_x**2) + (pm.sin(2*theta))/(4*sigma_y**2)
        c = (pm.sin(theta)**2)/(2*sigma_x**2) + (pm.cos(theta)**2)/(2*sigma_y**2)
        gauss = offset+amplitude*pm.exp(-1*(a*((x-xo)**2)+2*b*(x-xo)*(y-yo)+c*((y-yo)**2)))
        return gauss

    # Return the Theano function that we'll use when sampling
    return gaussianTheano(thermal_position_x, thermal_position_y,
                          thermal_amplitude, thermal_sd, thermal_sd)

# Zero offset, rotation, and same sigma in both x and y
def thermalEq(position, amplitude, sd):
    return gaussian(position[0], position[1], amplitude, sd, sd, 0, 0)

# See: http://stackoverflow.com/q/25342899
def gaussian(xo, yo, amplitude, sigma_x, sigma_y, theta, offset):
    xo = float(xo)
    yo = float(yo)
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)
    gauss = lambda x,y: offset+amplitude*np.exp(-1*(a*((x-xo)**2)+2*b*(x-xo)*(y-yo)+c*((y-yo)**2)))
    return gauss

# Take single measurement
#
# If desired, also add some Gaussian noise with mean zero and a standard
# deviation of the specified value
def takeMeasurement(field, position, noise=0.05):
    noise_value = 0
    measurement = 0

    for thermal in field:
        measurement += thermal(position[0], position[1])

    if noise:
        noise_value = np.random.normal(0, noise)

    return measurement + noise_value

# Take measurements at the points along the path
# Input: field=[eq1, eq2, ...], path=[(x1,y1),(x2,y2),...]
# Output: [v1, v2, ...]
def takeMeasurements(field, path, noise=0.05):
    measurements = np.empty(len(path))

    for i, pos in enumerate(path):
        measurements[i] = takeMeasurement(field, pos, noise)

    return measurements

#
# Create the visualization of the 3D thermal field, our path,
# and where we think the thermals are
#
def visualizeThermalField(field, path, measurements, trace, pos_min, pos_max,
                          legend=False, only2d=False, center=None,
                          fig=None, subplot=111, lines=True,
                          limits=None):
    if not fig:
        fig = plt.figure(figsize=(15,8))

    if only2d:
        ax = fig.add_subplot(subplot)
    else:
        ax = fig.add_subplot(subplot, projection='3d')

    plt.title('Bayesian')
    ax.set_xlabel('$x$')
    ax.set_ylabel('$y$')

    if not only2d:
        ax.set_zlabel('$f(x,y)$')

    # The learned values, first so they're displayed on the bottom
    ax.scatter(trace["thermal_position_x"], trace["thermal_position_y"],
                np.ones(len(trace["thermal_position_x"]))*ax.get_zlim()[0],
                alpha=0.05, c="r")

    # Compute bounds based on measurements
    pos_min_x, pos_max_x, pos_min_y, pos_max_y = boundsFromPath(path)

    # Evaluate thermal field equations over X,Y
    # See: http://matplotlib.org/examples/mplot3d/surface3d_demo.html
    X = np.arange(pos_min_x, pos_max_x, (pos_max_x-pos_min_x)/40)
    Y = np.arange(pos_min_y, pos_max_y, (pos_max_y-pos_min_y)/40)
    X, Y = np.meshgrid(X, Y)
    Z = np.zeros((len(X),len(Y)))

    for thermal in field:
        Z += thermal(X, Y)

    if not only2d:
        surf = ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=cm.coolwarm,
                           alpha=0.5, linewidth=0, antialiased=True)

        #fig.colorbar(surf, aspect=10, shrink=0.3)

    # Contours so we can see how it compares with the path
    # See: http://matplotlib.org/examples/mplot3d/contour3d_demo3.html
    try:
        cset = ax.contour(X, Y, Z, zdir='z', offset=ax.get_zlim()[0], cmap=cm.coolwarm)
    except ValueError:
        # Fixing the issue might be preferred, but really we don't care if we don't
        # plot the contour. But, if we can, it's nice.
        pass

    #cset = ax.contour(X, Y, Z, zdir='x', offset=pos_min, cmap=cm.coolwarm)
    #cset = ax.contour(X, Y, Z, zdir='y', offset=pos_max, cmap=cm.coolwarm)

    # Plot the path
    # See: http://matplotlib.org/examples/mplot3d/lines3d_demo.html
    #ax.plot(X, Y, Z)

    # Plot the path as line segments
    # See: http://stackoverflow.com/a/11541628
    if lines:
        for i in range(1, len(path)):
            if only2d:
                ax.plot([path[i-1][0], path[i][0]], [path[i-1][1],path[i][1]],
                    label='Path Segment #'+str(i))
            else:
                ax.plot([path[i-1][0], path[i][0]], [path[i-1][1],path[i][1]],
                        zs=[0,0], label='Path Segment #'+str(i))

    # Otherwise, just plot the observed points
    #else:
    #    ax.scatter(path[:,0], path[:,1], measurements,
    #                c='r', marker='.', s=20, label='Observed')

    # Put legend outside the graph
    # See: http://stackoverflow.com/a/4701285
    if legend:
        # Shrink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Display where we think the center is
    if center:
        ax.plot([center[0]], [center[1]], 'sb', markersize=10)
        # From: http://stackoverflow.com/a/5147430
        #plt.annotate("Center", xy=center, xytext=(-20, 20),
        #             textcoords='offset points', ha='right', va='bottom',
        #             bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
        #             arrowprops=dict(arrowstyle = '->', connectionstyle = 'arc3,rad=0'))

    if limits:
        ax.set_xlim(limits[0])
        ax.set_ylim(limits[1])

        if not only2d:
            ax.set_zlim(limits[2])

# Compute the Maximum a posteriori estimation via how PyMC3 outputs the
# distribution via in traceplot. Probably not the best way, but it will
# find the peak that is displayed on that plot.
#
# See: https://github.com/pymc-devs/pymc3/blob/master/pymc3/plots.py
def lameMAP(data):
    density = kde.gaussian_kde(data)
    l = np.min(data)
    u = np.max(data)
    x = np.linspace(0, 1, 200) * (u - l) + l
    values = density(x)
    return x[np.argmax(values)]

#
# Use PyMC3 to determine the posterior distributions for where we believe
# a Gaussian-shaped thermal is located
#
def BayesianLearning(fig, path, measurements,
                     pos_min=-50, pos_max=50, subplot=133):
    with pm.Model() as model:
        # Compute bounds based on measurements
        pos_min_x, pos_max_x, pos_min_y, pos_max_y = boundsFromPath(path)
        minPos = min(pos_min_x, pos_min_y)
        maxPos = max(pos_max_x, pos_max_y)

        # Priors
        # See: http://stackoverflow.com/q/25342899
        thermal_position_x = pm.Uniform('thermal_position_x',
                                      lower=pos_min_x, upper=pos_max_x)
        thermal_position_y = pm.Uniform('thermal_position_y',
                                      lower=pos_min_y, upper=pos_max_y)
        thermal_amplitude = pm.Uniform('thermal_amplitude',
                                       lower=-10, upper=10)
        thermal_sd = pm.Uniform('sd', lower=0.1, upper=100)

        # When sampling, look at the values of the test thermal field at the points
        # we have taken measurements at.
        velocity = deterministicVelocity(path, measurements,
                                         thermal_position_x, thermal_position_y,
                                         thermal_amplitude, thermal_sd)

        # Observe the vertical velocities
        thermal_vert_vel = pm.Normal('thermal_vert_vel', mu=velocity,
                                     observed=measurements)

        # Sample this to find the posterior, note Metropolis works with discrete
        step = pm.Metropolis()
        start = pm.find_MAP(fmin=sp.optimize.fmin_powell)
        trace = pm.sample(2000, step=step, progressbar=True, start=start)

        # Find the most probable surface and plot that for comparison
        x = lameMAP(trace['thermal_position_x'])
        y = lameMAP(trace['thermal_position_y'])
        amp = lameMAP(trace['thermal_amplitude'])
        sd = lameMAP(trace['sd'])
        eq = thermalEq((x,y), amp, sd)

        # Plot it
        prev = plt.gca()
        visualizeThermalField([eq], path, measurements, trace, pos_min, pos_max,
                              only2d=False, fig=fig, subplot=subplot, lines=False,
                              limits=[prev.get_xlim(),prev.get_ylim(),prev.get_zlim()])

        # Really, we have more information than just this MAP estimate.
        # We have probability distributions over all the parameters.
        # It's hard to visualize this in one figure that we can directly
        # compare with the GPR though.
        pm.traceplot(trace, ['thermal_position_x','thermal_position_y',
                             'thermal_amplitude','sd'])
        #visualizeThermalField(thermals, path, trace, -50, 50, only2d=False)
        #visualizeThermalField(thermals, path, trace, -50, 50, only2d=True)
