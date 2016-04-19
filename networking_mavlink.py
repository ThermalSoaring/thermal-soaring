#
# Connecting to mavlink for the Pixhawk rather than the Piccolo
#
import json
import mavlink
import threading
from datetime import datetime
from pymavlink import mavutil, mavwp

#
# Thread to send commands through network connection
#
class NetworkingThreadSend(threading.Thread):
    def __init__(self, master, manager, wp, wp_loading, debug):
        threading.Thread.__init__(self)
        self.master = master
        self.manager = manager
#        self.wp = wp
#        self.wp_loading = wp_loading
        self.debug = debug

        # Used to tell when to exit this thread
        self.exiting = False

    def run(self):
        while not self.exiting:
            # Wait till we get a command
            c = json.loads(self.manager.getCommandWait())

            # Send the new waypoint and orbit
            #
            # See: http://www.colorado.edu/recuv/2015/05/25/mavlink-protocol-waypoints
            lat = c["lat"]*1e-7 # TODO is this right?
            lon = c["lon"]*1e-7
            alt = c["alt"]
            radius = c["radius"]
            frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT

            self.master.mav.mission_item_send(
                    self.master.target_system,
                    self.master.target_component,
                    0,
                    frame,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    2, 0, 0, radius, 0, 0,
                    lat, lon, alt)
            self.master.set_mode('GUIDED')

#            points = [[lat,lon,alt,radius]]
#
#            # Remove all points in our saved copy except for the home point
#            home = self.wp.wp(0)
#            self.wp.clear()
#
#            # Assuming we found a home point...
#            if home:
#                self.wp.add(home)
#            else:
#                print("Warning: no home point, not sending waypoint!")
#                continue
#
#            # We'll be sending the next waypoint
#            seq = home.seq+1
#
#            # Add the new points
#            for lat, lon, alt, radius in points:
#                self.wp.add(mavutil.mavlink.MAVLink_mission_item_message(
#                    self.master.target_system,
#                    self.master.target_component,
#                    seq,
#                    frame,
#                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
#                    0, 0, 0, radius, 0, 0,
#                    lat, lon, alt))
#                seq += 1
#
#            # Clear all the waypoints on the autopilot
#            self.master.waypoint_clear_all_send()
#            self.master.waypoint_count_send(self.wp.count())
#
#            # Tell the other thread to send our new flight plan
#            self.wp_loading.set()
#
#            if self.debug:
#                print("New mission is", self.wp.count(), "points")

    def stop(self):
        self.exiting = True

#
# Thread to receive data
#
class NetworkingThreadReceive(threading.Thread):
    def __init__(self, master, manager, wp, wp_loading, debug):
        threading.Thread.__init__(self)
        self.master = master
        self.manager = manager
