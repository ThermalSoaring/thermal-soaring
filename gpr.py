#
# Use GPR to figure out what the thermal looks like
#

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.gaussian_process import GaussianProcess

from data import boundsFromPath

# Make the plots look prettier
import seaborn as sns
sns.set(style="ticks")

#
# Compute mean-squared error (MSE)
#
def evalMSE(predicted, correct):
    p = predicted.flatten()
    c = correct.flatten()
    n = len(p)
    assert len(p)==len(c)
    return 1.0/n*sum(np.square(p-c))

# Comments from documentation:
# http://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.GaussianProcess.html
class GPRParams:
    def __init__(self, theta0=1e-1, thetaL=None, thetaU=None,
                 nugget=None, random_start=1):
        # Since thetaL and thetaU are specified, theta0 is the starting point
        # for the maximum likelihood estimation of the best set of parameters
        #
        # Default assumes isotropic autocorrelation model with theta0 = 1e-1
        self.theta0 = theta0

        # Lower bound on the autocorrelation parameters for maximum likelihood
        # estimation
        #
        # Default is None, so that it skips maximum likelihood estimation and
        # it uses theta0
        self.thetaL = thetaL

        # Upper bound on the autocorrelation parameters for maximum likelihood
        # estimation
        #
        # Default is None, so that it skips maximum likelihood estimation and
        # it uses theta0
        self.thetaU = thetaU

        # Introduce a nugget effect to allow smooth predictions from noisy data.
        # If nugget is an ndarray, it must be the same length as the number of
        # data points used for the fit. The nugget is added to the diagonal of
        # the assumed training covariance
        #
        # Default assumes a nugget close to machine precision for the sake of
        # robustness (nugget = 10. * MACHINE_EPSILON)
        self.nugget = nugget

        # The number of times the Maximum Likelihood Estimation should be performed
        # from a random starting point
        #
        # Default does not use random starting point (random_start = 1)
        self.random_start = random_start

    # For debugging, when printing
    def __str__(self):
        return "Theta0: %f, ThetaL: %f, ThetaU: %f, Nugget: %f, RandomStart: %d" % (
            self.theta0, self.thetaL, self.thetaU, self.nugget, self.random_start)

#
# Gaussian Process Regression to learn thermals
#
# Extent - predict over bounding box of measurements given but extend this
#     bounding box this much in each direction
# Points - how much to divide each axis of the bounding box into, predicting
#     at each of these points
#
def GPR(path, measurements, gprParams, extent=50, points=200):
    # Compute bounds based on measurements
    pos_min_x, pos_max_x, pos_min_y, pos_max_y = boundsFromPath(path)

    # Extend the prediction out from the measurements given
    pos_min_x -= extent
    pos_max_x += extent
    pos_min_y -= extent
    pos_max_y += extent

    # Generate all the points we want to output at
    # See: http://stackoverflow.com/a/32208788
    grid_x, grid_y = np.meshgrid(
        np.arange(pos_min_x, pos_max_x, (pos_max_x-pos_min_x)/points),
        np.arange(pos_min_y, pos_max_y, (pos_max_y-pos_min_y)/points))
    grid = np.vstack((grid_x.flatten(), grid_y.flatten())).T

    gp = GaussianProcess(corr='squared_exponential',
                         theta0=gprParams.theta0,
                         thetaL=gprParams.thetaL,
                         thetaU=gprParams.thetaU,
                         nugget=gprParams.nugget,
                         random_start=gprParams.random_start)

    # Regression, fit to data using Maximum Likelihood Estimation of the parameters
    gp.fit(path, measurements)

    # Prediction over our grid
    prediction, MSE = gp.predict(grid, eval_MSE=True)
    sigma = np.sqrt(MSE)

    return (grid, grid_x, grid_y), prediction, sigma

#
# Take GPR results and find the thermal
#
def GPRtoThermal(grid, prediction, sigma):
    # Find the highest point in the grid
    index = np.argmax(prediction)
    x = grid[index][0]
    y = grid[index][1]

    return x, y, prediction[index], sigma[index]

#
# Get thermal from GPR without plotting
#
def ThermalGPR(path, measurements, gprParams):
    # Run GPR
    (grid, grid_x, grid_y), prediction, sigma = GPR(path, measurements,
            gprParams)

    # Get thermal
    return GPRtoThermal(grid, prediction, sigma)

