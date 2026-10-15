from functools import wraps 
from flask import Flask, abort, render_template, request, session, redirect, url_for
import database
import math
import os
import dotenv
from dotenv import load_dotenv
import random
from authlib.integrations.flask_client import OAuth

load_dotenv()

print("0")

app = Flask(__name__)
database.setup()

print("1")

app.secret_key = os.environ["FLASK_SECRET"]

print("2")

oauth = OAuth(app)

print("3")

domain = os.environ["AUTHO_0_DOMAIN"]
client_id = os.environ["AUTH_0_CLIENT_ID"]
client_secret = os.environ["AUTHO_0_CLIENT_SECRET"]

print("4")

oauth.register(
    "auth0",
    client_id=client_id,
    client_secret=client_secret,
    client_kwargs={
       "scope": "openid profile email",
    },
    server_metadata_url=f"https://{domain}/.well-known/openid-configuration",
)

print("ClientID: " + str(client_id) + "Client Secret: " + str(client_secret) + "Domain: " + str(domain))

@app.route("/")
def render_home():
    listings = database.get_first_six()

    return render_template("home.html", listings=listings)

@app.route("/chat")
def chat():
    return render_template( "chat.html")

@app.route("/create_listing/", methods=["GET", "POST"])
def create_listing():
    if request.method == 'GET':
        return render_template( "create_listing.html", google_maps_url=os.environ['GOOGLE_MAPS_URL'])
    else:
        title = request.form.get("title")
        address = request.form.get("address")
        rent = request.form.get("monthly_rent")
        leaseStart = request.form.get("lease_start_date")
        leaseEnd = request.form.get("lease_end_date")
        description = request.form.get("description")

        database.add_listing(title, address, rent, leaseStart, leaseEnd, description)
        listings = database.get_first_six()
        return render_template("home.html", listings=listings)

@app.route("/edit_listing/<int:listing_id>/", methods=["GET", "POST"])
def edit_listing(listing_id):
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)

    if request.method == "POST":
        database.update_listing(
            listing_id,
            request.form.get("title"),
            request.form.get("address"),
            request.form.get("monthly_rent"),
            request.form.get("lease_start_date"),
            request.form.get("lease_end_date"),
            request.form.get("description"),
        )
        return redirect(url_for("listing", listing_id=listing_id))

    return render_template("edit_listing.html", item=item)

@app.route("/favorites/")
def favorites():
    return render_template( "favorites.html")

@app.route("/feed/")
def feed():
    listings = database.get_all_listings()
    return render_template("feed.html", listings=listings)

@app.route("/listing/<int:listing_id>/")
def listing(listing_id):
    item = database.get_listing(listing_id)
    if item is None:
        abort(404)
    return render_template("listing.html", item=item)


@app.route("/listing/<int:listing_id>/delete/", methods=["POST"])
def delete_listing(listing_id):
    deleted_listing = database.delete_listing(listing_id)
    if deleted_listing is None:
        abort(404)
    return redirect(url_for("feed"))


#@app.route("/callback", methods=["GET", "POST"])
#def callback():
#    """
#    Callback redirect from Auth0
#   """
#    token = oauth.auth0.authorize_access_token()
#    session["user"] = token
#    return redirect("/")


#@app.route("/login")
#def login():
#    return oauth.auth0.authorize_redirect(
#        redirect_uri=url_for("callback", _external=True)
#    )


@app.route("/messages/")
def messages():
    return render_template( "messages.html")

@app.route("/profile/")
def profile():
    return render_template( "profile.html")



