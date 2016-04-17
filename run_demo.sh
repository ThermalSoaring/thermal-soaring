#!/bin/bash
#
# Requirements:
#   crrcsim-apm    https://github.com/tridge/crrcsim-ardupilot
#   ardupilot      https://github.com/diydrones/ardupilot
#   mavproxy       https://github.com/Dronecode/MAVProxy
#   mavlink        https://github.com/mavlink/mavlink
#
# Installation:
#   Add '~/.local/bin' to your PATH, so that APM's sim_vehicle.sh script and
#   can find mavproxy.py
#
#   mavlink
#        $ git clone https://github.com/mavlink/mavlink
#
#        Fix issue where it won't import mavexpression:
#        $ sed -i 's/select, mavexpression/select, pymavlink.mavexpression/' \
#              mavlink/pymavlink/mavutil.py
#
#        Add this mavlink/ directory to PYTHONPATH (see export statement below)
#        So that 'import pymavlink' will work, which is included in this mavlink/
#        directory.
#
#   Optional, recreate the mavlink.py file included in this repository:
#        $ python3 -m pymavlink.tools.mavgen -o mavlink --lang Python \
#              --wire-protocol 1.0 ./message_definitions/v1.0/ardupilotmega.xml
#        $ sed -i 's/from ...generator.mavcrc/from pymavlink.generator.mavcrc/' mavlink.py
#        $ cp mavlink.py path/to/repo/
#
#   mavproxy
#        $ sudo pacman -S wxpython opencv
#        $ git clone https://github.com/Dronecode/MAVProxy mavproxy
#        $ cd mavproxy
#        $ python2 setup.py build install --user
#
#   ardupilot
#        $ git clone https://github.com/diydrones/ardupilot
#        Set the APM variable in this script to point to where you cloned this
#
#   crrcsim-apm
#        Install manually or use
#        https://github.com/floft/PKGBUILDs/tree/master/crrcsim-apm
#

# Path to find APM's sim_vehicle.sh script
APM="$HOME/Documents/Github/ThermalSoaring/ardupilot"

# Path so we can import pymavlink for communication
MAVLINK="$HOME/Documents/Github/ThermalSoaring/mavlink"
export PYTHONPATH="$PYTHONPATH:$MAVLINK"

# Configuration
ProxyPort=9999
Script=learning.py

# Kill/interrupt all the processes we started on Ctrl+C
intList=()
killList=()

exiting() {
    echo "Exiting..."

    for i in "${killList[@]}"; do
        kill $i &>/dev/null
    done

    # Otherwise we'll be left with it's child proccesses still running
    mavlink="$(pgrep mavlink.py)"
    [[ -n $mavlink ]] && kill -INT $mavlink

    exit 1
}

trap "exiting" 2 15

# Start the crrcsim simulation
run_simulation() {
    crrcsim -i APM &>/dev/null &
    killList+=("$!")
}

# Start the autopilot
run_autopilot () {
    cd "$APM/Tools/autotest"
    ./sim_vehicle.sh -v ArduPlane -f CRRCSim -j 4 --console --map --out=127.0.0.1:$ProxyPort
}

# Run our code which connects to the MAVProxy ground station started by the
# autopilot script
run_ourcode() {
    xterm -e "python3 \"$Script\"" &
    killList+=("$!")
}

waitline() {
    echo -n "Press enter to continue..."
    read
}

run_simulation

# Display message if not in fast mode
if [[ $1 != "-f" ]]; then
cat <<EOF
In the simulator,
    Options -> Launch -> Load Preset: Motor
    Options -> Airplane -> Select airplane: Sport
    Options -> Wind, Thermals -> adjust as desired
    Press 't' to show thermals
    Press 'r' to reset

Once the simulator starts, this window will become a MAVProxy
shell. Type 'arm throttle' to start flying.

EOF
waitline
fi

run_ourcode
run_autopilot
wait