#        self.wp = wp
#        self.wp_loading = wp_loading
        self.debug = debug

        # Used to tell when to exit this thread
        self.exiting = False

        # Initial parameters
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.rollspeed = 0.0
        self.pitchspeed = 0.0
        self.yawspeed = 0.0
        self.airspeed = 0.0
        self.groundspeed = 0.0
        self.heading = 0.0
        self.throttle = 0.0
        self.alt = 0.0
        self.timestamp = 0.0
        self.timeboot = 0.0
        self.pressure_abs = 0.0
        self.pressure_diff = 0.0
        self.temperature = 0.0
        self.battery = 0.0
        self.wind_direction = 0.0
        self.wind_speed = 0.0
        self.wind_speed_z = 0.0
        self.lat = 0.0
        self.lon = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.xacc = 0.0
        self.yacc = 0.0
        self.zacc = 0.0
        self.xgyro = 0.0
        self.ygyro = 0.0
        self.zgyro = 0.0
        self.xmag = 0.0
        self.ymag = 0.0
        self.zmag = 0.0
        self.local_x = 0.0
        self.local_y = 0.0
        self.local_z = 0.0
        self.local_vx = 0.0
        self.local_vy = 0.0
        self.local_vz = 0.0
        self.ahrs_roll = 0.0
        self.ahrs_pitch = 0.0
        self.ahrs_yaw = 0.0
        self.ahrs_lat = 0.0
        self.ahrs_lon = 0.0
        self.ahrs_alt = 0.0

    # Receive incoming mavlink messages from the groundstation
    def run(self):
        # Count how many messages we get, debugging
        i = 0

        while not self.exiting:
            msg = self.master.recv_match(blocking=True)

            if not msg:
                print("Exiting, could not receive message")
                return()

            msgType = msg.get_type()
            msgData = msg.to_dict()

            if msgType == "BAD_DATA":
                print("Warning: bad data from groundstation")
                #if mavutil.all_printable(msg.data):
                #    sys.stdout.write(msg.data)
                #    sys.stdout.flush()
            elif msgType == "ATTITUDE":
                self.roll = msgData['roll']
                self.pitch = msgData['pitch']
                self.yaw = msgData['yaw']
                self.rollspeed = msgData['rollspeed']
                self.pitchspeed = msgData['pitchspeed']
                self.yawspeed = msgData['yawspeed']
            elif msgType == "VFR_HUD":
                self.airspeed = msgData['airspeed']
                self.groundspeed = msgData['groundspeed']
                self.heading = msgData['heading']
                self.throttle = msgData['throttle']
                self.alt = msgData['alt']
            elif msgType == "SYSTEM_TIME":
                self.timestamp = msgData['time_unix_usec']
                self.timeboot = msgData['time_boot_ms']
            elif msgType == "SCALED_PRESSURE":
                self.pressure_abs = msgData['press_abs']
                self.pressure_diff = msgData['press_diff']
                self.temperature = msgData['temperature']
            elif msgType == "SCALED_IMU2":
                self.xacc = msgData['xacc']
                self.yacc = msgData['yacc']
                self.zacc = msgData['zacc']
                self.xgyro = msgData['xgyro']
                self.ygyro = msgData['ygyro']
                self.zgyro = msgData['zgyro']
                self.xmag = msgData['xmag']
                self.ymag = msgData['ymag']
                self.zmag = msgData['zmag']
            elif msgType == "SYS_STATUS":
                self.battery = msgData['battery_remaining']
            elif msgType == "WIND":
                self.wind_direction = msgData['direction']
                self.wind_speed = msgData['speed']
                self.wind_speed_z = msgData['speed_z']
            elif msgType == "GLOBAL_POSITION_INT":
                self.lat = msgData['lat']
                self.lon = msgData['lon']
                self.vx = msgData['vx']
                self.vy = msgData['vy']
                self.vz = msgData['vz']
            elif msgType == "LOCAL_POSITION_NED":
                self.local_x = msgData['x']
                self.local_y = msgData['y']
                self.local_z = msgData['z']
                self.local_vx = msgData['vx']
                self.local_vy = msgData['vy']
                self.local_vz = msgData['vz']
            elif msgType == "AHRS3":
                self.ahrs_roll = msgData['roll']
                self.ahrs_pitch = msgData['pitch']
                self.ahrs_yaw = msgData['yaw']
                self.ahrs_lat = msgData['lat']
                self.ahrs_lon = msgData['lng']
                self.ahrs_alt = msgData['altitude']
