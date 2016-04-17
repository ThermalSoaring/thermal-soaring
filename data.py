#
# Handle working with CSV files or live data from the simulator
#

import numpy as np
import pandas as pd

#
# Compute bounds based on measurements
#
def boundsFromPath(path):
    pos_min_x = np.min(path[:,0])
    pos_max_x = np.max(path[:,0])
    pos_min_y = np.min(path[:,1])
    pos_max_y = np.max(path[:,1])

    if pos_max_x-pos_min_x == 0:
        pos_min_x = -1
        pos_max_x = 1
    if pos_max_y-pos_min_y == 0:
        pos_min_y = -1
        pos_max_y = 1

    return pos_min_x, pos_max_x, pos_min_y, pos_max_y

#
# Take a list of points and add the specified number of points
# in between every set of two points linearly
#
def morePoints(path, num):
    newPath = []

    # Add points between each pair
    for i in range(1, len(path)):
        prev = path[i-1]
        cur  = path[i]

        # Add the first point
        newPath.append(prev)

        # Calculate the vector toward the next point
        towardCurrent = np.subtract(cur, prev)
        distance = np.linalg.norm(towardCurrent)
        towardCurrentNorm = towardCurrent / np.linalg.norm(towardCurrent)
        eachStep = distance/(num+1)

        # Go the right proportion along it the right number of times
        # to insert the specified number of points between
        for j in range(0, num):
            newPosition = prev + (j+1)*eachStep*towardCurrentNorm
            newPath.append(tuple(newPosition))

    # Append the last point as well
    newPath.append(path[-1])

    return np.array(newPath)

#
# Convert from lat-long to x-y
#  http://stackoverflow.com/a/16271669
#
# lat_0 is the latitude in the center of the region you'll be looking at.
# For instance, you could average over all the latitudes.
#
def latLongToXY(lat, long, lat_0):
    r = 6.371e6 # m
    x = r*long*np.cos(lat_0)
    y = r*lat

    return x, y

#
# Convert from x-y to lat-long
#
def xyToLatLong(x, y, lat_0):
    r = 6.371e6 # m
    lat = y/r
    long = x/r/np.cos(lat_0)

    return lat, long

#
# Read the data from the simulator
#
# If you don't care about actual X-Y position, you can use either
# startAtZero to set the first position as the zero point or use
# normalize to make the X-Y values all be between 0 and 1.
#
def readData(df, startAtZero=False, normalize=False):
    data = pd.DataFrame()

    # Average all the latitudes to use as the center of our map
    lat_0 = np.average(df[['Latitude']]) #*np.pi/180

    # Get the data we care about and convert Lat-Long to X-Y
    #for index, row in df[['Latitude','Longitude','VelDown']].iterrows():
    for index, row in df.iterrows():
        lat = row['Latitude'] #*np.pi/180
        long = row['Longitude'] #*np.pi/180
        vel = row['VelDown']
        x, y = latLongToXY(lat, long, lat_0)
        data = data.append(pd.DataFrame([[x, y, vel, lat, long]], index=[index],
                                        columns=['x','y','VelDown',
                                                 'Latitude', 'Longitude']))

    # Try to shrink the range of X-Y values if desired
    if startAtZero:
        data[['x']] -= data[['x']].iloc[0]
        data[['y']] -= data[['y']].iloc[0]
    elif normalize:
        minX, maxX = np.min(data[['x']]), np.max(data[['x']])
        minY, maxY = np.min(data[['y']]), np.max(data[['y']])
        data[['x']] -= minX
        data[['y']] -= minY
        data[['x']] /= maxX-minX
        data[['y']] /= maxY-minY

    # For GPR (x,y) must be unique
    data = data.drop_duplicates(subset=['x','y'])

    return data, lat_0

#
# Read data from a deque of objects from the network
#
def readNetworkData(networkData):
    if not networkData:
        return None

    # Format so so we can run GPR on it
    data = pd.DataFrame()

    # Just take the first lattitude as the center of our map
    lat_0 = networkData[0]["lat"]

    # Get the data we care about and convert Lat-Long to X-Y
    for index, row in enumerate(networkData):
        lat = row['lat']
        long = row['lon']
        energy = row['energy']
        x, y = latLongToXY(lat, long, lat_0)
        data = data.append(pd.DataFrame([[x, y, energy, lat, long]], index=[index],
                                        columns=['x','y','energy',
                                                 'Latitude', 'Longitude']))

    # For GPR (x,y) must be unique
    data = data.drop_duplicates(subset=['x','y'])

    return data, lat_0

#
# Compare Lat-Long with X-Y
#
def compareXYLatLong(data, xy=True, latlong=True):
    if xy:
        data.plot(x='x', y='y', marker='.',
                title="Glider Position X-Y", figsize=(15,8))
    if latlong:
        data.plot(x='Longitude', y='Latitude', marker='.',
                title="Glider Position Lat-Long", figsize=(15,8))

#
# We want to look at a window of a certain size
#
# Start and size are specified in samples, so if you want a 45-second window
# and you're recording data at 25 Hz, you'd specify:
#   start = start_time [s] * 25 [1/s]
#   size  = 45 [s] * 25 [1/s]
#
def windowSubset(df, start, size):
    return df.iloc[start:start+size,:]

#
# Take only ever nth sample
#
def shrinkSamples(df, n):
    return df.iloc[::n, :]
