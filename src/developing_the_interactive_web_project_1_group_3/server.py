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