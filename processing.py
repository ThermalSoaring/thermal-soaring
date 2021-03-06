#
# Run the thermal soaring procesing of data received from the autopilots
#

import json
import numpy as np
from time import sleep
from datetime import datetime
import matplotlib.pyplot as plt

from identification.data import xyToLatLong, readNetworkData, shrinkSamples
from identification.gpr import GPRParams, ThermalGPR, ThermalGPRPlot

#
# Processing thread, where we do thermal identification
#
def processingProcess(manager, debug):
    # Only show one figure, just update it on key press
    #
    # Note: to get the plot to update correctly on Linux, you may have to
    # change the matplotlib backend. I'm using TkAgg. However, on Windows, the
    # default one provided with Anaconda works fine apparently.
    #
    # .config/matplotlib/matplotlibrc:
    #   backend      : TkAgg
    #
    # http://matplotlib.org/users/customizing.html#customizing-matplotlib
    #
    fig = plt.figure(figsize=(10,5))

    while True:
        # Get the last so many data points
        networkData = manager.getAllData()

        # We want quite a few points
        if not networkData:
            if debug:
                print("No data yet")
            sleep(1)
            continue

        # We need some data to work with
        if len(networkData) < 10:
            if debug:
                print("Only have", len(networkData))
            sleep(1)
            continue

        data, lat_0 = readNetworkData(networkData)

        # Try to get about 50 points
        if len(data) > 100:
            #data = shrinkSamples(data, int(len(data)/50))
            data = data.iloc[len(data)-100:len(data), :]

        # Run GPR
        print("Running GPR with", len(data), "points")

        # Data to run GPR
        timepos = np.array(data[['time', 'x', 'y']])
        measurements = np.array(data[['energy']])
        gprParams = GPRParams(theta0=1e-2, thetaL=1e-10, thetaU=1e10,
                nugget=1, random_start=10)

        try:
            # Run GPR
            if debug:
                x, y, prediction, uncertainty = ThermalGPRPlot(fig, timepos,
                        measurements, gprParams, fast=True)

                # Update the plot
                plt.ion()
                plt.draw()
                plt.waitforbuttonpress(timeout=0.001)
            else:
                x, y, prediction, uncertainty = ThermalGPR(timepos, measurements,
                        gprParams)

            # Go back to the normal flight plan if we're not predicting with
            # 97.5% confidence that we have an upwards vertical velocity
            # (or if /2, then 83.6% confidence)
            #
            # Or, if it's imaginary
            #if not np.isreal(prediction) or prediction-1.9600*uncertainty <= 0:
            if not np.isreal(prediction) or prediction-1.9600/2*uncertainty <= 0.5:
                command = json.dumps({
                    "type": "command",
                    "date": str(datetime.now()),
                    "lat": 0,
                    "lon": 0,
                    "alt": 0,
                    "radius": 0,
                    "prediction": float(0),
                    "uncertainty": float(-1) # Magic value meaning we're not in a thermal
                    })

                # TODO see if the prediction is real!!!???
                if debug:
                    print("Prediction:", prediction)

            # If we do think we're in a thermal, send real data
            else:
                # Convert X/Y to Lat/Long
                lat, lon = xyToLatLong(x, y, lat_0)

                # Calculate average altitude from last 45 seconds
                s = 0
                for d in networkData:
                    s += d["alt"]
                avgAlt = s / len(networkData)

                # Send a new orbit and radius
                command = json.dumps({
                    "type": "command",
                    "date": str(datetime.now()),
                    "lat": lat,
                    "lon": lon,
                    "alt": avgAlt,
                    "radius": 10.0, # Can only be in 10 m intervals?
                    "prediction": float(prediction),
                    "uncertainty": float(uncertainty)
                    })

            manager.addCommand(command)

            if debug:
                print("Sending:", command)

        except ValueError:
            print("Error: ValueError, couldn't run GPR")

    print("Exiting processingProcess")
