from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from sqlalchemy import ForeignKey
from sqlalchemy.testing.schema import mapped_column
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from dataclasses import dataclass
from datetime import datetime

@dataclass
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    role: so.Mapped[str] = so.mapped_column(sa.String(10), default="Normal")
    records: so.Mapped[list["AnswerRecord"]] = so.relationship(back_populates="user", cascade="all, delete-orphan")


    def __repr__(self):
        return f'User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, pwh=...{self.password_hash[-5:]})'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

@dataclass
class AnswerRecord(db.Model):
    __tablename__ = 'answer_records'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), nullable=False)
    questionnaire_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False)
    score: so.Mapped[int] = so.mapped_column(nullable=False)
    conclusion: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False)
    timestamp: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    user: so.Mapped["User"] = so.relationship(back_populates="records")

@dataclass
class Question(db.Model):
    __tablename__ = 'questions'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    questionnaire_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False)
    content: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False)


