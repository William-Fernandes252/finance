import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT stocks.symbol, stocks.name, SUM(transactions.shares) FROM stocks JOIN transactions ON stocks.id = transactions.stock_id JOIN users ON users.id = transactions.user_id WHERE transactions.user_id = ? GROUP BY stocks.symbol HAVING SUM(transactions.shares) > 0", session["user_id"])
    user = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]

    stocks = []
    total = 0.00
    for row in rows:
        quote = lookup(row["symbol"])
        stock = {}
        stock["symbol"] = quote["symbol"]
        stock["name"] = quote["name"]
        stock["shares"] = db.execute("SELECT SUM(transactions.shares) FROM transactions JOIN stocks ON stocks.id = transactions.stock_id WHERE stocks.symbol = ?", row["symbol"])[0]["SUM(transactions.shares)"]
        stock["price"] = quote["price"]
        stock["cash"] = quote["price"] * int(stock["shares"])
        total += stock["cash"]
        stocks.append(stock)
    total += float(user["cash"])
    user["total"] = total

    return render_template("index.html", stocks = stocks, user = user)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 400)
        symbol = symbol.upper()
        shares = request.form.get("shares")
        if not shares:
            return apology("missing shares", 400)
        elif not shares.isdecimal():
            return apology("must enter a valid number of shares", 400)
        shares = int(shares)
        if shares < 1:
            return apology("number of shares must be greater than or equal to 1", 400)

        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)

        if not db.execute("SELECT * FROM stocks WHERE symbol = ?", quote["symbol"]):
            db.execute("INSERT INTO stocks(symbol, name) VALUES(?, ?)", quote["symbol"], quote["name"])

        stock_id = db.execute("SELECT id FROM stocks WHERE symbol = ?", quote["symbol"])[0]["id"]

        if request.form.get("Cart"):
            if "cart" not in session:
                session["cart"] = []
            item = {"id": stock_id, "shares": shares}
            session["cart"].append(item)
            flash("Added to Cart!")
            return redirect("/buy")

        total = quote["price"] * shares
        if total > db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]:
            return apology(f"Trade denied. Currently you can not afford this amount of {quote['name']} shares", 400)

        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total, session["user_id"])
        db.execute("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], stock_id, shares, quote["price"], total, db.execute("SELECT DATETIME('now')")[0]["DATETIME('now')"])

        flash("Bought!")
        return redirect("/")

    else:

        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT stocks.symbol, transactions.shares, transactions.price, transactions.date FROM stocks JOIN transactions ON stocks.id = transactions.stock_id JOIN users ON users.id = transactions.user_id WHERE transactions.user_id = ?", session["user_id"])
    return render_template("history.html", transactions = transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        symbol = request.form.get("symbol")
        if not symbol:
            return apology("missing symbol", 400)
        elif not symbol.isalpha():
            return apology("symbol must contain only alphabetical charaters.", 400)
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)

        if request.form.get("Favorite"):
            if "favorites" not in session:
                session["favorites"] = []
            session["favorites"].append(quote["symbol"])
            flash("Added to Favorites!")
            return redirect("/quote")

        return render_template("quoted.html", name = quote["name"], symbol = quote["symbol"], price = quote["price"])

    else:

        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        confirmation = request.form.get("confirmation")

        if not confirmation:
            return apology("must confirm password", 400)
        elif  password != confirmation:
            return apology("the passwords do not match", 400)

        checkUsername = db.execute("SELECT username FROM users WHERE username = ?", username)
        if not checkUsername:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        else:
            return apology("Failed to register. This username already is in use!", 400)

        flash("You were successfully registered!")
        return redirect("/login")

    else:

        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks = db.execute("SELECT stocks.symbol FROM stocks JOIN transactions ON stocks.id = transactions.stock_id JOIN users ON users.id = transactions.user_id WHERE transactions.user_id = ? GROUP BY stocks.symbol HAVING SUM(transactions.shares) > 0", session["user_id"])
    user = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]

    if request.method == "POST":

        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 400)
        symbol = symbol.upper()
        shares = request.form.get("shares")
        if not shares:
            return apology("missing shares", 400)
        elif not shares.isdecimal():
            return apology("must enter a valid number of shares", 400)
        shares = int(shares)
        if shares < 1:
            return apology("number of shares must be greater than or equal to 1", 400)
        quote = lookup(symbol)
        if not quote:
            return apology("invalid symbol", 400)

        for stock in stocks:
            stock["shares"] = db.execute("SELECT SUM(transactions.shares) FROM transactions JOIN stocks ON stocks.id = transactions.stock_id WHERE stocks.symbol = ?", stock["symbol"])[0]["SUM(transactions.shares)"]
            if stock["symbol"] == symbol:
                if shares > stock["shares"]:
                    return apology(f"Trade denied. Currently you do not own this amount of shares of {quote['name']}", 400)

        total = quote["price"] * shares

        stock_id = db.execute("SELECT id FROM stocks WHERE symbol = ?", quote["symbol"])[0]["id"]
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total, session["user_id"])
        db.execute("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], stock_id, -shares, quote["price"], total, db.execute("SELECT DATETIME('now')")[0]["DATETIME('now')"])

        flash("Sold!")
        return redirect("/")

    else:

        return render_template("sell.html", stocks = stocks)


@app.route("/username", methods = ["GET", "POST"])
@login_required
def username():
    """Change username"""
    if request.method == "POST":
        new = request.form.get("new")

        checkUsername = db.execute("SELECT username FROM users WHERE username = ?", new)
        if not checkUsername:
            db.execute("UPDATE users SET username = ? WHERE id = ?", new, session["user_id"])
        else:
            return apology("Operation failed. This username already is in use.")

        flash("Username has been succefuly updated!")
        return redirect("/")

    else:

        return render_template("username.html")


@app.route("/password", methods = ["GET", "POST"])
@login_required
def password():
    """Change password"""
    if request.method == "POST":

        old = request.form.get("old")
        if generate_password_hash(old) != db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]:
            return apology("Operation failed. Old password is invalid.", 403)

        new = request.form.get("new")
        confirmation = request.form.get("confirmation")

        if new != confirmation:
            return apology("Operation failed. The passwords do not match.", 403)

        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new), session["user_id"])

        flash("Password has been succefuly updated!")
        return redirect("/")

    else:

        return render_template("password.html")


