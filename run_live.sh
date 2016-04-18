#!/bin/bash
#
# Connect our thermal soaring program to the real APM:Plane autopilot over the
# USB telemetry radio
#
# Setup: look at run_simulation.sh
#

# Path to find APM's sim_vehicle.sh script
APM="../ardupilot"

# Configuration
ProxyPort=2050
Script="soaring.py"

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

# Start the autopilot
run_mavproxy() {
    mavproxy.py --console --map --master=/dev/ttyUSB0 --out=127.0.0.1:$ProxyPort
}

# Run our code which connects to the MAVProxy ground station started by the
# autopilot script
run_ourcode() {
    xterm -e "python3 \"$Script\"" &
    killList+=("$!")
}

run_ourcode
run_mavproxy
wait
