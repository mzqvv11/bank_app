from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь со счётом (один пользователь → один счёт)
    account = db.relationship('Account', backref='owner', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False)  # номер счёта
    balance = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Транзакции, где этот счёт является отправителем или получателем
    outgoing_transactions = db.relationship('Transaction',
                                            foreign_keys='Transaction.from_account_id',
                                            backref='sender_account',
                                            lazy='dynamic')
    incoming_transactions = db.relationship('Transaction',
                                            foreign_keys='Transaction.to_account_id',
                                            backref='receiver_account',
                                            lazy='dynamic')


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    description = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount} from {self.from_account_id} to {self.to_account_id}>'