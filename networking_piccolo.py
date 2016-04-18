#
# Connecting to the C++/Python interface for the Piccolo autopilot
#

import socket
import threading

#
# Thread to send commands through network connection
#
class NetworkingThreadSend(threading.Thread):
    def __init__(self, socket, manager, delimiter):
        threading.Thread.__init__(self)
        self.socket = socket
        self.manager = manager
        self.delimiter = delimiter

        # Store the output data since we will be sending it through multiple
        # send() calls
        self.sendBuf = b''

        # Used to tell when to exit this thread
        self.exiting = False

    def run(self):
        while not self.exiting:
            # Wait till we get a command
            c = self.manager.getCommandWait()

            # Add it to the buffer
            self.sendBuf += c.encode('utf-8') + self.delimiter

            # Send this command
            while self.sendBuf and not self.exiting:
                # See if we're ready to write data
                inputready, outputready, exceptready = \
                    select.select([],[self.socket],[],300)

                # Write some of the data
                for s in outputready:
                    sent = s.send(self.sendBuf)

                    # Remove the data we ended up being able to send
                    self.sendBuf = self.sendBuf[sent:]

                    # If we couldn't send something, then error
                    if sent == 0:
                        s.close()
                        print("Exiting, could not send data")
                        return

    def stop(self):
        self.exiting = True

#
# Thread to get data from the network connection
#
class NetworkingThreadReceive(threading.Thread):
    def __init__(self, socket, manager, debug, delimiter):
        threading.Thread.__init__(self)
        self.debug = debug
        self.socket = socket
        self.manager = manager
        self.delimiter = delimiter

        # Store the input data since we will be receiving it through multiple
        # recv() calls
        self.recvBuf = b''

        # Used to tell when to exit this thread
        self.exiting = False

    def run(self):
        # Count how many messages we get, debugging
        i = 0

        while not self.exiting:
            # See if we're ready to read data
            inputready, outputready, exceptready = \
                select.select([self.socket],[],[],300)

            # Read data
            for s in inputready:
                # Receive up to 4096 bytes
                data = s.recv(4096)

                # If no data was received, the connection was closed
                if not data:
                    s.close()
                    print("Exiting, connection closed")
                    return

                # Append to already-received data
                self.recvBuf += data

                # Process received messages
                while True:
                    # Split into (before,delim,after)
                    before, delimfound, after = \
                        self.recvBuf.partition(self.delimiter)

                    # If we found a delimiter, we have a complete message
                    # before that
                    if len(delimfound) > 0:
                        receivedData = json.loads(before.decode('utf-8'))
                        self.manager.addData(receivedData)

                        i += 1
                        if self.debug and i%125 == 0:
                            print(i, "Received:", receivedData)

                        # Save what we haven't processed already
                        self.recvBuf = after

                    # If we don't have any messages, continue receiving more
                    # data
                    else:
                        break

    def stop(self):
        self.exiting = True

#
# The process that connects over the network and starts the send and receive
# threads
#
def networkingProcess(server, port, manager, debug):
    # Connect to server
    print("Connecting to ", server, ":", port, sep="")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server, port))

    # I don't know if we want it blocking or not, maybe it doesn't matter since
    # they're in separate threads
    client.setblocking(1)

    # We'll speparate the data using a null byte
    delimiter = b'\0'

    # Start send/recieve threads
    receive = NetworkingThreadReceive(client, manager, debug, delimiter)
    send = NetworkingThreadSend(client, manager, delimiter)
    receive.start()
    send.start()
    receive.join()
    send.join()

    print("Exiting networkingProcess")
