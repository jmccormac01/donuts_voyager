"""
Utility functions for Donuts and Voyager
"""
import os
from datetime import (
    date,
    timedelta,
    datetime)
from tomlkit import parse, dumps


def load_config(filename):
    """
    Load the config file

    Parameters
    ----------
    filename : string
        Name of the configuration file to load

    Returns
    -------
    configuration : dict
        Configuration information

    Raises
    ------
    None
    """

    f = open(filename, "r")
    data = f.read()
    f.close()
    return parse(data)


def save_config(data, filename):
    """
    Load the config file

    Parameters
    ----------
    data : basestring
        data of the configuration

    filename : string
        Name of the configuration file to load

    Returns
    -------

    Raises
    ------
    None
    """
    f = open(filename, "w")
    f.write(dumps(data))
    f.close()


# get evening or morning
def get_am_or_pm():
    """
    Determine if it is morning or afteroon

    This function uses now instead of utcnow because
    it is the local time which determines if we are
    starting or ending the curent night.

    A local time > midday is the evening
    A local time < midday is the morning of the day after
    This is not true for UTC in all places

    Parameters
    ----------
    None

    Returns
    -------
    token : int
        0 if evening
        1 if morning

    Raises
    ------
    None
    """
    now = datetime.now()
    if now.hour >= 12:
        token = 0
    else:
        token = 1
    return token


def get_tonight():
    """
    Get tonight's date in YYYY-MM-DD format
    """
    token = get_am_or_pm()
    d = date.today()-timedelta(days=token)
    night = "{:d}-{:02d}-{:02d}".format(d.year, d.month, d.day)
    return night


# get tonights directory
def get_data_dir(root_dir, windows=True):
    """
    Get tonight's data directory and night string

    If directory doesn't exist make it

    Parameters
    ----------
    root_dir : string
        the path to the data directory
    data_subdir : stringsubdir inside nightly folder

    Returns
    -------
    data_loc : string
        Path to tonight's data directory

    Raises
    ------
    None
    """
    night = get_tonight()
    if windows:
        data_loc = f"{root_dir}\\{night}"
    else:
        data_loc = f"{root_dir}/{night}"
    if not os.path.exists(data_loc):
        os.mkdir(data_loc)
    return data_loc