@app.route("/cash", methods = ["GET", "POST"])
@login_required
def cash():
    """Add or withdraw cash from account"""
    if request.method == "POST":

        value = float(request.form.get("value"))
        if not value:
            return apology("must insert a value", 400)
        elif value <= 0:
            return apology("must insert a non-zero value", 400)
        operation = request.form.get("operation")
        if not operation:
            return apology("must choose an operation", 400)

        if operation == "Add":
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", value, session["user_id"])
        elif operation == "Withdraw":
            db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", value, session["user_id"])

        flash("Operation performed successfully!")
        return redirect("/")

    else:

        return render_template("cash.html")


@app.route("/profile")
@login_required
def profile():
    """Manage app profile"""
    return render_template("profile.html")


@app.route("/cart", methods = ["GET", "POST"])
@login_required
def cart():
    """Manage and buy items in cart"""
    if "cart" not in session:
        session["cart"] = []

    rows = db.execute("SELECT id, symbol, name FROM stocks WHERE id IN (?)", [item["id"] for item in session["cart"]])

    items = []
    cartTotal = 0.00
    for row in rows:
        item = {}
        item["id"] = int(row["id"])
        item["symbol"] = row["symbol"]
        item["name"] = row["name"]
        for i in session["cart"]:
            if i["id"] == item["id"]:
                item["shares"] = i["shares"]
        quote = lookup(item["symbol"])
        item["price"] = quote["price"]
        item["cash"] = item["shares"] * quote["price"]
        cartTotal += item["cash"]
        items.append(item)

    if request.method == "POST":

        if not session["cart"]:
            flash("Empty Cart!")
            return redirect("/")

        if request.form.get("Buy"):
            user = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]
            if cartTotal > user["cash"]:
                return apology("Trade denied. Currently you can not afford this cart", 400)

            db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", cartTotal, session["user_id"])
            for item in items:
                db.execute("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], item["id"], item["shares"], quote["price"], item["cash"], db.execute("SELECT DATETIME('now')")[0]["DATETIME('now')"])

            flash("Bought!")
            return redirect("/")

        elif request.form.get("Clear"):
            session["cart"].clear()
            flash("Cart deleted")
            return redirect("/")

    else:

        return render_template("cart.html", items = items, total = cartTotal)


@app.route("/favorites", methods = ["GET", "POST"])
@login_required
def favorites():
    """Manage and buy items in cart"""
    if "favorites" not in session:
        session["favorites"] = []

    quotes = []
    for symbol in session["favorites"]:
        quote = lookup(symbol)
        if not db.execute("SELECT * FROM stocks WHERE symbol = ?", quote["symbol"]):
            db.execute("INSERT INTO stocks(symbol, name) VALUES(?, ?)", quote["symbol"], quote["name"])
        quote["id"] = db.execute("SELECT id FROM stocks WHERE symbol = ?", quote["symbol"])[0]["id"]
        quotes.append(quote)

    if request.method == "POST":

        id = int(request.form.get("id"))
        if not id:
            return apology("missing item identifier", 400)

        if "cart" not in session:
            session["cart"] = []
        item = {"id": id, "shares": shares}
        session["cart"].append(item)

        flash("Added to Cart!")
        return redirect("/favorites")

    else:

        return render_template("favorites.html", quotes = quotes)