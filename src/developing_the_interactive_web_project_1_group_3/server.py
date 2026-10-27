from gevent import monkey
monkey.patch_all()
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
from authlib.integrations.base_client.errors import OAuthError
from urllib.parse import quote_plus, urlencode
from flask_socketio import SocketIO, emit, join_room

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
    username = database.get_username(id)
    if username:
        return username
    else:
        return None

def check_user_conversation(conversation_id, user_id):
    conversation = database.get_conversation(conversation_id)

    if not conversation:
        return False

    return ((conversation["user1_id"] == user_id) or (conversation["user2_id"] == user_id))

def get_user_convo_list(user_id):
    conversations = database.get_all_conversations(user_id)
    list = []

    for conversation in conversations:
        list.append({"id": conversation["id"], "listing_title": conversation["listing_title"]})

    return list



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
        "home.html", listings=listings, name=name, user_id=str(user_id), google_home_map_url=os.environ["GOOGLE_HOME_MAP_URL"],
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

        if not user_id:
                return redirect("/login")

        title = request.form.get("title")
        address = request.form.get("address")
        location = request.form.get("location")
        rent = request.form.get("monthly_rent")
        leaseStart = request.form.get("lease_start_date")
        leaseEnd = request.form.get("lease_end_date")
        description = request.form.get("description")
        if not all((title, address, location, rent, leaseStart, leaseEnd, description)):
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
                location,
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
        name = getUserName(user_id)

    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    if item["owner_id"] != str(user_id):
        abort(403)

    images = database.get_listing_images(listing_id)

    if request.method == "POST":
        title = request.form.get("title")
        address = request.form.get("address")
        location = request.form.get("location")
        rent = request.form.get("monthly_rent")
        description = request.form.get("description")
        leaseStart = request.form.get("lease_start_date")
        leaseEnd = request.form.get("lease_end_date")

        if not all((title, address, rent, leaseStart, leaseEnd, description)):
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
                title,
                address,
                location,
                rent,
                leaseStart,
                leaseEnd,
                description,
            )
            removed_public_ids = database.update_listing_images(
                listing_id,
                delete_image_ids,
                uploaded_images,
            )
        except Exception:
            delete_cloudinary_images(image["public_id"] for image in uploaded_images)
            app.logger.exception("Could not update listing")
            abort(500, "The listing could not be updated.")

        delete_cloudinary_images(removed_public_ids)
        return redirect(url_for("listing", listing_id=listing_id))

    return render_template("edit_listing.html", item=item, images=images, name=name, google_maps_url=os.environ["GOOGLE_MAPS_URL"])



@app.route("/favorites/")
def favorites():
    user_id = getUserID()
    if not user_id:
        return redirect("/login")
    name = getUserName(user_id)
    listings = database.get_favorites(user_id)
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
        "feed.html", listings=listings, name=name, user_id=str(user_id), google_home_map_url=os.environ["GOOGLE_HOME_MAP_URL"]
    )

@app.route("/search")
def search():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    search_inp=request.args.get("q","")

    max_rent=request.args.get("max_rent", "")
    min_rent=request.args.get("min_rent", "")
    move_in=request.args.get("move_in", "")
    move_out=request.args.get("move_out", "")


    if max_rent:
        try:
            max_rent=int(max_rent)
        except ValueError:
            abort(400,"Maxium rent must be a whole number")
        if max_rent<0:
            abort(400,"Maxium rent cannot be a negative number")
    else:
        max_rent=None

    if min_rent:
        try:
           min_rent=int(min_rent)
        except ValueError:
            abort(400,"Minimum rent must be a whole number")
        if min_rent<0:
            abort(400,"Minimum rent cannot be a negative number")
    else:
        min_rent=None
    if move_in:
        try:
            move_in = date.fromisoformat(move_in)
        except ValueError:
            abort(400, "Invalid move-in date.")
    else:
        move_in = None
    if move_out:
        try:
            move_out = date.fromisoformat(move_out)
        except ValueError:
            abort(400, "Invalid move-out date.")
    else:
        move_out = None
    if min_rent is not None and max_rent is not None:
        if min_rent > max_rent:
            abort(400, "Minimum rent cannot exceed maximum rent.")

    if move_in is not None and move_out is not None:
        if move_out < move_in:
            abort(400, "Move-out cannot be before move-in.")
    


    listings=database.search_listings(search_inp,
    min_rent=min_rent,
    max_rent=max_rent,
    move_in=move_in,
    move_out=move_out,)
    return render_template(
        "feed.html", listings=listings, name=name,min_rent=min_rent,
        max_rent=max_rent,
        move_in=move_in,
        move_out=move_out, user_id=str(user_id), search_inp=search_inp, google_home_map_url=os.environ["GOOGLE_HOME_MAP_URL"]
    )

