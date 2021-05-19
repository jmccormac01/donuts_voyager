"""
Utility functions for Donuts and Voyager
"""
import os
from datetime import (
    date,
    timedelta,
    datetime)

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

# get tonights directory
def get_data_dir(root_dir, data_subdir=""):
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
    token = get_am_or_pm()
    d = date.today()-timedelta(days=token)
    night = "{:d}{:02d}{:02d}".format(d.year, d.month, d.day)
    night_str = "{:d}-{:02d}-{:02d}".format(d.year, d.month, d.day)
    data_loc = "{}\\{}".format(root_dir, night)
    # adds capability for data to live in folders
    # inside the nightly folder, as for saintex
    if data_subdir != "":
        data_loc = f"{data_loc}\\{data_subdir}"
    if not os.path.exists(data_loc):
        os.mkdir(data_loc)
    return data_loc, night_str
