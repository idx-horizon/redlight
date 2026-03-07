from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import json
from app import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    username = db.Column(db.String(50), primary_key=True)
    password_hash = db.Column(db.String(128), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(120))
    settings = db.Column(db.Text)  # store JSON as text

    def set_settings(self, settings_dict):
        self.settings = json.dumps(settings_dict)

    def get_settings(self):
        if self.settings:
            return json.loads(self.settings)
        return {}

    def __repr__(self):
        return f"<User {self.username}>"
