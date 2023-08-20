# Change Log
All notable changes to this project after 2023-07-31 will be documented in this file.

## [0.1.0] - In development

Major non-backward compatible changes

### Added

- Support for boolean masking of bad pixels. A full frame mask fits file must be created and stored in the DonutsCalibration folder and the filename added to the config.toml. See below
- Added support for GEM mounts and GEM mount calibration parameters
- Added reporting of calibration parameters is a copy/paste-able format for easier enabling of calibration results
- Added new config.toml parameters
   - ```xsize_keyword```: fits header keyword for image size in X
   - ```ysize_keyword```: fits header keyword for image size in Y
   - ```xorigin_keyword```: fits header keyword for image subframe origin in X direction
   - ```yorigin_keyword```: fits header keyword for image subframe origin in Y direction
   - ```full_frame_boolean_mask_file```: name of the boolean mask file. Delete this entry if you don't want masking. This file is assumed to be in the ```calibration_root_host``` folder
   - ```calibration_filter_index```: the Voyager index for the filter to use during calibration. Use a broadband filter for best results
   - ```calibration_binning```: binning level in both X and Y for the calibration routine. For extremely large detectors consider binning of 2 or 3 during calibration and observations for increased performance. Binning of 1 is fine for detectors of few k times few k pixels.
   - ```mount_type```: Options are ```GEM``` and ```FORK```. See the ```README.md``` for notes on calibration either mount type.
- Added scripts for managing reference images
- Added much more information to README on calibrating etc

### Changed

- Voyager socket reading now gives up after 10 failed tries to avoid infinite spamming of empty strings
- Database schema has been updated to include the new reference image characteristics above (x/ysize and x/yorigin)
- Python requirements file to include newer packages

### Fixed

- Issue with calibration binning and filter being hard coded
- Issue with guide corrections not rescaling if binning science images
