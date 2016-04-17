import time
from threading import Thread

import mavlink
from pymavlink import mavutil

class GroundStation:
    def __init__(self, device):
        # Connect to MAVProxy ground station
        self.master = mavutil.mavlink_connection(device)

        # Wait for a heartbeat so we know the target system IDs
        print("Waiting for heartbeat")
        self.master.wait_heartbeat()

        # Do we need to get the parameters?
        #self.master.param_fetch_all()

        # Set that we want to receive data
        print("Requesting data")
        self.master.mav.request_data_stream_send(
                self.master.target_system,
                self.master.target_component,
                mavlink.MAV_DATA_STREAM_ALL, 4, 1)

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

        # Start receiving messages in the background
        print("Starting to receive data")
        self.exiting = False
        self.listenThread = Thread(target=self.receive_messages)
        self.listenThread.start()

    # Exit background thread on close
    def exit(self):
        self.exiting = True
        self.listenThread.join()

    # Receive incoming mavlink messages from the groundstation
    def receive_messages(self):
        while not self.exiting:
            msg = self.master.recv_match(blocking=True)

            if not msg:
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
            #else:
            #    print(msg)

    def __repr__(self):
        return("Bat %d AirV %f Alt: %f Lat: %f Lon: %f Vz: %f WindV: %f WindVZ: %f Temp: %f" % (
            self.battery, self.airspeed, self.alt, self.lat, self.lon,
            self.vz, self.wind_speed, self.wind_speed_z, self.temperature))

    def header(self):
        return("Roll, Pitch, Yaw, RollSpeed, PitchSpeed, YawSpeed, AirSpeed, GroundSpeed, Heading, Throttle, Alt, Timestamp, Timeboot, PressureAbs, PressureDiff, Temperature, Battery, WindDirection, WindSpeed, WindSpeedZ, Lat, Lon, Vx, Vy, Vz")
        #return("Roll*100, Pitch*100, Yaw*100, RollSpeed*100, PitchSpeed*1000, YawSpeed*1000, AirSpeed, GroundSpeed, Heading, Throttle, Alt, Timestamp, Timeboot, PressureAbs, PressureDiff, Temperature, Battery, WindDirection, WindSpeed*10, WindSpeedZ, Lat, Lon, Vx, Vy, Vz")

    def __str__(self):
        return(', '.join([str(i) for i in [self.roll, self.pitch, self.yaw, self.rollspeed, self.pitchspeed, self.yawspeed, self.airspeed, self.groundspeed, self.heading, self.throttle, self.alt, self.timestamp, self.timeboot, self.pressure_abs, self.pressure_diff, self.temperature, self.battery, self.wind_direction, self.wind_speed, self.wind_speed_z, self.lat, self.lon, self.vx, self.vy, self.vz]]))
        #return(', '.join([str(int(round(i))) for i in [self.roll*100, self.pitch*100, self.yaw*100, self.rollspeed*100, self.pitchspeed*1000, self.yawspeed*1000, self.airspeed, self.groundspeed, self.heading, self.throttle, self.alt, self.timestamp, self.timeboot, self.pressure_abs, self.pressure_diff, self.temperature, self.battery, self.wind_direction, self.wind_speed*10, self.wind_speed_z, self.lat, self.lon, self.vx, self.vy, self.vz]]))

if __name__ == "__main__":
    s = GroundStation('localhost:9999')
    filename = "simulation.csv"

    try:
        # Wait till armed
        print("Waiting for motors to be armed")
        s.master.motors_armed_wait()

        # Set to auto so we take off
        print("Setting mode to auto")
        s.master.set_mode_auto()

        # TODO: send waypoints

        with open(filename, "w+") as f:
            f.write(s.header()+'\n')

        with open(filename, "a+") as f:
            while True:
                f.write(str(s)+'\n')
                print(repr(s))
                time.sleep(1)

    except KeyboardInterrupt:
        print("Exiting...")
        s.exit()
