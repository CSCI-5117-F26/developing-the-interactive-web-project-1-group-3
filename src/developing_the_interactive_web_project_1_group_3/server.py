from datetime import date
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
import database
from authlib.integrations.flask_client import OAuth
from urllib.parse import quote_plus, urlencode
from flask_socketio import SocketIO, emit

load_dotenv()
cloudinary.reset_config()
cloudinary.config(secure=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
database.setup()
socketio = SocketIO()

app.secret_key = os.environ["FLASK_SECRET"]
socketio.init_app(app)
MAX_LISTING_IMAGES = 10

def getUserID():
    user = session.get("user")
    if user:
        userinfo = user.get("userinfo")
        if userinfo:
            auth0sub = userinfo.get("sub")
        else: 
            return None
    else:
        return None

    name = "Unknown User"
    if userinfo and userinfo.get("name"):
        name = userinfo.get("name")
    userID = database.get_or_create_user_id(auth0sub, name)
    return userID

def getUserName(id):
    username = database.getUsername(id)
    if username:
        return username
    else:
        return None


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
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"

    return render_template(
        "home.html", listings=listings, name=name, user_id=user_id
    )


@app.route("/chat")
def chat():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    
    return render_template("chat.html", name=name)


@app.route("/create_listing/", methods=["GET", "POST"])
def create_listing():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    
    if request.method == "GET":
        return render_template(
            "create_listing.html", google_maps_url=os.environ["GOOGLE_MAPS_URL"], name=name
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
                user_id,
            )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not save listing and image records")
            abort(500, "The listing could not be saved.")

        return redirect(url_for("listing", listing_id=listing["id"], name=name))

@app.route("/edit_listing/<int:listing_id>/", methods=["GET", "POST"])
def edit_listing(listing_id):
    user_id = getUserID()
    if user_id:
        name = getUserName()

    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    if item["owner_id"] != user_id:
        abort(403)

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

    return render_template("edit_listing.html", item=item, images=images, name=name)


@app.route("/favorites/")
def favorites():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    listings = database.get_favorites()
    return render_template("favorites.html", listings=listings, name=name)


@app.route("/feed/")
def feed():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    listings = database.get_all_listings()
    return render_template(
        "feed.html", listings=listings, name=name, user_id=user_id
    )

@app.route("/search")
def search():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    search_inp=request.args.get("q","")
    listings=database.search_listings(search_inp)
    return render_template(
        "feed.html", listings=listings, name=name, user_id=user_id,search_inp=search_inp
    )



    





@app.route("/listing/<int:listing_id>/")
def listing(listing_id):
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    images = database.get_listing_images(listing_id)
    saved = database.is_favorite(listing_id)
    return render_template(
        "listing.html",
        item=item,
        images=images,
        saved=saved,
        name=name,
        user_id=user_id,
    )



@app.route("/listing/<int:listing_id>/favorite/", methods=["POST"])
def favorite_listing(listing_id):
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    database.add_favorite(listing_id)
    flash("Saved to Favorites")
    return redirect(url_for("listing", listing_id=listing_id, name=name))


@app.route("/listing/<int:listing_id>/unfavorite/", methods=["POST"])
def unfavorite_listing(listing_id):
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    database.remove_favorite(listing_id)
    flash("Removed from Favorites")
    return redirect(url_for("listing", listing_id=listing_id, name=name))


@app.route("/listing/<int:listing_id>/image/")
def listing_image(listing_id):
    image = database.get_listing_image(listing_id)
    if image is None:
        abort(404)
    return Response(
        image["image_data"],
        mimetype=image["image_mimetype"],
        headers={"X-Content-Type-Options": "nosniff"},
    )

@app.route("/listing/<int:listing_id>/delete/", methods=["POST"])
def delete_listing(listing_id):
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    listing = database.get_listing(listing_id)
    if listing is None:
        abort(404)
    if listing["owner_id"] != user_id:
        abort(403)

    deleted_listing = database.delete_listing(listing_id)
    if deleted_listing is None:
        abort(404)
    delete_cloudinary_images(deleted_listing["image_public_ids"])
    return redirect(url_for("feed", name=name))


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

@app.route("/logout")
def logout():
    """
    Logs the user out of the session and from the Auth0 tenant
    """
    session.clear()
    return redirect(
        "https://" + domain
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("render_home", _external=True),
                "client_id": client_id,
            },
            quote_via=quote_plus,
        )
    )
@app.route("/messages", defaults={"conversation_id": None})
@app.route("/messages/<int:conversation_id>")
def messages(conversation_id):
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"

    if conversation_id:
        owner, self = conversation_id.split("+")
        if user_id == self:
            print("access")
        else:
            print("No Access")

    return render_template("messages.html", name=name)

@app.route("/404")
def fourOfour():
    return render_template("404.html")


@app.route("/profile")
def profile():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    return render_template("profile.html", name=name)


@app.route("/message_owner/<int:listing_id>", methods=["POST"])
def message_owner(listing_id):
    user_id = getUserID()

    if not user_id:
        return redirect("/login")

    listing = database.getlisting(listing_id)

    if not listing:
        return redirect("/404")

    listing_id = listing["owner_id"]

    if user_id == listing_id:
        return redirect("/404")

    conversation_id=str(listing_id) + "+" + str(user_id)

    return redirect(url_for("messages", conversation_id=conversation_id))

    

