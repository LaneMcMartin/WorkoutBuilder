import os

from cs50 import SQL
import sqlalchemy
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# Configure application
app = Flask(__name__)
app.secret_key = '20180906'

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
#app.config["SESSION_FILE_DIR"] = mkdtemp()
#app.config["SESSION_PERMANENT"] = False
#app.config["SESSION_TYPE"] = "filesystem"
#Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("postgres://nroejpbfllwtau:019feb4fc02a9659a99618996e4f48f152b98fedd03a19719dabbf6a0cda25c5@ec2-54-225-92-1.compute-1.amazonaws.com:5432/d5c9on8gnask50")

### Define each route under GET and POST

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show the user their created workout list"""

    # If the user has selected a workout
    if request.method == "POST":

        # Check if the user is selecting a workout or deleting
        if request.form.get('selector'):

            # Check which workout the user selected based on the button chosen, fetch a table of that specific workout and return the exercise html
            workout_id = request.form.get('selector')
            workouts = db.execute("SELECT workouts.workout_name, exercises.exercise, exercises.sets, exercises.reps FROM workouts INNER JOIN exercises ON workouts.workout_id=exercises.workout_id WHERE workouts.workout_id=(:workout_id)", workout_id=workout_id)
            return render_template("exercise.html", workouts=workouts)

        else:

            # Check which workout the user selected based on the button chosen, delete that workout
            workout_id = request.form.get('deleter')
            db.execute("DELETE FROM workouts WHERE workouts.workout_id=(:workout_id)", workout_id=workout_id)
            db.execute("DELETE FROM exercises WHERE exercises.workout_id=(:workout_id)", workout_id=workout_id)

            # Reselect all the remainign workouts and refresh
            workouts = db.execute("SELECT workouts.workout_name, workouts.workout_id, workouts.author_name, workouts.workout_type FROM workouts WHERE workouts.author_id=(:user_id)", user_id=session["user_id"])
            return render_template("index.html", workouts=workouts)

    else:

        # Fetch a table of every workout the user has created
        workouts = db.execute("SELECT workouts.workout_name, workouts.workout_id, workouts.author_name, workouts.workout_type FROM workouts WHERE workouts.author_id=(:user_id)", user_id=session["user_id"])

        # If the user has no personal workouts - return the 'empty.html' page
        if not workouts:
            return render_template("empty.html")
        else:
            # Return 'index.html' which will generate a table of all user-created workouts
            return render_template("index.html", workouts=workouts)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register the user"""

    # Check if the user reached this page by POST (Submitting form)
    if request.method == "POST":

        errormsg = None

        # Make sure that the username field is filled
        if not request.form.get("username"):
            return render_template("register.html", errormsg = "Please enter a username")

        # Make sure that the password field is filled
        if not request.form.get("password"):
            return render_template("register.html", errormsg = "Please enter a password")

        # Make sure that the confirm password field is filled
        if not request.form.get("confirmation"):
            return render_template("register.html", errormsg = "Please enter a confirmation password")

        # Make sure that the password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html", errormsg = "Confirmation password must match")

        # Assuming the user has met every condition, hash the password and insert to 'users', and ensure that user is unique
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))

        # If the user is not unique then deny access and return error
        if not result:
            return render_template("register.html", errormsg = "Username is already in use")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Now that they are logged in, send to the home page
        return redirect("/")

    # Otherwise redirect them back to the register
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log-in the user"""

    # Forget any user_id
    session.clear()

    errormsg = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", errormsg = "Please enter a username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", errormsg = "Please enter a password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", errormsg = "Invalid username or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Allow the user to create a workout"""

    # Check if the user submitted the workout form
    if request.method == "POST":
        name = request.form.get("workout_name")
        exercise = request.form.getlist("exercise")
        sets = request.form.getlist("sets")
        reps = request.form.getlist("reps")

        # Check validity of name
        if not name:
            return render_template("create.html", errormsg = "Please enter a name")

        # Check validity of entered data, must exist and be greater than 0
        for x in range(len(exercise)):
            if not exercise[x]:
                return render_template("create.html", errormsg = "Please enter an exercise name")

            if not sets[x] or int(sets[x]) < 0:
                return render_template("create.html", errormsg = "Please enter a valid number of sets")

            if not reps[x] or int(reps[x]) < 0:
                return render_template("create.html", errormsg = "Please enter a valid number of reps")

        # If the workout was created as private, update the table as such
        if request.form.get("private"):
            private = 1
        else:
            private = 0

        # Get author name
        author_name = db.execute("SELECT username FROM users WHERE id=(:id)", id=session["user_id"])

        # Append data to the 'workouts' table and get a 'temp_id' to refer to it later when we join tables
        db.execute("INSERT INTO workouts (author_id, workout_name, private, author_name, workout_type) VALUES (:id, :name, :private, :author_name, :workout_type);", id=session["user_id"], name=name, private=private, author_name=author_name[0]["username"], workout_type=request.form.get("workout_type"))
        temp_id = db.execute("SELECT max(workout_id) AS id FROM workouts;")

        # Append data to the 'exercises' table by iterating a loop of each exercise
        for x, y, z in zip(exercise, sets, reps):
            db.execute("INSERT INTO exercises (workout_id, exercise, sets, reps) VALUES (:temp_id, :exercise, :sets, :reps);", temp_id=temp_id[0]["id"], exercise=x, sets=int(y), reps=int(z))

        # Now return the user to their homepage ('index.html') where they can automatically see the new exercise they made based on the temp_id
        workouts = db.execute("SELECT workouts.workout_name, exercises.exercise, exercises.sets, exercises.reps FROM workouts INNER JOIN exercises ON workouts.workout_id=exercises.workout_id WHERE workouts.workout_id=(:temp_id)", temp_id=temp_id[0]["id"])
        return render_template("exercise.html", workouts=workouts)

    # If the user has not yet fileld the workout form, send to the form
    else:
        return render_template("create.html")

@app.route("/view", methods=["GET", "POST"])
@login_required
def view():
    """Show the user all workouts"""

    # If the user has selected a workout
    if request.method == "POST":

        # Check which workout the user selected based on the button chosen, fetch a table of that specific workout and return the exercise html
        workout_id = post_id = request.form.get('selector')
        workouts = db.execute("SELECT workouts.workout_name, exercises.exercise, exercises.sets, exercises.reps FROM workouts INNER JOIN exercises ON workouts.workout_id=exercises.workout_id WHERE workouts.workout_id=(:workout_id)", workout_id=workout_id)
        return render_template("exercise.html", workouts=workouts)

    else:

        # Fetch a table of every workout stored in the database, provided they aren't private
        workouts = db.execute("SELECT workouts.workout_name, workouts.workout_id, workouts.author_name, workouts.workout_type FROM workouts WHERE private=:private", private=False)

        # Return 'index.html' which will generate a table of all created workouts
        return render_template("view.html", workouts=workouts)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
