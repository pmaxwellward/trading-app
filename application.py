import os
import json

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, make_response
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd



# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use database
uri = os.getenv("DATABASE_URL") 
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
db = SQL(uri)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

def calcShares(sym):
    # Store values of stocks purchased and stocks sold
    sharesBought = db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = :symbol AND sale IS NULL AND id = :user_id", symbol=sym, user_id=session["user_id"])[0]
    sharesSold = db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = :symbol AND sale IS NOT NULL AND id = :user_id", symbol=sym, user_id=session["user_id"])[0]
    
    # If user hasn't sold any stocks
    if sharesSold["sum"] == None:
        return sharesBought["sum"]
    # Else if user hasn't purchase any stocks
    elif sharesBought["sum"] == None:
        return 0
    # Else subtract sold stocks from purchased stocks
    else:
        return round((sharesBought["sum"] - sharesSold["sum"]), 2)

def calcSumPrice(sym):
    # 
    purchasePrice = db.execute("SELECT SUM(price * shares) FROM transactions WHERE symbol = :symbol AND id = :user_id AND sale IS NULL", symbol=sym, user_id=session["user_id"])[0]
    salePrice = db.execute("SELECT SUM(price * shares) FROM transactions WHERE symbol = :symbol AND id = :user_id AND sale = 'true'", symbol=sym, user_id=session["user_id"])[0]
    # 
    if salePrice["sum"] == None:
        salePrice["sum"] = 0
    # 
    if purchasePrice["sum"] == None:
        purchasePrice["sum"] = 0 
    # 
    return round(purchasePrice["sum"] - salePrice["sum"], 2)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # Select transaction table, set a variable that will hold total stock value, and select user cash balance
    rows = db.execute("SELECT id, symbol FROM transactions WHERE id = :user_id GROUP BY id, symbol", user_id=session["user_id"])

    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]

    if request.method == "GET":

        total = 0
        cost = 0
        close = 0
        acctOpen = {}
        acctDay = {}
        
        """Show value of currently owned stocks on homepage"""
        for row in rows:
            # Get current value of stock
            position = lookup(row["symbol"])
            row["curPrice"] = round(position["price"], 2)
            #
            row["shares"] = calcShares(row["symbol"])
            # Multiply current price of stock by amount user owns and add to total
            total += row["curPrice"] * row["shares"]
            # Get average purchase price of symbol and add to row
            avgPrice = db.execute("SELECT AVG(price) FROM transactions WHERE symbol = :symbol AND id = :user_id", symbol=row["symbol"], user_id=session["user_id"])
            row["avgPrice"] = round(avgPrice[0]["avg"], 2)
            #
            row["sumPrice"] = calcSumPrice(row["symbol"])
            cost += row["sumPrice"]
            close += position["close"] * row["shares"]
            #
            if (row["shares"] > 0):
                row["pl-usd"] = round((row["curPrice"] * row["shares"]) - row["sumPrice"], 2)
                row["pl-pct"] = round((row["curPrice"] * row["shares"] - row["sumPrice"]) / (row["curPrice"] * row["shares"]) * 100, 2)

        if total > 0:
            acctOpen["usd"] = round(total-cost, 2)
            acctOpen["pct"] = round(((total - cost)/total) * 100, 2)
            acctDay["usd"] = round(close - cost, 2)
            acctDay["pct"] = round(((close - cost)/total) * 100, 2)

        return render_template("index.html", rows=rows, total=round(total, 2), cash=round(cash["cash"], 2), cost=round(cost, 2), close=round(close, 2), acctOpen=acctOpen, acctDay=acctDay)

    else:
        #
        res = {}
        #
        total = 0
        cost = 0
        close = 0
        #
        for row in rows:
            #
            position = lookup(row["symbol"])
            row["shares"] = calcShares(row["symbol"])
            row["sumPrice"] = calcSumPrice(row["symbol"])
            cost += row["sumPrice"]
            close += position["close"] * row["shares"]

            total += position["price"] * row["shares"]

            if row["shares"] > 0:
                res[row["symbol"] + "-mkt-value"] = position["price"] * row["shares"]
                res[row["symbol"] + "-pl-usd"] = (position["price"] * row["shares"]) - row["sumPrice"]
                res[row["symbol"] + "-pl-pct"] = (position["price"] * row["shares"] - row["sumPrice"]) / (position["price"] * row["shares"]) * 100
                res[row["symbol"] + "-cur-price"] = position["price"]
                res["acct-total"] = total + cash["cash"]
                res["acct-mkt-value"] = total
                res["acct-open-pl-usd"] = total - cost
                res["acct-open-pl-pct"] = ((total - cost)/total) * 100
                res["acct-day-pl-usd"] = close - cost
                res["acct-day-pl-pct"] = ((close - cost)/total) * 100
        
        return jsonify(res)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    """Purchase stocks"""

    if request.method == "POST":

        # Check submitted values
        symbol = request.form.get("symbol")
        if not symbol:
            return render_template("apology.html", msg="You Must Enter a Valid Symbol", code=400), 400
        shares = request.form.get("shares")
        if not shares:
            return render_template("apology.html", msg="You Must Enter a Valid Number for shares", code=400), 400
        position = lookup(symbol)
        if position == None:
            return render_template("apology.html", msg="Invalid Symbol", code=400), 400

        # Check is user has enough money to buy shares and insert into db table
        price = position["price"]
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        balance = cash["cash"]
        name = position["name"]

        if cash["cash"] < price:
            return render_template("apology.html", msg="You don't have enough cash", code=403), 403
        else:
            balance -= (price * float(shares))

        db.execute("INSERT INTO transactions (id, symbol, name, shares, price) VALUES (:sessionID, :symbol, :name, :shares, :price)",
            sessionID=session["user_id"], symbol=symbol, name=name, shares=shares, price=price)

        db.execute("UPDATE users SET cash = :balance WHERE id = :user_id", balance=balance, user_id=session["user_id"])

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show transaction history"""

    # Store entire table in variable and display it
    rows = db.execute("SELECT * FROM transactions WHERE id = :user_id ORDER BY date", user_id=session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("apology.html", msg="must provide username", code=403), 403

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("apology.html", msg="must provide password", code=403), 403

        username = request.form.get("username")
        username = username.upper()

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("apology.html", msg="invalid username and/or password", code=403), 403

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
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    """Get Price of Stock"""

    if request.method == "POST":

        # Lookup price of submitted symbol
        symbol = request.form.get("symbol")

        # See is stock is valid, and if it is show quoted price
        if not quote:
            return render_template("apology.html", msg="Invalid stock symbol", code=400), 400
        else:
            return redirect("/quote/" + symbol)
    else:
        return render_template("quote.html")


@app.route("/quote/<symbol>", methods=["GET","POST"])
@login_required
def quoted(symbol):
    """Get Price of Stock"""
    
    # Lookup price of submitted symbol
    quote = lookup(symbol)
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
    balance = cash["cash"]

    if not quote:
        return render_template("apology.html", msg="Invalid stock symbol", code=400), 400
    
    if quote["change"]:
        quote["change"] = round(quote["change"], 2)
        quote["changePct"] = round(quote["changePct"] * 100, 2)


    if request.method == "POST":
        # See is stock is valid, and if it is show quoted price
        res = {}
        res["price"] = quote["price"]
        res["change"] = quote["change"]
        res["changePct"] = quote["changePct"]

        return jsonify(res)

    else:
        return render_template("quoted.html", quote=quote, balance=round(balance, 2))
    

@app.route("/register", methods=["GET", "POST"])
def register():

    """Register User"""

    if request.method == "POST":
        # Check user submitted values
        name = request.form.get("username")
        if not name:
            return render_template("apology.html", msg="You must provide a username", code=403), 403
        password = request.form.get("password")
        if not password:
            return render_template("apology.html", msg="You must provide a password", code=403), 403

        name = name.upper()

        # Check if username already exists, return apology is yes, insert in to db if no
        userMatch = db.execute("SELECT * FROM users WHERE username = :name", name=name)

        if userMatch:
                return render_template("apology.html", msg="Username is already taken", code=403), 403

        db.execute("INSERT INTO users (username, hash) VALUES (:name, :password)", name=name, password=generate_password_hash(password))
        return redirect("/login")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    """Sell shares"""

    if request.method == "POST":

        # Check submitted values
        symbol = request.form.get("symbol")
        if not symbol:
            return render_template("apology.html", msg="You Must Enter a Valid Symbol", code=400), 400
        shares = request.form.get("shares")
        if not shares:
            return render_template("apology.html", msg="You Must Enter a Valid Number for shares", code=400), 400
        position = lookup(symbol)
        if position == None:
            return render_template("apology.html", msg="Invalid Symbol", code=400), 400
        
        # See if user owns shares of queried symbol
        userPosition = calcShares(symbol)
        
        if not userPosition or userPosition < int(shares):
            return render_template("apology.html", msg="Amount entered is greater than amount owned", code=400), 400

        # Get current price of shares selected, add transaction value to account
        price = position["price"]
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        balance = cash["cash"] + (position["price"] * float(shares))
        name = position["name"]

        db.execute("INSERT INTO transactions (id, symbol, name, shares, price, sale) VALUES (:sessionID, :symbol, :name, :shares, :price, :sale)",
            sessionID=session["user_id"], symbol=symbol, name=name, shares=shares, price=price, sale='true')

        db.execute("UPDATE users SET cash = :balance WHERE id = :user_id", balance=balance, user_id=session["user_id"])

        return redirect("/")
    else:

        # Gather what stocks the user currently owns to display them
        rows = db.execute("SELECT * FROM transactions WHERE id = :user_id GROUP BY symbol", user_id=session["user_id"])
        for row in rows:
            sharesBought = db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = :symbol AND sale IS NULL", symbol=row["symbol"])[0]
            sharesSold = db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = :symbol AND sale = 'true'", symbol=row["symbol"])[0]
            if sharesSold["sum"] == None:
                row["shares"] = sharesBought["sum"]
            elif sharesBought["sum"] == None:
                row["shares"] = 0
            else:
                row["shares"] = (sharesBought["sum"] - sharesSold["sum"])

        return render_template("sell.html", rows=rows)

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    """Deposit Money into account"""

    # Get current cash balance
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]

    if request.method == "POST":

        # Get amount that user submitted via form from deposit.html
        amount = request.form.get("amount")

       # If there is an invalid amount submitted
        if not amount:
            return render_template("apology.html", msg="Enter an amount to deposit", code=400), 400

        # Add amount to current cash balance and update db
        newBalance = cash["cash"] + float(amount)
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=float(newBalance), user_id=session["user_id"])

        return redirect("/")

    else:
        return render_template("deposit.html", cash=cash["cash"])

@app.route("/search")
@login_required
def search():
    """"Search Bar behavior"""
    # Select symbols and company names that closely match the search query
    q1 = "SELECT * FROM symbols WHERE symbol ILIKE ?"
    q2 = "SELECT * FROM symbols WHERE name ILIKE ?"
    symbols = db.execute(q1 + " UNION ALL " + q2, "%" + request.args.get("q") + "%", request.args.get("q") + "%") 
    return jsonify(symbols)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("apology.html", msg=e.name, code=e.code), e.code


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
