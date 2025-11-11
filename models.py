from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    strava_id = db.Column(db.String(64), unique=True, nullable=False, primary_key=True)
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    token_expires_at = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.String(128), default="UNKNOWN")
    last_name = db.Column(db.String(128), default="UNKNOWN")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Log(db.Model):
    strava_id = db.Column(db.String(64), db.ForeignKey('user.strava_id'), primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, primary_key=True)