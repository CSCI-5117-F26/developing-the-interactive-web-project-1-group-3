from flask import Flask, render_template, request, session, redirect, url_for
import database
import math
import os
import random


app = Flask(__name__)
database.setup()

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
        return render_template( "create_listing.html")
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

@app.route("/edit_listing/")
def edit_listing():
    return render_template( "edit_listing.html")

@app.route("/favorites/")
def favorites():
    return render_template( "favorites.html")

@app.route("/feed/")
def feed():
    listings = database.get_all_listings()
    return render_template("feed.html", listings=listings)

@app.route("/listing/")
def listing():
    return render_template( "listing.html")

@app.route("/login/")
def login():
    return render_template( "login.html")

@app.route("/messages/")
def messages():
    return render_template( "messages.html")

@app.route("/profile/")
def profile():
    return render_template( "profile.html")



