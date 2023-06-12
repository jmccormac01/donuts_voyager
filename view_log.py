"""
Script to view donuts log between two times
"""
import sys
import argparse as ap
from contextlib import contextmanager
import pymysql

# pylint: disable=invalid-name

def arg_parse():
    """
    Parse the command line arguments
    """
    p = ap.ArgumentParser()
    p.add_argument("--t1",
                   help="start time of log view",
                   type=str)
    p.add_argument("--t2",
                   help="end time of log view",
                   type=str)
    p.add_argument("--last",
                   help="view last X entries instead of supplying times",
                   type=int)
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

    if args.last_x:
        qry = """
            SELECT *
            FROM autoguider_log
            ORDER BY updated DESC
            LIMIT %s
            """
        qry_args = (args.last_x, )

    elif args.t1 and args.t2:
        qry = """
            SELECT *
            FROM autoguider_log
            WHERE updated > %s AND updated < %s
            ORDER BY updated DESC
            """
        qry_args = (args.t1, args.t2)

    else:
        print("Supply either --last X or --t1 YYYY-MM-DD HH:mm:ss --t2 YYYY-MM-DD hh:mm:ss")
        sys.exit(1)

    with db_cursor() as cur:
        cur.execute(qry, qry_args)
        results = cur.fetchall()

    # print the results
    for result in results:
        print(result)