@app.route("/dist-filter")
def dist_filter():
    user_id = getUserID()
    if user_id:
        name = getUserName(user_id)
    else:
        name = "Guest"
    location = request.args.get("location", "")
    distance = request.args.get("distance", type=int)
    address = request.args.get("address", "")
    if not location or distance not in (1, 3, 5, 10, 25):
        abort(400, description="Invalid location or distance")
    listings = database.search_by_distance(location, distance)
    return render_template(
        "feed.html",
        listings=listings,
        name=name,
        user_id=str(user_id),
        search_inp=address,
        search_mode="distance",
        google_home_map_url=os.environ["GOOGLE_HOME_MAP_URL"]
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
    saved = database.is_favorite(user_id, listing_id) if user_id else False
    return render_template(
        "listing.html",
        item=item,
        images=images,
        saved=saved,
        name=name,
        user_id=str(user_id),
    )



@app.route("/listing/<int:listing_id>/favorite/", methods=["POST"])
def favorite_listing(listing_id):
    user_id = getUserID()
    if not user_id:
        return redirect("/login")
    name = getUserName(user_id)
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    database.add_favorite(user_id, listing_id)
    flash("Saved to Favorites")
    return redirect(url_for("listing", listing_id=listing_id, name=name))


@app.route("/listing/<int:listing_id>/unfavorite/", methods=["POST"])
def unfavorite_listing(listing_id):
    user_id = getUserID()
    if not user_id:
        return redirect("/login")
    name = getUserName(user_id)
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    database.remove_favorite(user_id, listing_id)
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
    if listing["owner_id"] != str(user_id):
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
    try:
        token = oauth.auth0.authorize_access_token()
    except OAuthError:
        message = "Unable to Login"
        return redirect(url_for("fourOfour", message=message))
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
@app.route("/messages/", defaults={"conversation_id": None})
@app.route("/messages/<string:conversation_id>/")
def messages(conversation_id):
    user_id = getUserID()
    if not user_id:
        return redirect("/login")

    conversations = get_user_convo_list(user_id)
    messages = []

    if conversation_id is not None:
        if not check_user_conversation(conversation_id, user_id):
            message = "You aren't a part of this conversation!"
            return redirect(url_for("fourOfour", message=message))
        
        messages = database.get_messages(conversation_id)
        for message in messages:
            message["sender_name"] = getUserName(message["sender_id"])

    name = getUserName(user_id)

    return render_template("messages.html", name=name, user_id=str(user_id), conversation_id=conversation_id, conversations=conversations, messages=messages)

@app.route("/404/")
def fourOfour():
    message = request.args.get("message")
    return render_template("404.html", message=message)


@app.route("/profile/")
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

    listing = database.get_listing(listing_id)

    if not listing:
        return redirect("/404")

    owner_id = listing.get("owner_id")

    if owner_id is None:
        message = "This listing has no owner"
        return redirect(url_for("fourOfour", message=message))

    owner_id = int(owner_id)

    if user_id == owner_id:
        message = "You can't Message yourself!"
        return redirect(url_for("fourOfour", message=message))

    user1_id = min(user_id, owner_id)
    user2_id = max(user_id, owner_id)

    conversation_id = database.get_or_create_conversation(listing_id, user1_id, user2_id)

    return redirect(url_for("messages", conversation_id=conversation_id))


@socketio.on("join_conversation")
def handle_join_conversation(data):
    user_id = getUserID()

    if not user_id:
        return {"error": "Please Login First"}

    try:
        conversation_id = int(data.get("conversation_id"))
    except (TypeError, ValueError):
        message = "Bad Conversation ID"
        return redirect(url_for("fourOfour", message=message))

    if not check_user_conversation(conversation_id, user_id):
        message = "You Don't have Access to this Conversation"
        return redirect(url_for("fourOfour", message=message))
    
    join_room(str(conversation_id))

    return {"success": True}


@socketio.on("new_message")
def handle_send_message(data):
    user_id = getUserID()

    if not user_id:
        return redirect("/login")

    if not isinstance(data, dict):
            message = "Bad data format"
            return redirect(url_for("fourOfour", message=message))

    try:
        conversation_id = int(data.get("conversation_id"))
    except (TypeError, ValueError):
        message = "Bad Conversation ID"
        return redirect(url_for("fourOfour", message=message))

    message = data.get("message")

    if not isinstance(message, str) or not message:
        message = "Bad message format"
        return redirect(url_for("fourOfour", message=message))

    if len(message) > 2000:
        message = "Message Way too Long"
        return redirect(url_for("fourOfour", message=message))

    if not check_user_conversation(conversation_id, user_id):
        message = "You Don't have Access to this Conversation"
        return redirect(url_for("fourOfour", message=message))

    saved_message = database.save_message(conversation_id, user_id, message)

    emit("chat", {
        "conversation_id": conversation_id,
        "sender_id": int(user_id),
        "username": getUserName(user_id) or "Anonymous User",
        "message": saved_message["message"]
    }, to=str(conversation_id))

    return {"success": True}

    
    






    
