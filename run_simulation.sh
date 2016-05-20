#!/bin/bash
#
# Connect our thermal soaring program to APM:Plane in crrcsim, a simulator
#
# Setup: look at docs/PixhawkSimulation.md
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
    xterm -e "python3 \"$Script\" -d" &
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
    Options -> Airplane -> Select airplane: Flexifly XLM
    Options -> Wind, Thermals -> adjust as desired
    Press 't' to show thermals
    Press 'r' to reset

Once the simulator starts, this window will become a MAVProxy
shell. Type the following to start flying after you get some
messages in the Console about EXF2 IMU0.

    wp load ArduPlane-Missions/CMAC-toff-loop.txt
    arm throttle
    mode auto

EOF
waitline
fi

run_ourcode
run_autopilot
wait
