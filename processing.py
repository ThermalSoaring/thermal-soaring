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
# Work with data and commands
#
class NetworkData:
    def __init__(self, data, commands, cond):
        self.data = data
        self.commands = commands
        self.commandCondition = cond

    # Add data/commands
    def addData(self, d):
        self.data.append(d)

    def addCommand(self, c):
        with self.commandCondition:
            self.commands.append(c)
            self.commandCondition.notify()

    # Get one and pop off that we've used this data
    def getData(self):
        # Must copy since AutoProxy[deque] doesn't allow indexing
        c = self.data.copy()

        if c:
            d = c[0]
            self.data.popleft()
            return d

        return None

    # Just get *all* the data, so we can just keep on running the thermal
    # identification on the last so many data points
    def getAllData(self):
        return self.data.copy()

    # Get one and pop off that we've sent this command
    def getCommand(self):
        c = self.commands.copy()

        if c:
            d = c[0]
            self.commands.popleft()
            return d

        return None

    # If we have a command available, return it. Otherwise, wait for one to be
    # added, and then return that
    def getCommandWait(self):
        with self.commandCondition:
            while True:
                c = self.getCommand()

                if c:
                    return c

                self.commandCondition.wait()

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

        # Note: 250 at 25 Hz is 10 seconds
        if len(networkData) < 250:
            if debug:
                print("Only have", len(networkData))
            sleep(1)
            continue

        data, lat_0 = readNetworkData(networkData)

        # Take only every n'th point
        if len(data) > 100:
            data = shrinkSamples(data, 5)

        # Run GPR
        if debug:
            print("Running GPR")

        # Data to run GPR
        path = np.array(data[['x', 'y']])
        measurements = np.array(data[['energy']])
        gprParams = GPRParams(theta0=1e-2, thetaL=1e-10, thetaU=1e10,
                nugget=1, random_start=10)

        try:
            # Run GPR
            if debug:
                x, y, prediction, uncertainty = ThermalGPRPlot(fig, path,
                        measurements, gprParams)

                # Update the plot
                plt.ion()
                plt.draw()
                plt.waitforbuttonpress(timeout=0.001)
            else:
                x, y, prediction, uncertainty = ThermalGPR(path, measurements,
                        gprParams)

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
                "radius": 20.0, # Can only be in 10 m intervals
                "prediction": float(prediction),
                "uncertainty": float(uncertainty)
                })
            if debug:
                print("Sending:", command)
            manager.addCommand(command)

        except ValueError:
            print("Error: ValueError, couldn't run GPR")

    print("Exiting processingProcess")
