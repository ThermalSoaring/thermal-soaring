Thermal Soaring
---------------
Our goal with this project is to autonomously mimic the soaring habits of
birds, in particular their aptitude for finding what we know of as "thermals"
in the atmosphere. These thermals are locations where warm air is rising, and
with a sufficiently large thermal, orbiting inside it can allow a bird or
glider to gain altitude without flapping its wings or using its motor.

To complete this task we separated into two teams: one mechanical oriented team
to create a glider light and yet robust enough to find and take advantage of
these thermals, and a second more computer oriented team to add thermal soaring
capability to current autopilots.

This is the code for the computer side of the project. The complete solution
for working with the Pixhawk is provided here and the Python side of the
Piccolo solution as well (the C++ portion is currently not online since the
Piccolo is not open-source).

**Note:** see *docs/* for more documentation.

# Pixhawk / APM Plane
To connect to the USB telemetry radio for live flight:

    ./run_live.sh

or, to run APM Plane in a crrcsim simulation:

    ./run_simulation.sh

# Piccolo
To connect to the C++ code that connects to the Piccolo for both simulation
and for live flight:

    python3 soaring.py -d
