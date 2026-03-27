import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False
from io import BytesIO
from sqlalchemy import func




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

    crop = db.relationship("Crop", backref="incomes")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)



# -------------------- AUTH --------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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
@login_required
def home():
    user_id = session["user"]
    user = get_current_user()

    # Summary stats
    total_crops = Crop.query.filter_by(user_id=user_id).count()

    total_income = db.session.query(
        db.func.sum(Income.total_amount)
    ).filter(Income.user_id == user_id).scalar() or 0

    total_expense = db.session.query(
        db.func.sum(Expense.amount)
    ).filter(Expense.user_id == user_id).scalar() or 0

    profit = total_income - total_expense

    # Recent activity (last 5 each)
    recent_expenses = Expense.query.filter_by(user_id=user_id)\
        .order_by(Expense.id.desc()).limit(5).all()

    recent_incomes = Income.query.filter_by(user_id=user_id)\
        .order_by(Income.id.desc()).limit(5).all()

    return render_template(
        "home.html",
        current_user=user,
        total_crops=total_crops,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        profit=round(profit, 2),
        recent_expenses=recent_expenses,
        recent_incomes=recent_incomes
    )

@app.route("/crop_dashboard")
@login_required
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
@login_required
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
@login_required
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
@login_required
def income():
    crops = Crop.query.filter_by(user_id=session["user"]).all()

    if request.method == "POST":
        quantity = float(request.form["quantity"])
        price = float(request.form["price"])
        total = quantity * price

        income = Income(
            crop_id=request.form.get("crop_id") or None,
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

# -------------------- EDIT / DELETE ROUTES --------------------

# --- CROPS ---
@app.route("/crops/edit/<int:id>", methods=["POST"])
@login_required
def edit_crop(id):
    crop = Crop.query.get_or_404(id)
    if crop.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("crops"))

    crop.crop_name = request.form["crop_name"]
    crop.area = request.form["area"]
    crop.season = request.form["season"]
    crop.planted_date = request.form["planted_date"]
    db.session.commit()
    flash("Crop updated successfully", "success")
    return redirect(url_for("crops"))

@app.route("/crops/delete/<int:id>")
@login_required
def delete_crop(id):
    crop = Crop.query.get_or_404(id)
    if crop.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("crops"))

    db.session.delete(crop)
    db.session.commit()
    flash("Crop deleted", "success")
    return redirect(url_for("crops"))

# --- EXPENSES ---
@app.route("/expenses/edit/<int:id>", methods=["POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)
    if expense.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("expenses"))

    expense.expense_type = request.form["expense_type"]
    expense.category = request.form["category"]
    expense.description = request.form["description"]
    expense.amount = request.form["amount"]
    expense.date = request.form["date"]
    crop_id = request.form.get("crop_id")
    expense.crop_id = crop_id if expense.expense_type == "crop" else None
    db.session.commit()
    flash("Expense updated", "success")
    return redirect(url_for("expenses"))

@app.route("/expenses/delete/<int:id>")
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    if expense.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("expenses"))

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted", "success")
    return redirect(url_for("expenses"))

# --- INCOME ---
@app.route("/income/edit/<int:id>", methods=["POST"])
@login_required
def edit_income(id):
    inc = Income.query.get_or_404(id)
    if inc.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("income"))

    inc.crop_id = request.form.get("crop_id") or None
    inc.quantity = float(request.form["quantity"])
    inc.price_per_unit = float(request.form["price"])
    inc.total_amount = inc.quantity * inc.price_per_unit
    inc.details = request.form["details"]
    inc.date = request.form["date"]
    db.session.commit()
    flash("Income updated", "success")
    return redirect(url_for("income"))

@app.route("/income/delete/<int:id>")
@login_required
def delete_income(id):
    inc = Income.query.get_or_404(id)
    if inc.user_id != session["user"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("income"))

    db.session.delete(inc)
    db.session.commit()
    flash("Income deleted", "success")
    return redirect(url_for("income"))

# -------------------- JINJA FILTERS --------------------

@app.template_filter("format_date")
def format_date(value):
    """Convert date string or datetime to readable format like '15 Mar 2024'"""
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return value
    return value.strftime("%d %b %Y")


