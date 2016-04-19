# Piccolo Setup on Windows
This document will describe how to set up the Piccolo simulator, how to setup
our C++ application, how to setup the Python side, and how to setup the
Pixhawk.

## Piccolo Simulator Setup
The Piccolo simulator supports thermal simulation, which will be very useful
for getting our project to work without the added complexity of testing it only
in a real environment.

### Installation
On the Google drive you'll find two installers (you don't need the multirotor
one since we're simulating a fixed-wing):

    Piccolo/Piccolo-2.2.3.b.R19774/Piccolo-Installer.r19774.msi
    Piccolo/Piccolo-2.2.3.b.R19774/Piccolo-Installer-Developer.r19774.msi

### Running the Simulator with Thermals
Run `Piccolo 2.2.3.b/SoftwareSimLauncher.bat`

When Piccolo Command Center (PCC) starts, go to File --> License Manager and add
a file. Use the *Piccolo/WallaWalla-License.xml* file.

## Visual Studio Project Setup
The Piccolo software includes libraries that can be linked against with the
Visual Studio 2008 C++ compiler, but not any other. Thus, we need to use this
old version of Visual Studio to work with the simulator. This means that we'll
be limited to C++ functionality that was available in 2008.

### Download the C++ Thermal Soaring code

    git clone https://bitbucket.org/wwuthermalsoaring/thermal-soaring

### Install Visual C++ 2008 Express
This is needed since the Piccolo's CommSDK dll's are compiled with Visual
Studio 2008 and we need to use the same compiler so we can link against them.  
[Visual Studio 2008 download](https://go.microsoft.com/?linkid=7729279)

Then, since you can't register it anymore, crack it (????):  
[Stackoverflow](http://stackoverflow.com/a/30540370)

### Download Boost for Boost threading, since we can't use C++11 thread as 2008 < 2011
##### Download the msvc-9.0-32.exe and install somewhere, e.g. C:\boost\_1\_60\_0
[Direct 32-bit download](https://sourceforge.net/projects/boost/files/boost-binaries/1.60.0/boost_1_60_0-msvc-9.0-32.exe/download)  
[Sourceforge binaries](https://sourceforge.net/projects/boost/files/boost-binaries/1.60.0/)

##### Downloading RapidJSON
Extract somewhere, e.g. to C:\rapidjson-1.0.2  
[Rapid JSON 1.0.2](https://github.com/miloyip/rapidjson/archive/v1.0.2.zip)  
[All Rapid JSON releases](https://github.com/miloyip/rapidjson/releases)

### Adding paths/libraries to Visual Studio
##### Add environment variables:

    BOOST=C:\boost_1_60_0
    RAPIDJSON=C:\rapidjson-1.0.2

##### Right click on the project --> Properties --> Configuration Properties --> C/C++ --> Additional Include Directories:

    $(BOOST);$(RAPIDJSON)\include;

##### Right click on the project --> Properties --> Configuration Properties --> Linker --> Additional Library Directories:

    $(BOOST)\lib32-msvc-9.0; 

# Python Setup

The GPR and Reinforcement Learning algorithms have been developed using Python,
a higher-level language than C++ that allows for easier and faster development
and prototyping. The easiest way to set this all up on Windows is using
Anaconda as explained below.

### Setting up Anaconda for Python 3.5 and many Python libraries
##### Download and install the Python 3.5 compiler for Windows 64-bit:

[Download](https://www.continuum.io/downloads)

##### Install additional packages:

    conda install seaborn

##### Getting the Python Thermal Soaring code
After starting the Piccolo simulator and the C++ side of the C++/Python
interface, which includes the server, you can start the Python client that will
connect and run the GPR thermal identification:

    git clone https://github.com/ThermalSoaring/thermal-soaring
    cd thermal-soaring

Next, in the Visual Studio project, change the arguments when running the
program. Right click on the project --> Properties --> Configuration Properties
--> Debugging --> Command Arguments: -a gpr. This will then listen on a port
that the Python code can connect to.

Connect the Python code to the Visual Studio project by running:

    python soaring.py -p -d

Not for use with the simulator, but if you want to see the notebook code in a
browser in the *bayesian-learning* git repository:

    cd bayesian-learning
    jupyter notebook

##### Making PyMC3 Work
This is not required to run when using GPR live with the simulator, but it is
required to run the GPR and Bayesian parameter estimation comparisons. If you
are interested in that:

    pip install --process-dependency-links git+https://github.com/pymc-devs/pymc3
    cd thermal-soaring/identification
    python offline.py

Note: Theano will be slow (it'll print a warning about this when you run it)
since it needs g++ installed, but in order to build and link against Python it
needs the same g++ that was used to compile Anaconda. Guess what? Anaconda used
Visual Studio 2015 to compile Python, not g++. 