#
# Get thermal from GPR with plotting
#
def ThermalGPRPlot(fig, path, measurements, gprParams,
        field=None):

    (grid, grid_x, grid_y), prediction, sigma = GPR(path, measurements,
            gprParams)

    if field:
        Z = np.zeros(grid.shape)

        for thermal in field:
            Z += thermal(grid[:,0], grid[:,1])

    # Plot the predicted values
    plt.suptitle("GPR vs. Bayesian with "+str(len(measurements))+" points")

    if field:
        ax = fig.add_subplot(1,3,2, projection='3d')
    else:
        ax = fig.add_subplot(1,2,1, projection='3d')
    plt.title('GPR')
    ax.set_xlabel('$x$')
    ax.set_ylabel('$y$')
    ax.set_zlabel('$f(x,y)$')

    # Reshape from 1D to 2D so we can plot these
    pred_surface = prediction.reshape(grid_x.shape)
    sigma_surface = sigma.reshape(grid_x.shape)

    # The mean
    ax.plot_surface(grid_x, grid_y, pred_surface, label='Prediction',
                    rstride=1, cstride=1, cmap=cm.jet,
                    alpha=0.5, linewidth=0, antialiased=True)

    # 95% Confidence Interval
    lower = np.add(pred_surface, -1.9600*sigma_surface)
    upper = np.add(pred_surface, 1.9600*sigma_surface)

    ax.plot_surface(grid_x, grid_y, lower,
                    label='Lower 95% Confidence Interval',
                    rstride=1, cstride=1, cmap=cm.bone,
                    alpha=0.25, linewidth=0, antialiased=True)
    ax.plot_surface(grid_x, grid_y, upper,
                    label='Upper 95% Confidence Interval',
                    rstride=1, cstride=1, cmap=cm.coolwarm,
                    alpha=0.25, linewidth=0, antialiased=True)

    # Contours so we can see how it compares with the path
    # See: http://matplotlib.org/examples/mplot3d/contour3d_demo3.html
    cset = ax.contour(grid_x, grid_y, pred_surface, zdir='z', offset=ax.get_zlim()[0], cmap=cm.coolwarm)
    cset = ax.contour(grid_x, grid_y, lower, zdir='x', offset=ax.get_xlim()[0], cmap=cm.bone)
    cset = ax.contour(grid_x, grid_y, lower, zdir='y', offset=ax.get_ylim()[1], cmap=cm.bone)
    cset = ax.contour(grid_x, grid_y, pred_surface, zdir='x', offset=ax.get_xlim()[0], cmap=cm.jet)
    cset = ax.contour(grid_x, grid_y, pred_surface, zdir='y', offset=ax.get_ylim()[1], cmap=cm.jet)
    cset = ax.contour(grid_x, grid_y, upper, zdir='x', offset=ax.get_xlim()[0], cmap=cm.coolwarm)
    cset = ax.contour(grid_x, grid_y, upper, zdir='y', offset=ax.get_ylim()[1], cmap=cm.coolwarm)

    # Now for the actual values
    if field:
        ax2 = fig.add_subplot(1,3,1, projection='3d')
        plt.title('Actual')
        ax2.set_xlabel('$x$')
        ax2.set_ylabel('$y$')
        ax2.set_zlabel('$f(x,y)$')

        ax2.plot_surface(grid_x, grid_y, Z, rstride=1, cstride=1, cmap=cm.coolwarm,
                        alpha=0.5, linewidth=0, antialiased=True)

        # Plot the observed measurements
        ax2.scatter(path[:,0], path[:,1], measurements, c='r', marker='.', s=20, label='Observed')

        # Use the same scale
        ax2.set_xlim(ax.get_xlim())
        ax2.set_ylim(ax.get_ylim())
        ax2.set_zlim(ax.get_zlim())
    else:
        # Plot the observed measurements on the plot we did create, on the bottom of the plot
        ax.scatter(path[:,0], path[:,1], np.ones(len(measurements))*ax.get_zlim()[0],
                   c='r', marker='.', s=20, label='Observed')

    # Label the thermal on the plot
    x, y, prediction, uncertainty = GPRtoThermal(grid, prediction, sigma)
    ax.scatter([x], [y], [prediction], c='b', marker='.', s=2000, label='Max')

    return x, y, prediction, uncertainty
