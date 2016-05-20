# Setting up APM Plane and CRRCSim

## Installation
### Arch Linux
Add '~/.local/bin' to your PATH, so that APM's _sim\_vehicle.sh_ script and
can find mavproxy.py

##### mavlink
	$ git clone https://github.com/mavlink/mavlink
	$ cd mavlink/pymavlink

Fix issue where it won't import mavexpression:

	$ sed -i 's/select, mavexpression/select, pymavlink.mavexpression/'  mavutil.py
	$ python3 setup.py install --user

Optional: recreate the mavlink.py file included in the _thermal-soaring_ repository:

	$ python3 -m pymavlink.tools.mavgen -o mavlink --lang Python \
		  --wire-protocol 1.0 ./message_definitions/v1.0/ardupilotmega.xml
	$ sed -i 's/from ...generator.mavcrc/from pymavlink.generator.mavcrc/' mavlink.py
	$ cp mavlink.py path/to/repo/

##### mavproxy

	$ sudo pacman -S wxpython opencv
	$ git clone https://github.com/Dronecode/MAVProxy mavproxy
	$ cd mavproxy
	$ python3 setup.py build install --user

Note: OpenCV 3 removed the cv2.cv API, so this breaks all the map functionality
if you use version 3. You could always connect via Mission Planner if you want
a map to look at.

##### ardupilot

	$ git clone https://github.com/diydrones/ardupilot -b ArduPlane-release

Set the APM variable in the simulation script _run\_simulation.sh_ and the live
script _run\_live.sh_ to point to where you cloned this "ardupilot" repository.

##### crrcsim-apm
Install manually or use [my own Arch Linux
PKGBUILD](https://github.com/floft/PKGBUILDs/tree/master/crrcsim-apm)

## Links
* [crrcsim-apm](https://github.com/tridge/crrcsim-ardupilot)
* [ardupilot](https://github.com/diydrones/ardupilot)
* [mavproxy](https://github.com/Dronecode/MAVProxy)
* [mavlink](https://github.com/mavlink/mavlink)
