from flask import current_app, render_template
from flask_mail import Message
from threading import Thread
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_verification_email(user):
    token = user.get_email_verification_token()
    send_email(
        f"[{current_app.config['APP_NAME']}] Verify Your Email",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
        text_body=render_template('email/verify_email.txt', user=user, token=token, app_name=current_app.config['APP_NAME']),
        html_body=render_template('email/verify_email.html', user=user, token=token, app_name=current_app.config['APP_NAME'], app_url=current_app.config['APP_URL'])
    )

def send_password_reset_email(user):
    token = user.get_reset_token()
    send_email(
        f"[{current_app.config['APP_NAME']}] Reset Your Password",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token, app_name=current_app.config['APP_NAME']),
        html_body=render_template('email/reset_password.html', user=user, token=token, app_name=current_app.config['APP_NAME'], app_url=current_app.config['APP_URL'])
    )