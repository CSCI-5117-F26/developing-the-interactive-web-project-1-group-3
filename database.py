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
        os.environ["DATABASE_URL"], open=False, min_size=4, max_size=20, kwargs={"row_factory": dict_row}
    )
    # I'm not _actually_ convinced this is required, but the docs said to do it!
    atexit.register(pool.close)

def add_listing(title, address, rent, leaseStart, leaseEnd, description):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "insert into listing (title, address, rent, leaseStart, leaseEnd, description) values (%s, %s, %s, %s, %s, %s) returning id;",
            (title, address, rent, leaseStart, leaseEnd, description),
        )
        return curr.fetchone()

def get_first_six():
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "select * from listing order by id limit 6;",
        )
        return curr.fetchall()

def get_all_listings():
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "select * from listing order by id;",
        )
        return curr.fetchall()

def get_listing(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select * from listing where id = %s;",
            (listing_id,),
        )
        return curr.fetchone()

def update_listing(listing_id, title, address, rent, leaseStart, leaseEnd, description):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "update listing set title = %s, address = %s, rent = %s, leaseStart = %s, leaseEnd = %s, description = %s where id = %s;",
            (title, address, rent, leaseStart, leaseEnd, description, listing_id),
        )

def delete_listing(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "delete from listing where id = %s returning id;",
            (listing_id,),
        )
        return curr.fetchone()