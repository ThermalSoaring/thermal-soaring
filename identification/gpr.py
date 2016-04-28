#
# Use GPR to figure out what the thermal looks like
#

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.gaussian_process import GaussianProcess

from identification.data import boundsFromPath

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
# Custom correlation model
#
# Based on scikit-learn's squared exponential function:
#  /usr/lib/python3.5/site-packages/sklearn/gaussian_process/correlation_models.py
#
# Implementing the separable squared-exponential function from Lawrance's
# thesis, see page 145:
#  http://db.acfr.usyd.edu.au/download.php/Lawrance2011_Thesis.pdf?id=2615
#
# Note that on page 145 there is not a negative in the time portion of the
# separable equation, but on page 147 there is. Thus, I decided that there
# likely should be the negative on page 145 as well.
#
def time_squared_exponential(theta, d):
    """
    Seperable time-dependent squared exponential:

        l_x, l_t, d_x, d_t --> r(l_x, l_t, d_x, d_t) =
                   n
            exp(  sum - (dx_i)^2 / ( 2 * l_x ^ 2 ) )
                 i = 1

          * exp(  - dt^2 / ( 2 * l_t ^ 2 ) )

    where l_x is the spatial length scale and
          l_t is a temporal time scale

    However, DACE uses theta rather than l_x, so we note the following:
        l_x = 1/sqrt(2*theta_x) => theta_x = 1/(2 * l_x ^ 2)
        l_t = 1/sqrt(2*theta_t) => theta_t = 1/(2 * l_t ^ 2)

    Thus, we will actually use:

        theta_x, theta_t, dx, dt --> r(theta_x, theta_t, dx, dt) =
                   n-1
            exp(  sum - theta_x * (dx_i)^2 )
                 i = 1

          * exp(  - theta_t * dt^2 )

    Compared with the normal squared-exponential:
                                          n
        theta, d --> r(theta, d) = exp(  sum  - theta_i * (d_i)^2 )
                                        i = 1

    Parameters
    ----------
    l_x : array_like
        An array with shape 1 (isotropic) or n (anisotropic) giving the
        autocorrelation parameter(s). For position.

    l_t : array_like
        An array with shape 1 (isotropic) or n (anisotropic) giving the
        autocorrelation parameter(s). For time.

    d_x : array_like
        An array with shape (n_eval, n_features) giving the componentwise
        distances between locations x and x' at which the correlation model
        should be evaluated.

    d_t : array_like
        An array with shape (n_eval, n_features) giving the componentwise
        distances between times t and t' at which the correlation model
        should be evaluated.

    Returns
    -------
    r : array_like
        An array with shape (n_eval, ) containing the values of the
        autocorrelation model.
    """

    theta = np.asarray(theta, dtype=np.float)
    d = np.asarray(d, dtype=np.float)

    print("Theta.shape:", theta.shape)
    print("d.shape:", d.shape)

    #assert theta.shape[1] == 2, "theta must have 2 columns, theta_x and theta_t"
    assert d.shape[1] == 3, "d must have 2 columns: x, y, and t"

    theta_x = theta #theta[:,0] # for x, y
    #theta_t = theta[:,1] # for t
    theta_t = np.asarray([1], dtype=np.float) # for t, TODO change this
    dx = d[:,:d.shape[1]-1] # all but last column, i.e.: x, y
    dt = d[:,d.shape[1]-1] # just the last column, i.e.: t

    if dx.ndim > 1:
        n_features = dx.shape[1]
    else:
        n_features = 1

    if theta_x.size == 1:
        return np.exp(-theta_x[0] * np.sum(dx ** 2, axis=1)) * \
            np.exp(-theta_t[0] * dt ** 2)
    elif theta_x.size != n_features:
        raise ValueError("Length of theta_x must be 1 or %s" % n_features)
    else:
        return np.exp(-np.sum(theta_x.reshape(1, n_features) * dx ** 2, axis=1)) * \
            np.exp(-theta_t.reshape(1, n_features) * dt ** 2)

#
# Gaussian Process Regression to learn thermals
#
# Extent - predict over bounding box of measurements given but extend this
#     bounding box this much in each direction
# Points - how much to divide each axis of the bounding box into, predicting
#     at each of these points
#
def GPR(timepos, measurements, gprParams, extent, points):
    # Compute bounds based on measurements
    path = timepos[:,1:timepos.shape[1]] # get [x,y] from [t,x,y]
    pos_min_x, pos_max_x, pos_min_y, pos_max_y = boundsFromPath(path)

    # Extend the prediction out from the measurements given
    pos_min_x -= extent
    pos_max_x += extent
    pos_min_y -= extent
    pos_max_y += extent

    # Generate all the points we want to output at
    # See: http://stackoverflow.com/a/32208788
    #grid_x, grid_y, grid_time = np.meshgrid(
    #    np.arange(pos_min_x, pos_max_x, (pos_max_x-pos_min_x)/points),
    #    np.arange(pos_min_y, pos_max_y, (pos_max_y-pos_min_y)/points),
    #    np.zeros(points))
    grid_x, grid_y = np.meshgrid(
        np.arange(pos_min_x, pos_max_x, (pos_max_x-pos_min_x)/points),
        np.arange(pos_min_y, pos_max_y, (pos_max_y-pos_min_y)/points))
    grid = np.vstack((grid_x.flatten(), grid_y.flatten())).T
    #grid_time = np.vstack((grid_x.flatten(), grid_y.flatten(), grid_time.flatten())).T

    gp = GaussianProcess(corr='squared_exponential',
    #gp = GaussianProcess(corr=time_squared_exponential,
                         theta0=gprParams.theta0,
                         thetaL=gprParams.thetaL,
                         thetaU=gprParams.thetaU,
                         nugget=gprParams.nugget,
                         random_start=gprParams.random_start)

    # Regression, fit to data using Maximum Likelihood Estimation of the parameters
    #gp.fit(timepos, measurements)
    gp.fit(path, measurements)

    # Prediction over our grid
    prediction, MSE = gp.predict(grid, eval_MSE=True)
    #prediction, MSE = gp.predict(grid_time, eval_MSE=True)
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
def ThermalGPR(timepos, measurements, gprParams, extent=10, points=50):
    # Run GPR
    (grid, grid_x, grid_y), prediction, sigma = GPR(timepos, measurements,
            gprParams, extent, points)

    # Get thermal
    return GPRtoThermal(grid, prediction, sigma)

#
# Get thermal from GPR with plotting
#
def ThermalGPRPlot(fig, timepos, measurements, gprParams, extent=10, points=50,
        fast=False, field=None):

    path = timepos[:,1:timepos.shape[1]] # get [x,y] from [t,x,y]

    (grid, grid_x, grid_y), prediction, sigma = GPR(timepos, measurements,
            gprParams, extent, points)

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

    # The mean
    ax.plot_surface(grid_x, grid_y, pred_surface, label='Prediction',
                    rstride=1, cstride=1, cmap=cm.jet,
                    alpha=0.5, linewidth=0, antialiased=True)

    if fast:
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.get_xaxis().set_ticks([])
        ax.get_yaxis().set_ticks([])

    if not fast:
        # Reshape from 1D to 2D so we can plot these
        sigma_surface = sigma.reshape(grid_x.shape)

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

    if not fast:
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
