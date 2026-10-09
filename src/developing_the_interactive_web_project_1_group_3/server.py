from functools import wraps

from flask import Flask, render_template, request, session, redirect, url_for
import math
import os
import database
import random
from authlib.integrations.flask_client import OAuth


app = Flask(__name__)
database.setup()

@app.route("/")
def hello_world():
    
    return render_template("home.html")


@app.route("/chat")
def chat():
    return render_template( "chat.html")




@app.route("/create_listing/")
def create_listing():
    return render_template( "create_listing.html")

@app.route("/edit_listing/")
def edit_listing():
    return render_template( "edit_listing.html")



@app.route("/favorites/")
def favorites():
    return render_template( "favorites.html")



@app.route("/feed/")
def feed():
    return render_template( "feed.html")

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



