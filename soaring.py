#
# Connect thermal soaring code with either the Pixhawk or Piccolo
#
import sys
import argparse
from collections import deque
import multiprocessing
from multiprocessing.managers import SyncManager
from processing import NetworkData, processingProcess

# For debugging
# Trigger with: Tracer()()
# From: http://stackoverflow.com/a/35773311
from IPython.core.debugger import Tracer

#
# Allow working with a deque between threads
# http://stackoverflow.com/a/27345949
#
SyncManager.register('deque', deque)

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
