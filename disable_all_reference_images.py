"""
Script to disable all reference images with Voyager
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
    p.add_argument("--all",
                   help="add flag to confirm disabling all",
                   action='store_true')
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
    if args.all:
        # set valid until to now, to disable
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qry = """
            UPDATE autoguider_ref
            SET valid_until=%s
            WHERE valid_until IS NULL
            """
        qry_args = (now,)
        with db_cursor() as cur:
            cur.execute(qry, qry_args)
    else:
        print("Re-run with --all flag to confirm you want to disable them all")
