# Setting up the Pixhawk Hardware

While we are using the Piccolo for simulation, we decided to go with the
Pixhawk for actual flight. We have a Piccolo Nano, but after sending data to
Michael at CloudCap during the 2014-2015 school year, he thought there might be
hardware issues with it, and it is primarily designed for quadcopter flight
anyway. We also have a Piccolo SL, which we got since for the 2014-2015 project
with the Vertical Take-Off and Landing UAV, we needed to use version 2.1.4,
which didn't run on the Nano. This can be used for fixed-wing flight. However,
the wiring harness has very long wires (not ideal for a lightweight glider) and
also doesn't bring out the CAN bus, which is needed for hardware-in-the-loop.
In addition, for autonomous flight we might need to create an AVL model. In
other words, getting the Piccolo up and running seems like it would be a lot
more complex and time consuming than using the Pixhawk, and we used the Pixhawk
last year for similar reasons. It's really simple to set up.

### Pixhawk Overview
[Overview](http://ardupilot.org/plane/docs/common-pixhawk-overview.html)

### Physical Installation
##### Connecting the Telemetry Radio:
[3DR Radio Docs](http://ardupilot.org/copter/docs/common-3dr-radio-v1.html)

* Plug it into the Telem 1 port on the Pixhawk

##### Connecting the pitot tube / airspeed sensor
[px4airspeed](https://pixhawk.org/peripherals/sensors/px4airspeed)  
[Calibrating Airspeed Sensor](http://ardupilot.org/plane/docs/calibrating-an-airspeed-sensor.html)

##### Driver for Windows, if you plug in the USB live telemetry radio into the computer:
[ftdichip driver](http://www.ftdichip.com/Drivers/D2XX.htm)

* Install the latest one for Windows

##### Wiring the servos and motor
[Wiring and Quick Start](http://ardupilot.org/plane/docs/common-pixhawk-wiring-and-quick-start.html)

* Not the white background with black text but the white text on black background:
    * Pin 1 = Aileron
    * Pin 2 = Elevator
    * Pin 3 = Throttle
    * Pin 4 = Rudder

##### Connecting Futaba receiver to the Pixhawk:
[RC Transmitter/Receiver](http://ardupilot.org/copter/docs/common-pixhawk-and-px4-compatible-rc-transmitter-and-receiver-systems.html)

* 1 goes to 1, etc.
* Don't plug anything into the one by 3 with a red background that looks like a
  B
* Signal goes up (i.e. the white wires), the side with the text

### Computer Software and Pixhawk Firmware Setup
##### Install Mission Planner on the PC:
[Mission Planner Download](http://ardupilot.com/downloads/?did=82)

##### Install firmware on the Pixhawk:
[Loading Firmware](http://ardupilot.org/planner/docs/common-loading-firmware-onto-pixhawk.html)

### Calibration
[First time APM Setup](http://ardupilot.org/plane/docs/first-time-apm-setup.html)

* Accelerometer
    * Whatever you do, do not use the wizard! If you do, an accelerometer
      calibration window will keep coming up that doesn't work. (Though, you
      could just close it if it does keep coming up. But, it might fail to
      calibrate if you use that window.) You want to do the normal
      accelerometer calibration under Mandatory Hardware.
* Radio calibration
* Set ALL flight modes to manual

### Failsafe
[APM Failsafe](http://ardupilot.org/plane/docs/apms-failsafe-function.html)

* The ideal: turn motor off and put servos to level flight.
* Make sure the short and long failsafe functions are disabled.
* What actually happens if you turn off the controller with the throttle up and
  servos turned: the motor will shut off but the servos will stay where they
  were.

### Arming, checking the servos
[Arming the Motors](http://ardupilot.org/copter/docs/arming_the_motors.html)

* Take motor prop off, but make sure ESC is powered since it'll power the
servos, providing +5 V on the Pixhawk servo rail.
* Hold down red blinking button attached to Pixhawk for a couple seconds till
it is a solid red, first step in arming
* Hold Yaw and throttle down and to the right for second stage of arming
* If when you try the second stage of arming it spews error messages in Mission
Planner's top left flight data window, then you can allow arming anyway if you
set ARMING_CHECK = 0 to get around GPS fix required, etc. However, you likely
won't get good data if you do this. If you have a Bad AHRS error, then our only
solution we've found so far is just to wait (if you want good data from the
logs). Eventually it went away.

### Setting data to log
* Set LOG_BITMASK to 65535 in the Full Parameter List, to log everything when
  Armed

### After flight, analysis
[Common Analysis](http://ardupilot.org/planner/docs/common-mission-analysis.html)
[Downloading Data Logs](http://ardupilot.org/copter/docs/common-downloading-and-analyzing-data-logs-in-mission-planner.html)

* Take out the microsd card from the Pixhawk
* Plug into computer
* Go into APM/LOGS/ and copy the last log onto your computer (or, make sure you
  have write permission where the file is since it'll be creating a file with
  the same name but with a .log extension)
* In Mission Planner, under Flight Data --> DataFlash Logs --> PX4 .Bin to .Log
  --> Find file Then, Flight Data --> DataFlash Logs --> Review Log to plot the
  flight path, look at data, etc.

##### To interpret data:
[EKF2 Navigation System](http://ardupilot.org/dev/docs/ekf2-navigation-system.html)

* NKF1-NKF4 are first IMU
* NKF6-NKF9 are second, if enabled

In Mission Planner, there is also a "Create Matlab File" option. This will take
the .bin files from the microSD card and output a .mat file. In Matlab,

    d = load('152.log-775945.mat');

The labels for the columns, e.g.:

    d.GPS_label

The actual data, e.g.:

    d.GPS

There's a lot of other data there as well. GPS is probably useful as is EKF6,
which contains velocities in the north, east, and down directions. There is a
GPS "Spd" term, which may be an interesting velocity term.

Note: remember to put the SD card *back* into the glider!
