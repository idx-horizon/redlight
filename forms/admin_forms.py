from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class UserAdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[Optional(), Length(min=3)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    enabled = BooleanField('Enabled', default=True)
    settings = TextAreaField('Settings (JSON)', validators=[Optional()])
    submit = SubmitField('Save')


