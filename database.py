import atexit
import os

import dotenv
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

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
            (title, address, rent, leaseStart, leaseEnd, description),
        )
        return curr.fetchone()


def add_listing_with_images(
    title,
    address,
    rent,
    leaseStart,
    leaseEnd,
    description,
    images,
):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            """
            insert into listing
                (title, address, rent, leaseStart, leaseEnd, description)
            values (%s, %s, %s, %s, %s, %s)
            returning id;
            """,
            (title, address, rent, leaseStart, leaseEnd, description),
        )
        listing = curr.fetchone()

        for display_order, image in enumerate(images):
            curr.execute(
                """
                insert into listing_images
                    (listing_id, image_url, public_id, alt_text, display_order)
                values (%s, %s, %s, %s, %s);
                """,
                (
                    listing["id"],
                    image["image_url"],
                    image["public_id"],
                    image["alt_text"],
                    display_order,
                ),
            )

        return listing


def get_first_six():
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "select * from listing order by id limit 6;",
        )
        return curr.fetchall()


def get_all_listings():
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "select * from listing order by id;",
        )
        return curr.fetchall()


def get_listing(listing_id):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select * from listing where id = %s;",
            (listing_id,),
        )
        return curr.fetchone()


def get_listing_images(listing_id):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            """
            select id, listing_id, image_url, public_id, alt_text, display_order
            from listing_images
            where listing_id = %s
            order by display_order, id;
            """,
            (listing_id,),
        )
        return curr.fetchall()


def update_listing(listing_id, title, address, rent, leaseStart, leaseEnd, description):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "update listing set title = %s, address = %s, rent = %s, leaseStart = %s, leaseEnd = %s, description = %s where id = %s;",
            (title, address, rent, leaseStart, leaseEnd, description, listing_id),
        )


def update_listing_images(listing_id, delete_image_ids, new_images):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select id, public_id from listing_images where listing_id = %s;",
            (listing_id,),
        )
        existing = curr.fetchall()
        delete_ids = set(delete_image_ids)
        removed = [image for image in existing if image["id"] in delete_ids]

        if removed:
            curr.execute(
                "delete from listing_images where listing_id = %s and id = any(%s);",
                (listing_id, [image["id"] for image in removed]),
            )

        curr.execute(
            """
            select coalesce(max(display_order), -1) as max_order
            from listing_images
            where listing_id = %s;
            """,
            (listing_id,),
        )
        display_order = curr.fetchone()["max_order"] + 1
        for image in new_images:
            curr.execute(
                """
                insert into listing_images
                    (listing_id, image_url, public_id, alt_text, display_order)
                values (%s, %s, %s, %s, %s);
                """,
                (
                    listing_id,
                    image["image_url"],
                    image["public_id"],
                    image["alt_text"],
                    display_order,
                ),
            )
            display_order += 1

        return [image["public_id"] for image in removed]


def delete_listing(listing_id):
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select public_id from listing_images where listing_id = %s;",
            (listing_id,),
        )
        public_ids = [image["public_id"] for image in curr.fetchall()]

        curr.execute(
            "delete from listing where id = %s returning id;",
            (listing_id,),
        )
        deleted_listing = curr.fetchone()
        if deleted_listing is None:
            return None
        return {
            "id": deleted_listing["id"],
            "image_public_ids": public_ids,
        }
