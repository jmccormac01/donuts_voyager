"""
Script to disable a reference image with Voyager
"""
import argparse as ap
from datetime import datetime
from contextlib import contextmanager
import pymysql

# pylint: disable=invalid-name

def arg_parse():
    """
    Parse the command line arguments
    """
    p = ap.ArgumentParser()
    p.add_argument("field",
                   help="name of field to disable")
    p.add_argument("filter",
                   help="filter of field to disable")
    p.add_argument("xbin",
                   help="x binning level of field to disable")
    p.add_argument("ybin",
                   help="x binning level of field to disable")
    p.add_argument("flip_status",
                   help="flip status of field to disable")
    return p.parse_args()

@contextmanager
def db_cursor(host='127.0.0.1', port=3306, user='donuts',
              password='', db='donuts'):
    """
    Grab a database cursor
    """
    with pymysql.connect(host=host, \
                         port=port, \
                         user=user, \
                         password=password, \
                         db=db) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


if __name__ == "__main__":
    args = arg_parse()

    # set valid until to now, to disable
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qry = """
        UPDATE autoguider_ref
        SET valid_until=%s
        WHERE field=%s
        AND filter=%s
        AND xbin=%s
        AND ybin=%s
        AND flip_status=%s
        """
    qry_args = (now, args.field, args.filter, args.xbin, args.ybin, args.flip_status)

    with db_cursor() as cur:
        cur.execute(qry, qry_args)
