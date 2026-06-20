from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for
from models import db, User, Expense, Budget
from urllib.parse import quote_plus
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from flask import send_file
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
app = Flask(__name__)

# Secret Key
app.config["SECRET_KEY"] = "mysecretkey"

# MySQL Password
password = quote_plus("Aishu@1726")

# MySQL Connection
app.config["SQLALCHEMY_DATABASE_URI"] = \
f"mysql+pymysql://root:{password}@localhost/expense_tracker"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Database
db.init_app(app)

# Create Tables
with app.app_context():
    db.create_all()


# -------------------------------
# Helper Function
# -------------------------------
def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


# -------------------------------
# Dashboard
# -------------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    selected_month = request.args.get(
        "month",
        datetime.now().strftime("%Y-%m")
    )

    year, month = map(int, selected_month.split("-"))

    total_expenses = (
        Expense.query.with_entities(
            db.func.sum(Expense.amount)
        )
        .filter_by(user_id=current_user.id)
        .filter(
            db.extract("year", Expense.date) == year,
            db.extract("month", Expense.date) == month,
        )
        .scalar()
        or 0
    )

    budget = Budget.query.filter_by(
        user_id=current_user.id
    ).first()

    budget_amount = budget.budget_amount if budget else 0
    remaining = budget_amount - total_expenses

    # Defaults (so template vars always exist)
    percentage = 0
    alert_message = ""
    alert_class = ""

    if budget_amount > 0:
        percentage = (total_expenses / budget_amount) * 100

        if percentage >= 100:
            exceeded = total_expenses - budget_amount
            alert_message = f"Budget exceeded by ₹{exceeded:.2f}"
            alert_class = "danger"
        elif percentage >= 90:
            alert_message = "90% of budget used"
            alert_class = "warning"
        elif percentage >= 80:
            alert_message = "80% of budget used"
            alert_class = "warning"
        elif percentage >= 70:
            alert_message = "70% of budget used"
            alert_class = "info"
        else:
            alert_message = "Budget on track"
            alert_class = "success"

    recent_expenses = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.id.desc())
        .limit(5)
        .all()
    )

    highest = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.amount.desc())
        .first()
    )

    lowest = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.amount.asc())
        .first()
    )

    percent_used = 0
    if budget_amount > 0:
        percent_used = round((total_expenses / budget_amount) * 100)
        if percent_used < 0:
            percent_used = 0

    return render_template(
        "dashboard.html",
        total_expenses=total_expenses,
        budget_amount=budget_amount,
        remaining=remaining,
        percent_used=percent_used,
        expenses=recent_expenses,
        highest=highest,
        lowest=lowest,
        percentage=percentage,
        alert_message=alert_message,
        alert_class=alert_class,
        selected_month=selected_month,
    )


