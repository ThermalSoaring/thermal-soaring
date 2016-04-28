#
# Connecting to mavlink for the Pixhawk rather than the Piccolo
#
import json
import mavlink
import threading
from math import pi
from time import sleep, time
from datetime import datetime
from pymavlink import mavutil, mavwp, mavparm

# Start at 600 m above home point, stop if we drop down to 200 m
startAlt = 200
stopAlt = 100
turnRadius = 3

#
# Thread to send commands through network connection
#
class NetworkingThreadSend(threading.Thread):
    def __init__(self, master, manager, wp, debug):
        threading.Thread.__init__(self)
        self.master = master
        self.manager = manager
        self.wp = wp
        self.debug = debug

        # Used to tell when to exit this thread
        self.exiting = False

    def run(self):
        while not self.exiting:
            # Wait till we get a command
            c = json.loads(self.manager.getCommandWait())

            # Send the new waypoint and orbit
            lat = c["lat"]*180/pi
            lon = c["lon"]*180/pi
            #alt = c["alt"]
            alt = startAlt
            #radius = c["radius"]
            radius = turnRadius

            # Only enable when we're above the home point by more than stopAlt
            home = self.wp.wp(0)

            if home:
                AGL = c["alt"] - home.z

                # At the moment uncertainty = -1 means we're not in a thermal, so
                # continue with the normal flight plan
                #
                # Or, if we command below our stop altitude, also continue with the
                # normal flight plan
                if c["uncertainty"] != -1 and AGL > stopAlt:
                    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT

                    # Send a new waypoint to fly to
                    self.master.mav.mission_item_send(
                            self.master.target_system,
                            self.master.target_component,
                            0,
                            frame,
                            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                            2, 0, 0, radius, 0, 0,
                            lat, lon, alt)

                    # Set us to be in the mode to actually fly to it rather than
                    # continuing on the current mission / flight plan
                    self.master.set_mode('GUIDED')

                    print("Orbiting, Prediction:", c["prediction"], "Uncertainty:",
                            c["uncertainty"], "AGL:", AGL)
                else:
                    print("Skipping, Uncertainty:", c["uncertainty"],
                            "AGL:", AGL, "StopAlt:", stopAlt)
                    # Continue on normal flight plan
                    self.master.set_mode('AUTO')

    def stop(self):
        self.exiting = True

