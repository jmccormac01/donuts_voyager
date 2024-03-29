# Donuts with Voyager

An event driven version of Donuts using the Voyager observatory control system

# Contents

Below is a short description of each file in this repository

   1. ```CHANGELOG.md``` quick summary of recent changes to voyager donuts
   1. ```docker_configs``` example docker config files for various installations
   1. ```donuts_configs``` example donuts config files for various installations
   1. ```testing``` scripts used in development of donuts for voyager. Not generally useful
   1. ```.gitignore``` things to ignore from version control
   1. ```PID.py``` code for autoguiding PID control loop
   1. ```README.md``` this file
   1. ```disable_all_reference_images.py``` helper script to disable all references in MySQL database
   1. ```disable_reference_image.py``` helper script to disable one particular reference in MySQL database
   1. ```mysql-init.sql``` MySQL script to build initial database tables
   1. ```requirements.txt``` Python module requirements for donuts
   1. ```view_log.py``` helper script to view donuts log in MySQL database
   1. ```voyager_db.py``` donuts database functionality
   1. ```voyager_donuts.py``` main donuts script for autoguiding via voyager
   1. ```voyager_utils.py``` helper functions for donuts


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
      1. Copy the example ```james_test.toml``` file and edit the top section to set the paths to the data and FITS keywords etc
      1. Ensure that the final line of the ```Dockerfile``` is pointed at this new config file
      1. Set the ```calibration_filter_index``` to the filter position (0, 1, ... N_filters) you'd like to use for calibration. A broadband optical filter is suggested.
      1. Set the ```calibration_binning``` level. For very large sensors a binning factor of 2 or 3 is suggested. For most small format devices (e.g. 1k x 1k or 2k x 2k) binning of 1 is fine.
      1. Set the ```ra_axis``` to ```x``` or ```y``` depending on the orientation of your camera.
      1. Set the telescope ```mount_type``` to ```FORK``` or ```GEM```.
      1. The ```guide_directions``` and ```pixels_to_time``` lines will be set after the initial on-sky calibration run
   1. Build the Docker image for Donuts/Voyager
      1. Simply double click the ```start.bat``` file and the images will be built. Donuts will be left running. Double click the ```stop.bat``` if you wish to stop donuts
      1. Assuming all went well, we now have docker images for MySQL and for Donuts. Next step is calibrating the guide routine.


# Rebuilding the Donuts Docker Image

After the initial installation, you may need to rebuild the Donuts Docker image (e.g. there is an update to the code). To do so:

   1. Ensure Docker Desktop is running
   1. Type ```cmd``` in the windows search bar to bring up a terminal
   1. Navigate to the ```voyager_donuts``` folder on your PC:
      1. e.g. ```cd C:\Users\jmcc\Documents\Github\donuts_voyager```
   1. Rebuild the image:
      1. ```docker build -t voyager_donuts .```
   1. Wait for that to complete. You should see a new image appear in Docker Desktop.


# Rebuilding the Complete Donuts and MySQL Docker Environment

After major upgrades to Donuts, the MySQL database schema might change. This means that both the code and the reference image database need rebuilding.
This is much simpler than the initial setup above. To do a complete rebuild:

   1. In GitHub Desktop, pull the latest version of the code (check correct branch for development features)
   1. Check the ```donuts_configs/james_test.toml``` file to look for new donuts config parameters
   1. As of 2023-07-31 a ```CHANGELOG.md``` file is included, this will outline any new config parameters
   1. Add new entries to your config file with suitable parameters (e.g. new corresponding fits header keywords or calibration parameters)
   1. In Docker Desktop:
      1. In the containers tab, stop any running containers and delete them
      1. In the images tab, delete the ```voyager_donuts``` and ```db``` images
      1. In the volumes tab, delete the ```mysql``` volume
      1. This will invalidate the long term reference image storage. New references will be taken during the next observation sequence.
   1. Run the ```start.bat``` script. This will rebuild both images and apply all upgrades
   1. Run the ```stop.bat``` script, if you do not want to continue observing right now.
   1. If there have been no changes to the telescope hardware then you DO NOT need to redo the calibration process.


# Manually Running Donuts

You can manually start and stop donuts by simply double clicking the ```start.bat``` and ```stop.bat``` in the ```donuts_voyager``` repository. Manual starting/stopping is required during calibration (described below)

# Calibrating Donuts

Below are steps required to calibrate donuts. The results from the calibration run must be manually entered into the donuts ```*.toml``` config file.
Calibration is required initially for new systems and then again only if something changes in the hardware (e.g. you remove and reinstall the camera or collimate the telescope).

