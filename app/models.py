from datetime import datetime, timedelta, timezone
from app import db, login_manager
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires = db.Column(db.DateTime)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # Updated

    def get_email_verification_token(self, expires_sec=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        token = s.dumps({'user_id': self.id})
        self.email_verification_token = token
        db.session.commit()
        return token

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        token = s.dumps({'user_id': self.id})
        self.reset_token = token
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_sec)  # Updated
        db.session.commit()
        return token

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
            user_id = data['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"