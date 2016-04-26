#
# Connect thermal soaring code with either the Pixhawk or Piccolo
#
import sys
import argparse
from collections import deque
import multiprocessing
from multiprocessing.managers import SyncManager
from processing import processingProcess

# For debugging
# Trigger with: Tracer()()
# From: http://stackoverflow.com/a/35773311
from IPython.core.debugger import Tracer

#
# Allow working with a deque between threads
# http://stackoverflow.com/a/27345949
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

    with SyncManager() as syncManager:
        # Data to be passed back and forth between processes
        data = syncManager.deque(maxlen=maxLength)
        commands = syncManager.deque(maxlen=maxLength)

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