#            elif msgType in ["MISSION_REQUEST", "WAYPOINT_REQUEST"]:
#                # In combination with the sending thread above, when we want to
#                # send some waypoints, we tell the autopilot to request a
#                # certain number of them in that thread. Then, here we actually
#                # send them as it asks for them.
#                if self.wp_loading.is_set():
#                    if msg.seq > self.wp.count():
#                        print("Request for bad waypoint")
#                        continue
#
#                    self.master.mav.send(self.wp.wp(msg.seq))
#
#                    if self.debug:
#                        print('Sending waypoint {0}'.format(msg.seq))
#
#                    # We just sent the last waypoint
#                    if msg.seq == self.wp.count() - 1:
#                        self.wp_loading.clear()
#
#                        if self.debug:
#                            print("Sent last waypoint, switching to guided mode")
#                            self.master.set_mode_guided()
#
#                            # TODO this is a bad idea, but it makes it use the
#                            # new flight plan in the simulator
#                            #print("Switching to manual and back to auto")
#                            #self.master.set_mode_manual()
#                            #self.master.set_mode_auto()
#
#            elif msgType in ["MISSION_ITEM", "WAYPOINT"]:
#                # Save the waypoints that are already loaded. We'll get some of
#                # these messages since we request all waypoints initially.
#                self.wp.add(msg)

            #else:
            #    print(msg)

            # TODO presently just assuming every time we get GPS data is
            # a good time to say we've received new data
            if msgType == "GLOBAL_POSITION_INT":
                receivedData = {
                    "type": "data",
                    "date": str(datetime.now()),
                    "time": self.timestamp,
                    "lat": self.lat,
                    "lon": self.lon,
                    "alt": self.alt,
                    "velDown": self.local_vz,
                    "IAS": self.airspeed,
                    "TAS": self.airspeed,
                    "RPS": 0,
                    "accelZ": self.zacc,
                    "energy": self.local_vz, # TODO fix this
                    "avgEnergy": 0 # TODO and this
                }
                self.manager.addData(receivedData)

                i += 1
                if self.debug and i%125 == 0:
                    print(i, "Received:", receivedData)

    def __repr__(self):
        return("Bat %d AirV %f Alt: %f Lat: %f Lon: %f Vz: %f WindV: %f WindVZ: %f Temp: %f" % (
            self.battery, self.airspeed, self.alt, self.lat, self.lon,
            self.vz, self.wind_speed, self.wind_speed_z, self.temperature))

    def header(self):
        return("Roll, Pitch, Yaw, RollSpeed, PitchSpeed, YawSpeed, AirSpeed, GroundSpeed, Heading, Throttle, Alt, Timestamp, Timeboot, PressureAbs, PressureDiff, Temperature, Battery, WindDirection, WindSpeed, WindSpeedZ, Lat, Lon, Vx, Vy, Vz")

    def __str__(self):
        return(', '.join([str(i) for i in [self.roll, self.pitch, self.yaw, self.rollspeed, self.pitchspeed, self.yawspeed, self.airspeed, self.groundspeed, self.heading, self.throttle, self.alt, self.timestamp, self.timeboot, self.pressure_abs, self.pressure_diff, self.temperature, self.battery, self.wind_direction, self.wind_speed, self.wind_speed_z, self.lat, self.lon, self.vx, self.vy, self.vz]]))

    def stop(self):
        self.exiting = True

#
# The process that communciates with mavlink
#
def networkingProcess(server, port, manager, debug):
    # Connect to server
    print("Connecting to ", server, ":", port, sep="")

    # Manage waypoints
    wp = mavwp.MAVWPLoader()

    # Connect to MAVProxy ground station
    master = mavutil.mavlink_connection(server + ":" + str(port))

    # Wait for a heartbeat so we know the target system IDs
    print("Waiting for heartbeat")
    master.wait_heartbeat()

    # Do we need to get the parameters?
    #master.param_fetch_all()

    # Shared loading waypoints variable between threads since we request to
    # send in one and then send in the receive thread. We're using this rather
    # than a boolean, since this will be referenced rather than copied into
    # each thread, and rather than a condition since the condition doesn't let
    # you check without waiting. This lets you wait or check.
    wp_loading = threading.Event()

    # Wait till armed
    print("Waiting for motors to be armed")
    master.motors_armed_wait()

    # Set that we want to receive data
    print("Requesting data")
    rate = 25 # Hz
    master.mav.request_data_stream_send(
            master.target_system,
            master.target_component,
            mavlink.MAV_DATA_STREAM_ALL, rate, 1)

    # Request the home point
    master.waypoint_request_send(0)

    # Start send/recieve threads
    receive = NetworkingThreadReceive(master, manager, wp,
            wp_loading, debug)
    send = NetworkingThreadSend(master, manager, wp,
            wp_loading, debug)
    receive.start()
    send.start()
    receive.join()
    send.join()

    print("Exiting networkingProcess")
