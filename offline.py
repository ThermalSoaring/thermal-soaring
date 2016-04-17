#
# Compare GPR with Bayesian parameter estimation offline using recorded
# simulation data, rather than live connected to the simulator
#

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from bayesian import BayesianLearning
from gpr import GPRParams, ThermalGPRPlot
from data import windowSubset, shrinkSamples, readData, \
    compareXYLatLong, xyToLatLong

#
# Process the data using batch processing over a certain window size. This is an
# approach that some papers have used.
#
# slidingWindow - Process the data in batch sliding window sizes of a certain number
#     of seconds
# slideBy - Slide by a certain number of seconds for each subsequent iteration
# shrinkSampleSize - Take only every nth sample rather than all the data in this
#     sliding window, needed to speed up GPR and make it use less memory
# dataFrequency - The frequency in Hz that the data has been recored ata.
# limitWindows - which windows to run with, all by default, otherwise specify
#     e.g., [0,3,5]
#
def batchProcessing(df, slidingWindow=30, slideBy=15,
                    shrinkSampleSize=10, dataFrequency=25,
                    limitWindows=None):
    # How many samples we've recored
    length = df.shape[0]

    # Convert from seconds to samples
    slidingWindowSizeInSamples = slidingWindow * dataFrequency
    slideByInSamples = slideBy * dataFrequency

    # How many sliding windows will we be able to have?
    slidingWindows = np.floor(length/slideByInSamples)

    # Run GPR on each sliding window
    for i in range(0, int(slidingWindows)):
        if limitWindows and i not in limitWindows:
            continue

        # Limit the input data for only our sliding window
        start = slideByInSamples*i
        size = slidingWindowSizeInSamples
        df_subset = windowSubset(df, start, size)
        df_subset = shrinkSamples(df_subset, shrinkSampleSize)

        print()
        print("Sliding window #", i, " for samples ", start, " to ", start+size, sep="")
        print()

        # Compute Lat-Long to X-Y for this sliding window
        data, lat_0 = readData(df_subset, startAtZero=True)

        # Look at the flight path in this window
        #compareXYLatLong(data, latlong=False)

        # Put both in one figure
        fig = plt.figure(figsize=(15,8))
        measurements = np.array(data[['VelDown']])
        path = np.array(data[['x', 'y']])

        # Run GPR
        x, y, prediction, uncertainty = ThermalGPRPlot(fig, path, measurements,
                GPRParams(theta0=1e-2, thetaL=1e-10, thetaU=1e10, nugget=1,
                    random_start=10))
        lat, lon = xyToLatLong(x, y, lat_0)
        print("Thermal at:", lat, ",", lon)

        # Run Bayesian
        BayesianLearning(fig, path, measurements, subplot=122)

        plt.show()

if __name__ == "__main__":
    # Let's do this thing
    df = pd.read_csv('../gaussian-process-regression/run9.csv')
    batchProcessing(df, slidingWindow=45, slideBy=45, limitWindows=[4,5])
