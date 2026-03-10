from flask import Flask, render_template, redirect, url_for, flash, request
from flask import session as flask_session
from config import Config
from models import db, User, Account, Transaction
from forms import LoginForm, RegistrationForm, TransferForm
from sqlalchemy.exc import SQLAlchemyError
import random
import string

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ------------------------------------------------------------
# Генератор номера счёта (для простоты)
def generate_account_number():
    return '40817810' + ''.join(random.choices(string.digits, k=12))

# ------------------------------------------------------------
# Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in flask_session:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Создаём пользователя
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        # Генерируем счёт
        account = Account(account_number=generate_account_number(), balance=1000.0)  # начальный баланс 1000
        user.account = account
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in flask_session:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            flask_session['user_id'] = user.id
            flask_session['username'] = user.username
            flash('Вы успешно вошли.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    flask_session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in flask_session:
        flash('Пожалуйста, войдите.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(flask_session['user_id'])
    account = user.account
    # Последние 10 операций (где пользователь участник)
    transactions = Transaction.query.filter(
        (Transaction.from_account_id == account.id) | (Transaction.to_account_id == account.id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    return render_template('dashboard.html', user=user, account=account, transactions=transactions)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in flask_session:
        flash('Пожалуйста, войдите.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(flask_session['user_id'])
    account = user.account
    form = TransferForm()
    if form.validate_on_submit():
        recipient = User.query.filter_by(username=form.recipient_username.data).first()
        if not recipient:
            flash('Получатель с таким логином не найден.', 'danger')
        elif recipient.id == user.id:
            flash('Нельзя перевести средства самому себе.', 'danger')
        else:
            amount = form.amount.data
            if amount <= 0:
                flash('Сумма должна быть положительной.', 'danger')
            elif account.balance < amount:
                flash('Недостаточно средств.', 'danger')
            else:
                # Выполняем перевод
                try:
                    # Списание у отправителя
                    account.balance -= amount
                    # Зачисление получателю
                    recipient.account.balance += amount
                    # Запись транзакции
                    transaction = Transaction(
                        from_account_id=account.id,
                        to_account_id=recipient.account.id,
                        amount=amount,
                        description=form.description.data
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    flash(f'Перевод {amount} руб. пользователю {recipient.username} выполнен.', 'success')
                except SQLAlchemyError as e:
                    db.session.rollback()
                    flash('Ошибка базы данных. Перевод не выполнен.', 'danger')
                return redirect(url_for('dashboard'))
    return render_template('transfer.html', form=form, balance=account.balance)

# ------------------------------------------------------------
# Создание таблиц (только для первого запуска)
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('База данных инициализирована.')

if __name__ == '__main__':
    app.run(debug=True)