Autoguiding works via the ```pulseGuide``` command. This simulates pressing a button on the telescope hand paddle in one of 4 directions at the guiding rate for a number of X milliseconds (don't ask me why...).
We therefore must calibrate both the direction of the correction and the ratio of ms/pix for each direction. This is automated using the Donuts Calibration routine. However, the results from a calibration run
must be added manually to the config file. This is on purpose while I figure out the robustness of this proceedure.

## Calibrating Fork Mounts

Below are steps to calibrate a fork mount.

   1. Use Voyager to point the telescope 1h east of the meridian at 0 degrees declination
   1. Start the mount tracking
   1. Start the donuts docker container using the ```start.bat``` script
   1. In Voyager's on the fly section click the 'Donuts Calibration' button and click 'Yes'
   1. The config parameters ```calibration_filter_index``` and ```calibration_binning``` allow you to select which filter ID (0, 1, ... N_filters) and binning level to apply during calibration.
   1. Donuts will command voyager to take a series of images, stepping the mount in N, S, E and W directions between each image
   1. It will then analyse the images taken and determine the orientation of the camera and the magnitude of autoguiding impulses required
   1. A results file will be output to the ```voyager_calbration``` path on the HOST machine.
   1. Directions are quoted as 0, 1, 2 and 3 and are mapped to +x, -x, +y and -y.
   1. Similarly each direction has a calibrated ms/pixels value.
   1. If the calibration run is successful, a pair of lines are written to the results file that can be copied directly into the .toml file.
      1. These lines start ```pixels_to_time = ...``` and ```guide_directions = ...```.
      1. Replace both corresponding lines in the .toml template with the calibrated info.
   1. If the calibration fails, these lines are skipped and you must look at the reported directions and scales to determine the issue.

## Calibrating German Equatorial Mounts

The steps for a GEM are the same as above, but repeated once for 1h east of the meridian and again 1h west of the meridian.
Each calibration run will produce a pair of lines to enter into the .toml config file:

   1. For East calibration:
      1. ```guide_directions_east``` and ```pixels_to_time_east```
   1. For West calibration:
      1. ```guide_directions_west``` and ```pixels_to_time_west```

Be sure to remove or comment out ```guide_directions``` and ```pixels_to_time``` (without directional suffixes). These parameters are used for fork mounts only.

# Running Donuts Automatically

Voyager can start and stop donuts by calling the ```start.bat``` and ```stop.bat``` scripts that we configured in the Installation section above. This is done by:

   1. Add a call to an external script before an observing sequence. Point the external call at the ```start.bat``` script inside the ```donuts_voyager``` repository
   1. To automatically stop donuts after an observing sequence, add an external script call after the observing block. Point the external call at the ```stop.bat``` script in the ```donuts_voyager``` repository

# Managing Reference Images

If anything in your telescope changes (e.g. you remove and reinstall your camera), the long term reference images become invalid. Additionally, if a bad reference image is taken (e.g. a plane flies through the image), you will want to disable that reference.
There are two helper scripts to simplify managing reference images in the MySQL database. One quickly disables a selection of reference images (potentially a single reference) and the other disables all reference images. Below are instructions on using each.

## Disable a Single Reference Image

This script takes many arguments to target a subset or even a single reference image in the database. It can also take the wildcard symbol ```%``` to select multiple matching entries. See below for examples.

   1. Open a terminal inside the ```voyager_donuts``` running container in Docker Desktop
   1. Run ```python disable_reference_image.py -h``` to see the help file
   ```
▶ python disable_reference_image.py -h
usage: Disable reference images [-h] [--filter FILTER] [--xbin XBIN] [--ybin YBIN]
                                [--xsize XSIZE] [--ysize YSIZE] [--xorigin XORIGIN]
                                [--yorigin YORIGIN] [--flip_status FLIP_STATUS]
                                field

positional arguments:
  field                 name of field to disable

options:
  -h, --help            show this help message and exit
  --filter FILTER       filter of field to disable
  --xbin XBIN           x binning level of field to disable
  --ybin YBIN           x binning level of field to disable
  --xsize XSIZE         Image size x of field to disable
  --ysize YSIZE         Image size y of field to disable
  --xorigin XORIGIN     Image x origin of field to disable
  --yorigin YORIGIN     Image y origin of field to disable
  --flip_status FLIP_STATUS
                        flip status of field to disable
   ```
   1. A value is required for each input in order to target the correct reference image(s).
   1. However, you can supply a wildcard value ```%``` to match all values of a given parameter.
   1. For example:
      1. To disable all reference images for field "SP101" regardless of filter, binning etc
      1. ```python disable_reference_image.py SP101 --filter % --xbin % --ybin % --xsize % --ysize % --xorigin % --yorigin % --flip_status %```
      1. To disable all R band reference images for "SP101" regardless of the binning/windowing parameters:
      1. ```python disable_reference_image.py SP101 --filter R --xbin % --ybin % --xsize % --ysize % --xorigin % --yorigin % --flip_status %```
   1. To avoid accidental removal of references you must specify something for each parameter.
   1. For reference, a copy of the mysql command is printed to screen before execution. e.g.
   ```
 python disable_reference_image.py SP101 --filter % --xbin % --ybin % --xsize % --ysize % --xorigin % --yorigin % --flip_status %

 UPDATE autoguider_ref
 SET valid_until='2023-07-31 13:52:08'
 WHERE field='SP101'
 AND filter LIKE '%'
 AND xbin LIKE '%'
 AND ybin LIKE '%'
 AND xsize LIKE '%'
 AND ysize LIKE '%'
 AND xorigin LIKE '%'
 AND yorigin LIKE '%'
 AND flip_status LIKE '%'
   ```

## Disable All Reference Images

If a hardware change has invalidated all reference images, they can be disbaled using the following:

   1. Open a terminal inside the ```voyager_donuts``` running container in Docker Desktop
   1. Run ```python disable_all_reference_images.py --all``` to disable all reference images
   1. Note, the ```--all``` is needed to confirm you want to do this (potentially dangerous) activity

# Contributors

James McCormac

# License

MIT License

Copyright (c) 2023 James McCormac

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
