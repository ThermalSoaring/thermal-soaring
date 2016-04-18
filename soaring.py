#
# The Python side of the C++/Python interface
#
# Based on:
# https://docs.python.org/3/howto/sockets.html
# http://stackoverflow.com/a/1716173
# http://stackoverflow.com/a/27345949
import os
import sys
import json
import select
import argparse
import threading
import numpy as np
from time import sleep
from datetime import datetime
from collections import deque
import multiprocessing
from multiprocessing.managers import SyncManager
import matplotlib.pyplot as plt

from data import xyToLatLong, readNetworkData, shrinkSamples
from gpr import GPRParams, ThermalGPR, ThermalGPRPlot

# For debugging
# Trigger with: Tracer()()
# From: http://stackoverflow.com/a/35773311
from IPython.core.debugger import Tracer

#
# Allow working with a deque between threads
#
SyncManager.register('deque', deque)

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

        # Note: 375 at 25 Hz is 15 seconds
        if len(networkData) < 375:
            if debug:
                print("Only have", len(networkData))
            sleep(1)
            continue

        data, lat_0 = readNetworkData(networkData)

        # Take only every n'th point
        data = shrinkSamples(data, 5)

        if len(data) > 100:
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
        else:
            if debug:
                print("Skipping GPR. Only", len(data),
                    "samples at unique positions")

    print("Exiting processingProcess")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server', type=str, default="127.0.0.1:2050",
            help='address of MAVProxy or the C++/Python interface server if for Piccolo')
    parser.add_argument('-d', dest='debug', action='store_true',
            help='debugging information')
    parser.add_argument('-p', dest='piccolo', action='store_true',
            help='Connect to Piccolo autopilot rather than the Pixhawk')
    args = parser.parse_args()

    # Get the server and port number from the input arguments
    try:
        server, port = args.server.split(":")
        port = int(port)
    except ValueError:
        print("Error: invalid server address, example: localhost:2050")
        sys.exit(1)

    # Import either the mavlink or Piccolo networking
    if args.piccolo:
        from networking_piccolo import networkingProcess
    else:
        from networking_mavlink import networkingProcess

    # Max length of data to keep
    maxLength = 750

    with SyncManager() as manager:
        # Data to be passed back and forth between processes
        data = manager.deque(maxlen=maxLength)
        commands = manager.deque(maxlen=maxLength)

        # When we add another command to send to the autopilot, wake up the
        # sending thread to send this new data. This is to keep the sending
        # thread from using 100% of the CPU since the select() will wake up
        # continuously when we're done sending data and don't have any more to
        # send yet.
        commandCondition = multiprocessing.Condition()

        # Functions to operate on these deques
        nd = NetworkData(data, commands, commandCondition)

        # Start the processes
        n = multiprocessing.Process(target=networkingProcess,
                args=[server, port, nd, args.debug])
        p = multiprocessing.Process(target=processingProcess,
                args=[nd, args.debug])
        n.start()
        p.start()
        p.join()
        n.join()
