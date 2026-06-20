from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# User Table
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )


# Expense Table
class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    description = db.Column(
        db.String(255)
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )


# Budget Table
class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    budget_amount = db.Column(
        db.Float,
        nullable=False
    )

    month = db.Column(
        db.String(20)
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )