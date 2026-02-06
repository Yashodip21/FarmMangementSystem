import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.secret_key = "secret-key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "farm_db.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # check

db = SQLAlchemy(app)

# -------------------- MODELS --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100))
    area = db.Column(db.Float)
    season = db.Column(db.String(50))
    planted_date = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)




class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_type = db.Column(db.String(50))  # general / crop
    category = db.Column(db.String(50))
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    date = db.Column(db.String(20))
    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=True)

    crop = db.relationship("Crop", backref="expenses")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)



class Income(db.Model):   
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=True)
    quantity = db.Column(db.Float)
    price_per_unit = db.Column(db.Float)
    total_amount = db.Column(db.Float)
    details = db.Column(db.String(200))
    date = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)



# -------------------- AUTH --------------------

def get_current_user():
    if "user" in session:
        return User.query.get(session["user"])
    return None

@app.route("/", methods=["GET", "POST"])
def login():
    # if "user" not in session:
    #  return redirect(url_for("login"))

    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first() # check .first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.id
            return redirect(url_for("home"))
        flash("Invalid login", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # if "user" not in session:
    #  return redirect(url_for("login"))

    if request.method == "POST":
        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Login now.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------- PAGES --------------------

@app.route("/home")
def home():
    
    return render_template("home.html",current_user=get_current_user() )

@app.route("/crop_dashboard")
def crop_dashboard():
    crops = Crop.query.filter_by(user_id=session["user"]).all()

    total_income = db.session.query(
    db.func.sum(Income.total_amount)
).filter(
    Income.user_id == session["user"]   
).scalar() or 0

    total_expense = db.session.query(
    db.func.sum(Expense.amount)
).filter(
    Expense.user_id == session["user"]
).scalar() or 0

    profit = total_income - total_expense

    crop_chart_data = []

    for crop in crops:
        crop_income = db.session.query(
            db.func.sum(Income.total_amount)
        ).filter(
            Income.crop_id == crop.id,
            Income.user_id == session["user"]
        ).scalar() or 0

        crop_expense = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(
            Expense.crop_id == crop.id,
            Expense.user_id == session["user"]
        ).scalar() or 0

        crop_chart_data.append({
            "name": crop.crop_name,
            "income": crop_income,
            "expense": crop_expense
        })

        print(crop_chart_data)


    return render_template(
        "crop_dashboard.html",
        crops = crops,
        total_income=total_income,
        total_expense=total_expense,
        profit=profit,
        crop_chart_data=crop_chart_data,
         current_user=get_current_user()
    )

@app.route("/crops", methods=["GET", "POST"])
def crops():
    if request.method == "POST":
        crop = Crop(
            crop_name=request.form["crop_name"],
            area=request.form["area"],
            season=request.form["season"],
            planted_date=request.form["planted_date"],
            user_id=session["user"] ,
            
        )
        db.session.add(crop)
        db.session.commit()
        flash("Crop added successfully", "success")
        return redirect(url_for("crops"))

    all_crops = Crop.query \
    .filter_by(user_id=session["user"]) \
    .order_by(Crop.id.desc()) \
    .all()

     
    return render_template("crops.html",crops=all_crops,current_user=get_current_user() )
    

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    crops = Crop.query.filter_by(user_id=session["user"]).all()


    if request.method == "POST":
        expense_type = request.form["expense_type"]

        crop_id = request.form.get("crop_id")
        if expense_type == "general":
            crop_id = None

        expense = Expense(
            expense_type=expense_type,
            category=request.form["category"],
            description=request.form["description"],
            amount=request.form["amount"],
            date=request.form["date"],
            crop_id=crop_id,
            user_id=session["user"],
           
        )

        db.session.add(expense)
        db.session.commit()
        flash("Expense added successfully", "success")
        return redirect(url_for("expenses"))

    all_expenses = Expense.query \
    .filter_by(user_id=session["user"]) \
    .order_by(Expense.id.desc()) \
    .all()

    return render_template("expenses.html", crops=crops, expenses=all_expenses,current_user=get_current_user() )

@app.route("/income", methods=["GET", "POST"])
def income():
    crops = Crop.query.filter_by(user_id=session["user"]).all()


    if request.method == "POST":
        quantity = float(request.form["quantity"])
        price = float(request.form["price"])
        total = quantity * price

        income = Income(
            crop_id=request.form.get("crop_id"),
            quantity=quantity,
            price_per_unit=price,
            total_amount=total,
            details=request.form["details"],
            date=request.form["date"],
            user_id=session["user"],
           
        )
        db.session.add(income)
        db.session.commit()
        flash("Income recorded successfully", "success")
        return redirect(url_for("income"))

    incomes = Income.query \
    .filter_by(user_id=session["user"]) \
    .order_by(Income.id.desc()) \
    .all()

    total_income = sum(i.total_amount for i in incomes)

    return render_template(
        "income.html",
        crops=crops,
        incomes=incomes,
        total_income=total_income,
        current_user=get_current_user() 
    )

@app.route("/reports")
def reports():
    return render_template("reports.html",current_user=get_current_user() )

# -------------------- RUN --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# This format convert to jsonify