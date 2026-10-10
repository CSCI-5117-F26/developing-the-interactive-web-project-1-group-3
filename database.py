from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
import dotenv
from dotenv import load_dotenv
import os
import atexit

load_dotenv()

pool = None

def setup():
    global pool
    # note use of `[]` over `.get()` is intentional here. I want a hard-and-fast crash if environment is not setup right.
    pool = ConnectionPool(
        os.environ["DATABASE_URL"], open=True, kwargs={"row_factory": dict_row}
    )
    # I'm not _actually_ convinced this is required, but the docs said to do it!
    atexit.register(pool.close)

def add_listing(title, address, rent, leaseStart, leaseEnd, description):
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "insert into listing (title, address, rent, leaseStart, leaseEnd, description) values (%s, %s, %s, %s, %s, %s) returning id;",
            (title, address, rent, leaseStart, leaseEnd, description)
        )
        return curr.fetchone()


# Implement DB functions