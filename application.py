import os

from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from flask_bcrypt import Bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)
bcrypt = Bcrypt(app)

if not os.getenv('DATABASE_URL'):
	raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
	if "username" not in session:
		if request.method == "GET":
			return render_template("register.html")
		
		elif request.method == "POST":
			full_name = request.form.get("full_name")
			username = request.form.get("username")
			email = request.form.get("email")
			password = request.form.get("password")

			password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

			db_username = db.execute("SELECT username FROM Users WHERE username = :username", {"username": username}).fetchone()
			db_email = db.execute("SELECT username FROM Users WHERE email = :email", {"email": email}).fetchone()
			print(db_username)
			print(db_email)

			if (db_username == None and db_email == None):
				db.execute("INSERT INTO Users (username, email, password, full_name) VALUES (:username, :email, :password, :full_name)",
					{"username": username, "password": password_hash, "email": email, "password": password_hash, "full_name": full_name})

				db.commit()

				return redirect("/", code=303)
			
			else:
				return render_template("error.html", message="Username or Email already exist!!!")
	
	else:
		return redirect("/", code=303)
				

@app.route("/login", methods=["GET", "POST"])
def login():
	if "username" not in session:
		if request.method == "GET":
			return render_template("login.html")
		elif request.method == "POST":
			username = request.form.get("username")
			password = request.form.get("password")

			user = db.execute("SELECT * FROM Users WHERE username = :username", {"username": username}).fetchone()

			if user == None:
				return render_template("error.html", message="Username doesn't exist!!!")

			user_hashed_password = user.password

			check_password = bcrypt.check_password_hash(user_hashed_password, password)

			if check_password == True:
				session["username"] = username
				return redirect("/", code=303)
			else:
				return render_template("error.html", message="Incorrect password!!!")

	else:
		return redirect("/", code=303)

@app.route("/logout")
def logout():
	if "username" in session:
		session.pop("username", None)
		return redirect("/", code=303)