"""
Functions for interacting with donuts/voyager
database. Used for storing reference images etc
"""
from datetime import datetime
from contextlib import contextmanager
import logging
import pymysql
import os


@contextmanager
def db_cursor(host=os.environ['DB_HOST'], port=3306, user='donuts',
              password='', db='donuts'):
    """
    Grab a database cursor
    """
    with pymysql.connect(host=host,
                         port=port,
                         user=user,
                         password=password,
                         db=db) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def get_reference_image_path(field, filt, xbin, ybin):
    """
    Look in the database for the current
    field/filter reference image

    Parameters
    ----------
    field : string
        name of the current field
    filt : string
        name of the current filter
    xbin : int
        level of image binning in x direction
    ybin : int
        level of image binning in y direction

    Returns
    -------
    ref_image : string
        path to the reference image
        returns None if no reference image found

    Raises
    ------
    None
    """
    tnow = datetime.utcnow().isoformat().split('.')[0].replace('T', ' ')
    qry = """
        SELECT ref_image_path
        FROM autoguider_ref
        WHERE field = %s
        AND filter = %s
        AND xbin = %s
        AND ybin = %s
        AND valid_from < %s
        AND valid_until IS NULL
        """
    qry_args = (field, filt, xbin, ybin, tnow)

    with db_cursor() as cur:
        cur.execute(qry, qry_args)
        result = cur.fetchone()
        logging.debug(f"DB: {qry}")
        logging.debug(f"DB: {qry_args}")

    if not result:
        ref_image = None
    else:
        ref_image = result[0]
    return ref_image


def set_reference_image(ref_image_path, field, filt, xbin, ybin):
    """
    Set a new image as a reference in the database

    Parameters
    ----------
    field : string
        name of the current field
    filt : string
        name of the current filter
    ref_image : string
        name of the image to set as reference
    xbin : int
        level of image binning in x direction
    ybin : int
        level of image binning in y direction

    Returns
    -------
    None

    Raises
    ------
    """
    tnow = datetime.utcnow().isoformat().split('.')[0].replace('T', ' ')
    qry = """
        INSERT INTO autoguider_ref
        (ref_image_path, field, filter, xbin, ybin, valid_from)
        VALUES
        (%s, %s, %s, %s, %s, %s)
        """
    qry_args = (ref_image_path, field, filt, xbin, ybin, tnow)
    with db_cursor() as cur:
        cur.execute(qry, qry_args)
        logging.debug(f"DB: {qry}")
        logging.debug(f"DB: {qry_args}")


def log_shifts_to_db(qry_args):
    """
    Log the autguiding information to the database

    Parameters
    ----------
    qry_args : array like
        Tuple of items to log in the database.
        See itemised list in logShiftsToFile docstring

    Returns
    -------
    None

    Raises
    ------
    None
    """
    qry = """
        INSERT INTO autoguider_log
        (ref_image_path, comp_image_path, stabilised, shift_x, shift_y,
         pre_pid_x, pre_pid_y, post_pid_x, post_pid_y, final_x, final_y,
         std_buff_x, std_buff_y, culled_max_shift_x, culled_max_shift_y)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s, %s, %s, %s)
        """
    with db_cursor() as cur:
        cur.execute(qry, qry_args)
        logging.debug(f"DB: {qry}")
        logging.debug(f"DB: {qry_args}")


def print_last_log():
    qry = """
                SELECT *
                FROM autoguider_log
                ORDER BY updated DESC
                LIMIT 1
                """

    with db_cursor() as cur:
        cur.execute(qry)
        result = cur.fetchone()
        print(result)