# -------------------------------
# Register
# -------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()

        password_hash = generate_password_hash(
            request.form["password"]
        )

        user = User(
            username=username,
            email=email,
            password=password_hash
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# -------------------------------
# Login
# -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    error_message = None

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"].strip()

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user_id"] = user.id
            session["username"] = user.username

            return redirect(url_for("dashboard"))

        error_message = "Invalid email or password."

    return render_template("login.html", error_message=error_message)


# -------------------------------
# Logout
# -------------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# -------------------------------
# Add Expense
# -------------------------------
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    success_message = None

    if request.method == "POST":

        category = request.form["category"].strip()
        custom_category = request.form.get("custom_category", "").strip()
        amount = float(request.form["amount"])
        description = request.form["description"].strip()
        date = datetime.strptime(
            request.form["date"],
            "%Y-%m-%d"
        ).date()

        if category == "other":
            category = custom_category or "Other"

        expense = Expense(
            category=category,
            amount=amount,
            description=description,
            date=date,
            user_id=current_user.id
        )

        db.session.add(expense)
        db.session.commit()

        success_message = "Expense Added Successfully"

    return render_template(
        "add_expense.html",
        success_message=success_message
    )


# -------------------------------
# Set Budget
# -------------------------------
@app.route("/set_budget", methods=["GET", "POST"])
def set_budget():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    success_message = None

    if request.method == "POST":

        budget_amount = float(
            request.form["budget_amount"]
        )

        month = request.form["month"]

        budget = Budget.query.filter_by(
            user_id=current_user.id
        ).first()

        if budget:

            budget.budget_amount = budget_amount
            budget.month = month

        else:

            budget = Budget(
                budget_amount=budget_amount,
                month=month,
                user_id=current_user.id
            )

            db.session.add(budget)

        db.session.commit()

        success_message = "Budget Saved Successfully"

    return render_template(
        "set_budget.html",
        success_message=success_message
    )


# -------------------------------
# View Users
# -------------------------------
@app.route("/users")
def users():

    all_users = User.query.all()

    result = ""

    for user in all_users:
        result += (
            f"{user.id} | "
            f"{user.username} | "
            f"{user.email}<br>"
        )

    return result

#search for expenses
@app.route("/search")
def search():

    keyword = request.args.get("keyword")

    expenses = Expense.query.filter(
        Expense.category.like(f"%{keyword}%")
    ).all()

    return render_template(
        "view_expenses.html",
        expenses=expenses
    )
#view expenses    

@app.route("/view_expenses")
def view_expenses():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    selected_category = request.args.get("category", "")

    query = Expense.query.filter_by(user_id=current_user.id)

    if selected_category and selected_category != "All":
        query = query.filter_by(category=selected_category)

    expenses = query.all()

    categories = [
        row[0]
        for row in db.session.query(Expense.category)
        .filter_by(user_id=current_user.id)
        .distinct()
        .order_by(Expense.category)
        .all()
    ]

    return render_template(
        "view_expenses.html",
        expenses=expenses,
        categories=categories,
        selected_category=selected_category
    )
    
    
@app.route("/delete_expense/<int:id>")
def delete_expense(id):

    expense = Expense.query.get(id)

    if expense:
        db.session.delete(expense)
        db.session.commit()

    return redirect(url_for("view_expenses"))



@app.route("/profile", methods=["GET", "POST"])
def profile():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    success_message = None
    error_message = None

    if request.method == "POST":
        new_username = request.form["username"].strip()
        new_email = request.form["email"].strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not new_username or not new_email:
            error_message = "Username and email cannot be empty."
        elif new_password and new_password != confirm_password:
            error_message = "New password and confirmation do not match."
        else:
            if new_username != current_user.username:
                current_user.username = new_username
                session["username"] = new_username
            if new_email != current_user.email:
                current_user.email = new_email
            if new_password:
                current_user.password = generate_password_hash(new_password)

            db.session.commit()
            success_message = "Profile updated successfully."

    return render_template(
        "profile.html",
        user=current_user,
        success_message=success_message,
        error_message=error_message
    )


#edit expense
@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
def edit_expense(id):

    expense = Expense.query.get_or_404(id)

    if request.method == "POST":

        expense.category = request.form["category"]

        expense.amount = request.form["amount"]

        expense.description = request.form["description"]

        db.session.commit()

        return redirect(url_for("view_expenses"))

    return render_template(
        "edit_expense.html",
        expense=expense
    )

#export excel
@app.route("/export_excel")
def export_excel():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    data = []

    for expense in expenses:

        data.append({
            "Category": expense.category,
            "Amount": expense.amount,
            "Description": expense.description,
            "Date": expense.date
        })

    df = pd.DataFrame(data)

    file_name = "expenses.xlsx"

    df.to_excel(
        file_name,
        index=False
    )

    return send_file(
        file_name,
        as_attachment=True
    )
    
#add chart
@app.route("/charts")
def charts():

    current_user = get_current_user()

    if not current_user:
        return redirect(url_for("login"))

    selected_month = request.args.get(
        "month",
        datetime.now().strftime("%Y-%m")
    )

    year = int(selected_month.split("-")[0])
    month = int(selected_month.split("-")[1])

    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == month
    ).all()

    total_expenses = sum(
        expense.amount
        for expense in expenses
    )

    data = [
        {
            "category": expense.category,
            "amount": expense.amount,
            "date": expense.date,
        }
        for expense in expenses
    ]

    df = pd.DataFrame(data)

    if df.empty:
        df = pd.DataFrame(
            [{"category": "No Data", "amount": 1, "date": pd.Timestamp.today()}]
        )

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if df.empty:
        df = pd.DataFrame(
            [{"category": "No Data", "amount": 1, "date": pd.Timestamp.today()}]
        )

    category_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    category_counts = df["category"].value_counts().sort_values(ascending=False)

    date_totals = (
        df.dropna(subset=["date"])
        .groupby("date")["amount"]
        .sum()
        .sort_index()
    )

    # Pie chart: category distribution
    plt.figure(figsize=(6, 6))
    plt.pie(
        category_totals,
        labels=category_totals.index,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    plt.title("Expense Distribution by Category")
    plt.tight_layout()
    pie_path = "static/chart_pie.png"
    plt.savefig(pie_path, transparent=False)
    plt.close()

    # Bar chart: total amount by category
    plt.figure(figsize=(8, 5))
    category_totals.plot(kind="bar", color="#4f46e5")
    plt.title("Total Expense by Category")
    plt.xlabel("Category")
    plt.ylabel("Amount")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    bar_path = "static/chart_bar.png"
    plt.savefig(bar_path, transparent=False)
    plt.close()

    # Line or count chart
    if not date_totals.empty and len(date_totals) > 1:
        plt.figure(figsize=(8, 5))
        date_totals.plot(marker="o", color="#14b8a6")
        plt.title("Expense Trend Over Time")
        plt.xlabel("Date")
        plt.ylabel("Amount")
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()
        line_path = "static/chart_line.png"
        plt.savefig(line_path, transparent=False)
        plt.close()
        third_chart = line_path
        third_title = "Expense Trend"
    else:
        plt.figure(figsize=(8, 5))
        category_counts.plot(kind="bar", color="#f59e0b")
        plt.title("Expenses Count by Category")
        plt.xlabel("Category")
        plt.ylabel("Entries")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        count_path = "static/chart_count.png"
        plt.savefig(count_path, transparent=False)
        plt.close()
        third_chart = count_path
        third_title = "Expense Counts"

    return render_template(
        "charts.html",
        pie_chart=pie_path,
        bar_chart=bar_path,
        third_chart=third_chart,
        third_title=third_title,
        total_expenses=int(df['amount'].sum()),
        category_count=int(df['category'].nunique()),
        average_expense=int(df['amount'].mean() if not df.empty else 0),
        top_category=category_totals.idxmax() if not category_totals.empty else None,
        selected_month=selected_month,
    )


# Run App
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)