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
    p = ap.ArgumentParser("Disable reference images")
    p.add_argument("field",
                   help="name of field to disable")
    p.add_argument("--filter",
                   help="filter of field to disable")
    p.add_argument("--xbin",
                   help="x binning level of field to disable")
    p.add_argument("--ybin",
                   help="x binning level of field to disable")
    p.add_argument("--xsize",
                   help="Image size x of field to disable")
    p.add_argument("--ysize",
                   help="Image size y of field to disable")
    p.add_argument("--xorigin",
                   help="Image x origin of field to disable")
    p.add_argument("--yorigin",
                   help="Image y origin of field to disable")
    p.add_argument("--flip_status",
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
    qry = f"UPDATE autoguider_ref\nSET valid_until='{now}'\nWHERE field='{args.field}'\n"

    errors = 0

    # check for filter
    if args.filter is None:
        print("Must specify a filter or % for all filters")
        errors += 1
    elif args.filter == "%":
        qry = qry + "AND filter LIKE '%'\n"
    else:
        qry = qry + f"AND filter='{args.filter}'\n"
    # check for xbin
    if args.xbin is None:
        print("Must specify an xbin or % for all x binning levels")
        errors += 1
    elif args.xbin == "%":
        qry = qry + "AND xbin LIKE '%'\n"
    else:
        qry = qry + f"AND xbin={args.xbin}\n"
    # check for ybin
    if args.ybin is None:
        print("Must specify a ybin or % for all y binning levels")
        errors += 1
    elif args.ybin == "%":
        qry = qry + "AND ybin LIKE '%'\n"
    else:
        qry = qry + f"AND ybin={args.ybin}\n"
    # check for xsize
    if args.xsize is None:
        print("Must specify an xsize or % for all x sizes")
        errors += 1
    elif args.xsize == "%":
        qry = qry + "AND xsize LIKE '%'\n"
    else:
        qry = qry + f"AND xsize={args.xsize}\n"
    # check for ysize
    if args.ysize is None:
        print("Must specify a ysize or % for all y sizes")
        errors += 1
    elif args.ysize == "%":
        qry = qry + "AND ysize LIKE '%'\n"
    else:
        qry = qry + f"AND ysize={args.ysize}\n"
    # check for xorigin
    if args.xorigin  is None:
        print("Must specify an xorigin or % for all x origins")
        errors += 1
    elif args.xorigin== "%":
        qry = qry + "AND xorigin LIKE '%'\n"
    else:
        qry = qry + f"AND xorigin={args.xorigin}\n"
    # check for yorigin
    if args.yorigin is None:
        print("Must specify a yorigin or % for all y origins")
        errors += 1
    elif args.yorigin == "%":
        qry = qry + "AND yorigin LIKE '%'\n"
    else:
        qry = qry + f"AND yorigin={args.yorigin}\n"
    # check for flip status
    if args.flip_status is None:
        print("Must specify a flip_status or % for all flip statuses")
        errors += 1
    elif args.flip_status == "%":
        qry = qry + "AND flip_status LIKE '%'\n"
    else:
        qry = qry + f"AND flip_status={args.flip_status}\n"

    if errors > 0:
        print("\nFIX ISSUES ABOVE AND RE-RUN THE COMMAND\n")
    else:
        print(qry)
        with db_cursor() as cur:
            cur.execute(qry)
