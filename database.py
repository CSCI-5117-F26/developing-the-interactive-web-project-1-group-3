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
        os.environ["DATABASE_URL"], open=False, min_size=4, max_size=20, kwargs={"row_factory": dict_row}
    )
    # I'm not _actually_ convinced this is required, but the docs said to do it!
    atexit.register(pool.close)

def add_listing(
    title, address, rent, leaseStart, leaseEnd, description,
    image_data=None, image_mimetype=None, owner_id=None,
):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            "insert into listing (title, address, rent, leaseStart, leaseEnd, description, image_data, image_mimetype, owner_id) values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id;",
            (
                title, address, rent, leaseStart, leaseEnd, description,
                image_data, image_mimetype, owner_id,
            ),
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
    owner_id=None,
):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            """
            insert into listing
                (title, address, rent, leaseStart, leaseEnd, description, owner_id)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning id;
            """,
            (title, address, rent, leaseStart, leaseEnd, description, owner_id),
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
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            """
            select listing.*, (
                select image_url
                from listing_images
                where listing_id = listing.id
                order by display_order, id
                limit 1
            ) as preview_image_url
            from listing
            order by id
            limit 6;
            """,
        )
        return curr.fetchall()


def get_all_listings():
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            """
            select listing.*, (
                select image_url
                from listing_images
                where listing_id = listing.id
                order by display_order, id
                limit 1
            ) as preview_image_url
            from listing
            order by id;
            """,
        )
        return curr.fetchall()




def search_listings(search_inp):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        # A smarter Daniel would be validating the inputs here.
        # psycopg doesn't like "mixed" type lists so we cast the sound to 20 floats
        curr.execute(
            """
            select listing.*, (
                select image_url
                from listing_images
                where listing_id = listing.id
                order by display_order, id
                limit 1
            ) as preview_image_url
            from listing
            WHERE title ILIKE %s

            order by id;
            """,
            ("%"+search_inp+"%",)

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

def get_listing_image(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select image_data, image_mimetype from listing where id = %s and image_data is not null;",
            (listing_id,),
        )
        return curr.fetchone()

def get_listing_images(listing_id):
    pool.open()
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
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "update listing set title = %s, address = %s, rent = %s, leaseStart = %s, leaseEnd = %s, description = %s where id = %s;",
            (title, address, rent, leaseStart, leaseEnd, description, listing_id),
        )


def update_listing_images(listing_id, delete_image_ids, new_images):
    pool.open()
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
    pool.open()
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

def add_favorite(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            """
            insert into favorite (listing_id)
            values (%s)
            on conflict (listing_id) do nothing;
            """,
            (listing_id,),
        )

def get_favorites():
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            """
            select listing.*, (
                select image_url
                from listing_images
                where listing_id = listing.id
                order by display_order, id
                limit 1
            ) as preview_image_url
            from favorite
            join listing on listing.id = favorite.listing_id
            order by favorite.id;
            """
        )
        return curr.fetchall()

def is_favorite(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select id from favorite where listing_id = %s;",
            (listing_id,),
        )
        return curr.fetchone() is not None


def remove_favorite(listing_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "delete from favorite where listing_id = %s;",
            (listing_id,),
        )

def get_or_create_user_id(auth0_id, name):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "insert into users (auth0_id, name) "
            "values (%s, %s) "
            "on conflict (auth0_id) "
            "do update set name = excluded.name "
            "returning id",
            (auth0_id, name,),
        )
        return curr.fetchone()["id"]


def get_username(id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
            curr.execute(
                "select name from users where id = %s",
                (id,),
            )
            return curr.fetchone()["name"]

def get_or_create_conversation(listing_id, userOne, userTwo):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
                curr.execute(
                    "select id from conversations " \
                    "where listing_id = %s "
                    "and user1_id = %s "
                    "and user2_id = %s",
                    (listing_id, userOne, userTwo),
                )

                conversation = curr.fetchone()

                if conversation:
                    return conversation["id"]
                else:
                    curr.execute(
                        "insert into conversations " \
                        "(listing_id, user1_id, user2_id) "
                        "values (%s, %s, %s) "
                        "returning id",
                        (listing_id, userOne, userTwo),
                    )
                    return curr.fetchone()["id"]
                
def get_conversation(conversation_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
                curr.execute(
                    "select * from conversations where id = %s",
                    (conversation_id,),
                )
                return curr.fetchone()


def get_all_conversations(user_id):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select * from conversations " \
            "where user1_id = %s or user2_id = %s",
            (user_id, user_id),
        )
        return curr.fetchall()

def get_messages(conversation_id):
     pool.open()
     with pool.connection() as conn, conn.cursor() as curr:
        curr.execute(
            "select * from messages " \
            "where conversation_id = %s "
            "order by id asc",
            (conversation_id,),
        )
        return curr.fetchall()

def save_message(conversation_id, sender_id, message):
    pool.open()
    with pool.connection() as conn, conn.cursor() as curr:
            curr.execute(
                "insert into messages (conversation_id, sender_id, message)" \
                "values (%s, %s, %s)"
                "returning *",
                (conversation_id, sender_id, message),
            )
            return curr.fetchone()
     




