from flask import Blueprint, render_template, url_for, redirect, flash, request, current_app, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, timezone
from app import db, bcrypt
from app.models import User
from app.email import send_verification_email, send_password_reset_email
from itsdangerous import URLSafeTimedSerializer as Serializer

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        if not user or not bcrypt.check_password_hash(user.password, password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

        # Email verification is not required for login.
        login_user(user, remember=remember)

        flash('You have been logged in successfully!', 'success')

        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.home'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.register'))

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', 'danger')
            return redirect(url_for('auth.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            date_created=datetime.now(timezone.utc)
        )

        db.session.add(new_user)
        db.session.commit()

        send_verification_email(new_user)

        flash(
            'Your account has been created! Please check your email to verify your account.',
            'success'
        )

        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    if current_user.is_authenticated and current_user.email_verified:
        return redirect(url_for('main.home'))

    s = Serializer(current_app.config['SECRET_KEY'])

    try:
        data = s.loads(token, max_age=3600)

        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            raise ValueError("Invalid token")

        user.email_verified = True
        user.email_verification_token = None
        user.date_created = datetime.now(timezone.utc)

        db.session.commit()

        flash('Your email has been verified! You can now log in.', 'success')

        return redirect(url_for('auth.login'))

    except Exception as e:
        flash('Invalid or expired verification link', 'danger')
        return redirect(url_for('auth.register'))


@auth_bp.route('/reset', methods=['GET', 'POST'])
def reset():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            send_password_reset_email(user)

        flash(
            'If an account exists with that email, you will receive a password reset link.',
            'info'
        )

        return redirect(url_for('auth.login'))

    return render_template('reset.html')


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    user = User.verify_reset_token(token)

    if not user:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('auth.reset'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.reset_with_token', token=token))

        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.reset_token = None
        user.reset_token_expires = None

        db.session.commit()

        flash(
            'Your password has been updated! You can now log in.',
            'success'
        )

        return redirect(url_for('auth.login'))

    return render_template('reset_with_token.html', token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()

    flash('You have been logged out.', 'info')

    return redirect(url_for('main.home'))