#
# Thread to receive data
#
class NetworkingThreadReceive(threading.Thread):
    def __init__(self, master, manager, wp, debug):
        threading.Thread.__init__(self)
        self.master = master
        self.manager = manager
        self.debug = debug

        # Record if we've cut the throttle
        self.cutThrottle = False

        # Waypoints
        self.wp = wp

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
        self.airspeedLast = 0.0
        self.groundspeed = 0.0
        self.heading = 0.0
        self.throttle = 0.0
        self.climb = 0.0
        self.alt = 0.0
        self.relative_alt = 0.0
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
                self.roll = msgData['roll'] # rad, -pi..+pi
                self.pitch = msgData['pitch'] # rad, -pi..+pi
                self.yaw = msgData['yaw'] # rad, -pi..+pi
                self.rollspeed = msgData['rollspeed'] # rad/s
                self.pitchspeed = msgData['pitchspeed'] # rad/s
                self.yawspeed = msgData['yawspeed'] # rad/s
            elif msgType == "VFR_HUD":
                self.airspeedLast = self.airspeed # Save previous value
                self.airspeed = msgData['airspeed'] # m/s
                self.groundspeed = msgData['groundspeed'] # m/s
                self.heading = msgData['heading'] # 0..360, 0 = north
                self.throttle = msgData['throttle'] # 0 to 100, integer percentage
                self.alt = msgData['alt'] # m (MSL)
                self.climb = msgData['climb'] # m/s
            elif msgType == "SYSTEM_TIME":
                self.timestamp = msgData['time_unix_usec'] # microseconds since UNIX epoch
                self.timeboot = msgData['time_boot_ms'] # milliseconds since boot
            elif msgType == "SCALED_PRESSURE":
                self.pressure_abs = msgData['press_abs'] # hectopascal
                self.pressure_diff = msgData['press_diff'] # differential pressure, hectopascal
                self.temperature = msgData['temperature'] # 0.01 degrees celsius
            elif msgType == "SCALED_IMU2":
                self.xacc = msgData['xacc']*1e-3/9.81 # mg -> m/s^2
                self.yacc = msgData['yacc']*1e-3/9.81 # m/s^2
                self.zacc = msgData['zacc']*1e-3/9.81 # m/s^2
                self.xgyro = msgData['xgyro'] # millirad/sec
                self.ygyro = msgData['ygyro'] # millirad/sec
                self.zgyro = msgData['zgyro'] # millirad/sec
                self.xmag = msgData['xmag'] # milli tesla
                self.ymag = msgData['ymag'] # milli tesla
                self.zmag = msgData['zmag'] # milli tesla
            elif msgType == "SYS_STATUS":
                self.battery = msgData['battery_remaining'] # 0 - 100, -1 if not being estimated
            elif msgType == "WIND":
                self.wind_direction = msgData['direction'] # degrees, direction wind is coming from
                self.wind_speed = msgData['speed'] # m/s
                self.wind_speed_z = msgData['speed_z'] # m/s
            elif msgType == "GLOBAL_POSITION_INT":
                self.lat = msgData['lat']*1e-7/180*pi # rad
                self.lon = msgData['lon']*1e-7/180*pi # rad
                self.alt = msgData['alt']*1e-3 # m
                self.relative_alt = msgData['relative_alt']*1e-3 # m
                self.vx = msgData['vx']*1e-3 # m/s
                self.vy = msgData['vy']*1e-3 # m/s
                self.vz = msgData['vz']*1e-3 # m/s
                self.heading = msgData['hdg']*1e-3 # yaw angle, degrees, 0.0..359.99, UINT16_MAX if unknown
            elif msgType == "LOCAL_POSITION_NED":
                self.local_x = msgData['x']
                self.local_y = msgData['y']
                self.local_z = msgData['z']
                self.local_vx = msgData['vx']
                self.local_vy = msgData['vy']
                self.local_vz = msgData['vz']
            elif msgType == "AHRS3":
                # TODO Research data? Is this available on the Pixhawk? How do we get EKF results?
                self.ahrs_roll = msgData['roll'] # rad
                self.ahrs_pitch = msgData['pitch'] # rad
                self.ahrs_yaw = msgData['yaw'] # rad
                self.ahrs_lat = msgData['lat']*1e-7/180*pi # rad
                self.ahrs_lon = msgData['lng']*1e-7/180*pi # rad
                self.ahrs_alt = msgData['altitude'] # MSL
            elif msgType in ["MISSION_ITEM", "WAYPOINT"]:
                # Save the waypoints that are already loaded. We'll get some of
                # these messages since we request all waypoints initially.
                self.wp.add(msg)
            #else:
            #    print(msg)

            #
            # Energy equation
            # Note to Travis: this is probably wrong
            #
            # Prop data based on T15 Electric
            currentVelDown = self.local_vz
            currentAccelZ = self.zacc
            currentRPS = self.throttle # This is definitely wrong, but how do we get motor RPM?
            currentTAS = self.airspeed
            currentIAS = self.airspeed
            diffIAS = self.airspeed - self.airspeedLast # This is also probably wrong
            g = 9.8
            a_n = -0.0176
            b_n = 0.3782
            c_n = -2.4993
            rho_inf = 1.11164
            d_prop = 0.4572
            C_T = 0.506
            mg = 1.11164
            currentEnergy = -currentVelDown + currentIAS*diffIAS/g \
                - (a_n*currentTAS**2 + b_n*currentTAS + c_n)*(-currentAccelZ/g)**1.5 \
                - (rho_inf*currentRPS**2 * d_prop**2 * C_T)/mg

            # TODO presently just assuming every time we get GPS data is
            # a good time to say we've received new data
            if msgType == "GLOBAL_POSITION_INT":
                receivedData = {
                    "type": "data",
                    "date": str(datetime.now()),
                    "time": self.timeboot*1e-3, # s
                    "lat": self.lat,
                    "lon": self.lon,
                    "alt": self.alt,
                    "velDown": self.local_vz,
                    "IAS": self.airspeed,
                    "TAS": self.airspeed,
                    "RPS": 0,
                    "accelZ": self.zacc,
                    #"energy": currentEnergy,
                    "energy": -self.local_vz,
                    "avgEnergy": 0 # TODO fix this
                }

                # Cut the throttle if we're above startAlt meters but don't reenable
                # it until we drop to stopAlt meters
                home = self.wp.wp(0)

                if home:
                    AGL = self.alt - home.z

                    # TODO Until we get the currentEnergy thing working, the
                    # throttle messes up the GPR, so only use points where
                    # after we have cut the engine
                    if self.cutThrottle and AGL > stopAlt:
                        self.manager.addData(receivedData)

                    if not self.cutThrottle and AGL > startAlt:
                        self.cutThrottle = True
                        print("Alt:", self.alt, "Home:", home.z, "StartAlt:",
                                startAlt, "cutting throttle")
                        setThrottle(self.master, 0)
                    elif self.cutThrottle and AGL < stopAlt:
                        self.cutThrottle = False
                        setThrottle(self.master, 100)
                        print("Alt:", self.alt, "Home:", home.z, "StopAlt:",
                                stopAlt, "uncutting throttle")
                else:
                    print("Warning: no home point, will not adjust throttle")

                i += 1
                if self.debug and i%125 == 0:
                    print(i, "Received:", receivedData)

    def stop(self):
        self.exiting = True

#
# Allow us to cut the throttle by setting this to zero or back to normal by
# setting it to 100
#
def setThrottle(master, throttle=100):
    params = mavparm.MAVParmDict()
    params.mavset(master, b'TRIM_THROTTLE', throttle)

#
# The process that communciates with mavlink
#
def networkingProcess(server, port, manager, debug):
    # Connect to server
    print("Connecting to ", server, ":", port, sep="")

    # Connect to MAVProxy ground station
    master = mavutil.mavlink_connection(server + ":" + str(port))

    # Wait for a heartbeat so we know the target system IDs
    print("Waiting for heartbeat")
    master.wait_heartbeat()

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

    # Manage waypoints, so we can get the home point
    wp = mavwp.MAVWPLoader()

    #
    # Set glider settings
    #
    # "Glider Pilots: Set this parameter to 2.0 (The glider will adjust its
    # pitch angle to maintain airspeed, ignoring changes in height)."
    #
    # See: http://ardupilot.org/plane/docs/tecs-total-energy-control-system-for-speed-height-tuning-guide.html
    #
    params = mavparm.MAVParmDict()
    params.mavset(master, b'TECS_SPDWEIGHT', 2.0)
    params.mavset(master, b'WP_LOITER_RAD', turnRadius)

    # Request the home point, so we can roughly know how high above our
    # starting point we are
    master.waypoint_request_send(0)

    # Start send/recieve threads
    receive = NetworkingThreadReceive(master, manager, wp, debug)
    send = NetworkingThreadSend(master, manager, wp, debug)
    receive.start()
    send.start()
    receive.join()
    send.join()

    print("Exiting networkingProcess")