@app.route("/reports")
@login_required
def reports():
    user_id = session.get("user")

    crops = Crop.query.filter_by(user_id=user_id).all()
    report_data = []
    total_income = total_expense = 0

    general_expense = db.session.query(func.sum(Expense.amount)) \
        .filter(Expense.user_id == user_id, Expense.crop_id == None).scalar() or 0

    general_income = db.session.query(func.sum(Income.total_amount)) \
        .filter(Income.user_id == user_id, Income.crop_id == None).scalar() or 0

    per_crop_expense = general_expense / len(crops) if crops else 0
    per_crop_income = general_income / len(crops) if crops else 0

    for crop in crops:
        crop_exp = db.session.query(func.sum(Expense.amount)) \
            .filter(Expense.crop_id == crop.id, Expense.user_id == user_id).scalar() or 0

        crop_inc = db.session.query(func.sum(Income.total_amount)) \
            .filter(Income.crop_id == crop.id, Income.user_id == user_id).scalar() or 0

        final_exp = crop_exp + per_crop_expense
        final_inc = crop_inc + per_crop_income
        profit = final_inc - final_exp

        total_expense += final_exp
        total_income += final_inc

        report_data.append({
            "crop_name": crop.crop_name,   # ✅ MATCH TEMPLATE
            "expense": round(final_exp, 2),
            "income": round(final_inc, 2),
            "profit": round(profit, 2)
        })

    net_profit = total_income - total_expense

    return render_template(
        "reports.html",
        report_data=report_data,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        net_profit=round(net_profit, 2),
        current_user=get_current_user() 
        
    )

#---------------------- REPORTS API -------------------

@app.route("/api/reports")
@login_required
def reports_api():
    user_id = session.get("user")

    crops = Crop.query.filter_by(user_id=user_id).all()
    report_data = []
    total_income = total_expense = 0

    for crop in crops:
        expense = db.session.query(func.sum(Expense.amount)) \
            .filter(Expense.crop_id == crop.id, Expense.user_id == user_id).scalar() or 0

        income = db.session.query(func.sum(Income.total_amount)) \
            .filter(Income.crop_id == crop.id, Income.user_id == user_id).scalar() or 0

        profit = income - expense

        total_expense += expense
        total_income += income

        report_data.append({
            "crop": crop.crop_name,
            "expense": round(expense, 2),
            "income": round(income, 2),
            "profit": round(profit, 2)
        })

    return jsonify({
        "summary": {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_profit": round(total_income - total_expense, 2)
        },
        "crops": report_data
    })





#-----------+++-------- REPORT PDF DOWNLOAD --------------------

@app.route("/reports/pdf")
@login_required
def download_report_pdf():
    if not XHTML2PDF_AVAILABLE:
        flash("PDF export requires xhtml2pdf. Install it with: pip install xhtml2pdf", "warning")
        return redirect(url_for("reports"))

    user_id = session.get("user")
     
    user = User.query.get(user_id) 
    crops = Crop.query.filter_by(user_id=user_id).all()
    report_data = []

    total_expense = 0
    total_income = 0

    for crop in crops:
        expense = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(
            Expense.crop_id == crop.id,
            Expense.user_id == user_id
        ).scalar() or 0

        income = db.session.query(
            db.func.sum(Income.total_amount)
        ).filter(
            Income.crop_id == crop.id,
            Income.user_id == user_id
        ).scalar() or 0

        profit = income - expense
        total_expense += expense
        total_income += income

        report_data.append({
            "crop": crop.crop_name,
            "expense": round(expense, 2),
            "income": round(income, 2),
            "profit": round(profit, 2)
        })

    html = render_template(
        "reports_pdf.html",
        user=user,
        report_data=report_data,
        total_expense=round(total_expense, 2),
        total_income=round(total_income, 2),
        net_profit=round(total_income - total_expense, 2)
    )

    pdf = BytesIO()
    pisa.CreatePDF(html, pdf)

    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=farm_report.pdf"

    return response

# -------------------- RUN --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# This format convert to jsonify