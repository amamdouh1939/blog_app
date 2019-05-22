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
	if "username" in session:
		username = session["username"]
	else:
		username = None
	blogs = db.execute("SELECT blogs.id, title, content, username, author_id AS author_id FROM Blogs JOIN Users on author_id = users.id ORDER BY (upvotes - downvotes) DESC LIMIT 5").fetchall()	
	return render_template("index.html", blogs=blogs, username=username)

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

@app.route("/create", methods=["GET", "POST"])
def create():
	if "username" in session:
		username = session["username"]
		if request.method == "GET":
			return render_template("create.html", username=username)
		elif request.method == "POST":
			author = session["username"]
			title = request.form.get("blog-title")
			content = request.form.get("blog-content")
			upvotes = 0
			downvotes = 0

			author_id = db.execute("SELECT id FROM Users WHERE username = :username", {"username": author}).fetchone()[0]

			db.execute("INSERT INTO Blogs (author_id, title, content, upvotes, downvotes) VALUES (:author_id, :title, :content, :upvotes, :downvotes)",
				{"author_id": author_id, "title": title, "content": content, "upvotes": upvotes, "downvotes": downvotes})

			blogs = db.execute ("SELECT * FROM Blogs").fetchall()

			db.commit()

			return render_template("index.html", blogs=blogs, username=username)
	else:
		username = None
		return render_template("error.html", message="You must be logged in to create a blog!!!")

@app.route("/blogs")
def blogs():
	if "username" in session:
		username = session["username"]
	else:
		username = None
	blogs = db.execute("SELECT blogs.id, title, content, upvotes, downvotes, username, author_id AS author_id FROM Blogs JOIN Users ON author_id = users.id ORDER BY (upvotes - downvotes) DESC").fetchall()
	return render_template("blogs.html", blogs=blogs, username=username)
			
@app.route("/blog/<int:blog_id>")
def blog(blog_id):
	if "username" in session:
		username = session["username"]
	else:
		username = None
	blog = db.execute("SELECT blogs.id, title, content, upvotes, downvotes, username, author_id AS author_id FROM Blogs JOIN Users ON author_id = users.id WHERE blogs.id = :blog_id", {"blog_id": blog_id}).fetchone()
	blog_owner = False
	if "username" in session and session["username"] == blog.username:
		blog_owner = True
	
	elif "username" in session and session["username"] != blog.username:
		blog_owner = False

	return render_template("blog.html", blog=blog, blog_owner=blog_owner, username=username)

@app.route("/blog/<int:blog_id>/upvote")
def upvote(blog_id):
	upvotes = db.execute("SELECT upvotes FROM Blogs WHERE id = :blog_id", {"blog_id": blog_id}).fetchone().upvotes
	upvotes += 1
	db.execute("UPDATE Blogs SET upvotes = :upvotes WHERE id = :blog_id", {"upvotes": upvotes, "blog_id": blog_id})
	db.commit()

	return redirect("/blog/" + str(blog_id), code=303)

@app.route("/blog/<int:blog_id>/downvote")
def downvote(blog_id):
	downvotes = db.execute("SELECT downvotes FROM Blogs WHERE id = :blog_id", {"blog_id": blog_id}).fetchone().downvotes
	downvotes += 1

	db.execute("UPDATE Blogs SET downvotes = :downvotes WHERE id = :blog_id", {"downvotes": downvotes, "blog_id": blog_id})
	db.commit()

	return redirect("/blog/" + str(blog_id), code=303)


@app.route("/blog/<int:blog_id>/edit", methods=["GET", "POST"])
def edit(blog_id):
	if "username" in session:
		username = session["username"]
	else:
		username = None

	if request.method == "GET":
		blog = db.execute("SELECT blogs.id, title, content, username FROM Blogs JOIN Users ON author_id = users.id WHERE blogs.id = :blog_id", {"blog_id": blog_id}).fetchone()
		blog_author = blog["username"]
		if session["username"] and session["username"] == blog_author:
			return render_template("edit.html", blog=blog, username=username)
		else:
			return render_template("error.html", message="You can't edit another user's blog post!!!", username=username)
	
	elif request.method == "POST":
		title = request.form.get("blog-title")
		content = request.form.get("blog-content")

		db.execute("UPDATE Blogs SET title = :title, content = :content WHERE id = :blog_id", {"title": title, "content": content, "blog_id": blog_id})
		db.commit()

		return redirect("/blog/" + str(blog_id), code=303)

@app.route("/blog/<int:blog_id>/delete", methods=["GET", "POST"])
def delete(blog_id):
	if "username" in session:
		username = session["username"]
	else:
		username = None

	if request.method == "GET":
		blog = db.execute("SELECT blogs.id, title, username FROM Blogs JOIN Users ON author_id = users.id WHERE blogs.id = :blog_id", {"blog_id": blog_id}).fetchone()
		blog_author = blog["username"]
		if session["username"] and session["username"] == blog_author:
			return render_template("delete.html", blog = blog, username = username)
	
	elif request.method == "POST":
		db.execute("DELETE FROM Blogs WHERE id = :blog_id", {"blog_id": blog_id})
		db.commit()

		return redirect("/", code=303)

@app.route("/user/<int:author_id>")
def user(author_id):
	if "username" in session:
		username = session["username"]
	else:
		username = None

	user = db.execute("SELECT username, full_name, email FROM Users WHERE users.id = :author_id", {"author_id": author_id}).fetchone()
	blogs = db.execute("SELECT id, title FROM Blogs WHERE author_id = :author_id", {"author_id": author_id}).fetchall()
	return render_template("user.html", user=user, blogs=blogs, username=username)