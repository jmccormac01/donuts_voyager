# Donuts with Voyager

Initial scribbles to have an event driven version of donuts

# Installation

To simplify the installation process of Donuts and MySQL, everything is containerised using Docker.
Docker depends on the Windows Subsystem for Linux (WSL2.0) and this is only available on Windows 10.

   1. Install WSL2.0
      1. Open powershell as admin
      1. Run ```wsl --install -d Ubuntu```
      1. Enter a default username/password when prompted for the Ubuntu installation. For simplicity, copying the windows credentials is advisable.
      1. Once installed, restart the PC
   1. Install Docker desktop on your control PC
   1. Install Github desktop on youe control PC
   1. Clone the ```donuts_voyager``` git repository
      1. The repository can be found at ```https://github.com/jmccormac01/donuts_voyager```
      1. Where you store the git repository is important, as some files in the repo will need editing to point to this location (see below)
   1. Inside the ```voyager_donuts``` repository we need to edit several files as part of the installation.
   1. There are two config directories, one with Docker config (```docker_configs```) and one with Donuts config (```donuts_config```), let's start by editing the Docker config for a new system:
   1. Copy the following files from the ```docker_configs``` folder up one level into the main ```voyager_donuts``` folder:
      1. From the ```voyager_donuts``` folder run:
      1. ```cp docker_configs/Dockerfile_example Dockerfile```
      1. ```cp docker_configs/docker-compose_example.yml docker-compose.yml```
      1. ```cp docker_configs/start_example.bat start.bat```
      1. ```cp docker_configs/stop_example.bat stop.bat```
      1. Each of these files will need editing for new installations
   1. Edit the ```docker-compose.yml``` file to set the following information for your system:
      1. Volume paths in the ```docker-compose.yml``` have the format ```<host_path>:<container_path>```
      1. The ```db``` container paths should be fine as their default values
      1. You should ensure that the host paths configured in the ```voyager_donuts``` container exist and are correct:
         1. There are 4 paths that must be configured, they are discussed in turn below:
         1. Host path to ```voyager_calibration```. This folder is used to store data for the calibration of donuts
         1. Host path to ```voyager_log```. This folder contains logs from donuts if logging to disc is enabled
         1. Host path to ```voyager_data```. This folder contains nightly data files. Data for a given night is assumed to be in a folder titled ```YYYY-MM-DD``` within this folder
         1. Host path to ```voyager_reference```. This folder stores the reference images for long term guiding stability.
      1. Edit the ```docker-compose.yml``` file timezone information so the container has the correct local time configured:
         1. Edit the lines ```TZ: "<TIMEZONE>"``` to set your local timezone.
         1. Note there is a ```TZ:``` for each container (```db``` and ```voyager_donuts```)
         1. Names of timezones can be found [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) in the ```TZ database name``` column
   1. Edit the ```Dockerfile``` and set the following for your system:
      1. Make the timezone section to match the timezone entered in the ```docker-compose.yml``` file.
      1. In the final line set the path to the correct Donuts config file in the ```donuts_configs``` folder
   1. In order to start and stop donuts from Voyager automatically, do the following:
      1. Edit the ```start.bat``` and ```stop.bat``` scripts
      1. Enter the path to the ```donuts_voyager``` repository on line 1 of each script
      1. In Voyager's drag script interface, you can add a call to external scripts to point at ```start.bat``` and ```stop.bat``` at the beginning and end of an observing sequence, respectively
   1. Setting the MySQL root password:
      1. For security reasons, the MySQL database root password is not stored on github. Do the following to set a root password:
      1. ```cd /path/where/donuts/lives```
      1. ```mkdir secrets/```
      1. ```cd secrets/```
      1. Create a file called ```mysql_root``` with no file extension
      1. Inside that file save the desired root password.
      1. This root password file should not be commited to any git repository.
      1. Anything in the ```secrets/``` folder is automatically excluded from version control in the ```.gitignore``` file
      1. Once you've memorised the root password and have built donuts (see below) and ran it a few times (see further below), you should delete the ```secrets/mysql_root``` file.
   1. Next we need to edit the donuts config file for our new system:
      1. Copy the ```example.toml``` file and edit the top section to set the paths to the data and FITS keywords etc
      1. Ensure that the final line of the ```Dockerfile``` is pointed at this new config file
      1. The calibration values in the middle section will be set after the initial on-sky calibration run
   1. Build the Docker image for Donuts/Voyager
      1. ```docker build -t voyager_donuts .```

# Running Donuts Automatically

Voyager can start and stop donuts by calling the ```start.bat``` and ```stop.bat``` scripts that we configured in the Installation section above. This is done by:

   1. Add a call to an external script before an observing sequence. Point the external call at the ```start.bat``` script inside the ```donuts_voyager``` repository
   1. To automatically stop donuts after an observing sequence, add an external script call after the observing block. Point the external call at the ```stop.bat``` script in the ```donuts_voyager``` repository

# Manually Running Donuts

You can manually start and stop donuts by simply double clicking the ```start.bat``` and ```stop.bat``` in the ```donuts_voyager``` repository

# Contributors

James McCormac

# License

MIT License

Copyright (c) 2021 James McCormac

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the ???Software???), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED ???AS IS???, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
