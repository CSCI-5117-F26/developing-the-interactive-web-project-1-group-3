from functools import wraps
from datetime import date
import math
import os
import random
import cloudinary
import cloudinary.uploader
import dotenv
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, session, url_for

import database

from authlib.integrations.flask_client import OAuth

load_dotenv()
cloudinary.reset_config()
cloudinary.config(secure=True)

app = Flask(__name__)
database.setup()

app.secret_key = os.environ["FLASK_SECRET"]
MAX_LISTING_IMAGES = 10


def delete_cloudinary_images(public_ids):
    for public_id in public_ids:
        try:
            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )
        except Exception:
            app.logger.exception(
                "Could not delete Cloudinary image %s",
                public_id,
            )


oauth = OAuth(app)

domain = os.environ["AUTHO_0_DOMAIN"]
client_id = os.environ["AUTH_0_CLIENT_ID"]
client_secret = os.environ["AUTHO_0_CLIENT_SECRET"]

oauth.register(
    "auth0",
    client_id=client_id,
    client_secret=client_secret,
    client_kwargs={
       "scope": "openid profile email",
    },
    server_metadata_url=f"https://{domain}/.well-known/openid-configuration",
)


@app.route("/")
def render_home():
    listings = database.get_first_six()

    return render_template("home.html", listings=listings)


@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/create_listing/", methods=["GET", "POST"])
def create_listing():
    if request.method == "GET":
        return render_template(
            "create_listing.html", google_maps_url=os.environ["GOOGLE_MAPS_URL"]
        )
    else:
        title = request.form.get("title")
        address = request.form.get("address") or ""
        rent = request.form.get("monthly_rent")
        leaseStart = request.form.get("lease_start_date")
        leaseEnd = request.form.get("lease_end_date")
        description = request.form.get("description")

        if not all((title, rent, leaseStart, leaseEnd, description)):
            abort(400, "All listing fields are required.")

        try:
            rent = int(rent)
            parsed_lease_start = date.fromisoformat(leaseStart)
            parsed_lease_end = date.fromisoformat(leaseEnd)
        except (TypeError, ValueError):
            abort(400, "Rent and lease dates must be valid.")

        if rent < 0:
            abort(400, "Monthly rent cannot be negative.")
        if parsed_lease_end < parsed_lease_start:
            abort(400, "End date cannot be earlier than start date.")

        images = [
            image
            for image in request.files.getlist("images")
            if image and image.filename
        ]
        if len(images) > MAX_LISTING_IMAGES:
            abort(400, "A listing can have at most 10 images.")
        if any(
            not image.mimetype or not image.mimetype.startswith("image/")
            for image in images
        ):
            abort(400, "Only image files can be uploaded.")

        uploaded_images = []
        try:
            for image in images:
                result = cloudinary.uploader.upload(
                    image,
                    folder="subleasefinder/listings",
                    resource_type="image",
                )
                uploaded_images.append(
                    {
                        "image_url": result["secure_url"],
                        "public_id": result["public_id"],
                        "alt_text": image.filename,
                    }
                )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not upload listing images")
            abort(502, "One or more images could not be uploaded.")

        try:
            listing = database.add_listing_with_images(
                title,
                address,
                rent,
                leaseStart,
                leaseEnd,
                description,
                uploaded_images,
            )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not save listing and image records")
            abort(500, "The listing could not be saved.")

        return redirect(url_for("listing", listing_id=listing["id"]))


@app.route("/edit_listing/<int:listing_id>/", methods=["GET", "POST"])
def edit_listing(listing_id):
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)

    images = database.get_listing_images(listing_id)

    if request.method == "POST":
        leaseStart = request.form.get("lease_start_date")
        leaseEnd = request.form.get("lease_end_date")
        if date.fromisoformat(leaseEnd) < date.fromisoformat(leaseStart):
            abort(400, "End date cannot be earlier than start date.")

        try:
            delete_image_ids = [
                int(image_id)
                for image_id in request.form.getlist("delete_image_ids")
            ]
        except ValueError:
            abort(400, "Invalid image selection.")

        new_images = [
            image
            for image in request.files.getlist("images")
            if image and image.filename
        ]
        if any(
            not image.mimetype or not image.mimetype.startswith("image/")
            for image in new_images
        ):
            abort(400, "Only image files can be uploaded.")

        delete_ids = set(delete_image_ids)
        remaining_count = sum(image["id"] not in delete_ids for image in images)
        if remaining_count + len(new_images) > MAX_LISTING_IMAGES:
            abort(400, "A listing can have at most 10 images.")

        uploaded_images = []
        try:
            for image in new_images:
                result = cloudinary.uploader.upload(
                    image,
                    folder="subleasefinder/listings",
                    resource_type="image",
                )
                uploaded_images.append(
                    {
                        "image_url": result["secure_url"],
                        "public_id": result["public_id"],
                        "alt_text": image.filename,
                    }
                )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not upload listing images")
            abort(502, "One or more images could not be uploaded.")

        try:
            database.update_listing(
                listing_id,
                request.form.get("title"),
                request.form.get("address"),
                request.form.get("monthly_rent"),
                request.form.get("lease_start_date"),
                request.form.get("lease_end_date"),
                request.form.get("description"),
            )
            removed_public_ids = database.update_listing_images(
                listing_id,
                delete_image_ids,
                uploaded_images,
            )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not update listing images")
            abort(500, "The listing images could not be saved.")

        delete_cloudinary_images(removed_public_ids)
        return redirect(url_for("listing", listing_id=listing_id))

    return render_template("edit_listing.html", item=item, images=images)


@app.route("/favorites/")
def favorites():
    return render_template("favorites.html")


@app.route("/feed/")
def feed():
    listings = database.get_all_listings()
    return render_template("feed.html", listings=listings)


@app.route("/listing/<int:listing_id>/")
def listing(listing_id):
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    images = database.get_listing_images(listing_id)
    return render_template("listing.html", item=item, images=images)


@app.route("/listing/<int:listing_id>/delete/", methods=["POST"])
def delete_listing(listing_id):
    deleted_listing = database.delete_listing(listing_id)
    if deleted_listing is None:
        abort(404)
    delete_cloudinary_images(deleted_listing["image_public_ids"])
    return redirect(url_for("feed"))


@app.route("/callback", methods=["GET", "POST"])
def callback():
    """
    Callback redirect from Auth0
    """
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/messages/")
def messages():
    return render_template("messages.html")


@app.route("/profile/")
def profile():
    return render_template("profile.html")
