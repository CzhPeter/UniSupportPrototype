from typing import Optional, List
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

# Association table for users subscribing to topics
topic_subscribers = sa.Table(
    'topic_subscribers',
    db.metadata,
    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('topic_id', sa.Integer, sa.ForeignKey('topics.id'), primary_key=True),
)

# Association table for users allowed to post in topics
topic_posters = sa.Table(
    'topic_posters',
    db.metadata,
    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('topic_id', sa.Integer, sa.ForeignKey('topics.id'), primary_key=True),
)

# Association table for notification recipients
notification_recipients = sa.Table(
    'notification_recipients',
    db.metadata,
    sa.Column('notification_id', sa.Integer, sa.ForeignKey('notifications.id'), primary_key=True),
    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True),
)

@dataclass
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    role: so.Mapped[str] = so.mapped_column(sa.String(10), default="Normal")
    records: so.Mapped[list["AnswerRecord"]] = so.relationship(back_populates="user", cascade="all, delete-orphan")

    # Topics this user is subscribed to
    subscriptions: so.Mapped[List['Topic']] = so.relationship(
        'Topic',
        secondary=topic_subscribers,
        back_populates='subscribers',
    )

    # Topics this user is allowed to post in
    posting_topics: so.Mapped[List['Topic']] = so.relationship(
        'Topic',
        secondary=topic_posters,
        back_populates='posters',
    )

    # Notifications this user has created
    posted_notifications: so.Mapped[List['Notification']] = so.relationship(
        'Notification',
        back_populates='poster',
        cascade='all, delete-orphan',
    )

    # Notifications this user has received
    received_notifications: so.Mapped[List['Notification']] = so.relationship(
        'Notification',
        secondary=notification_recipients,
        back_populates='recipients',
    )

    def __repr__(self):
        pwh= 'None' if not self.password_hash else f'...{self.password_hash[-5:]}'
        return f'User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, pwh={pwh})'

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Topic(db.Model):
    __tablename__ = 'topics'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True, unique=True)
    description: so.Mapped[str] = so.mapped_column(sa.String(256))

    # Users who have subscribed to this topic
    subscribers: so.Mapped[List[User]] = so.relationship(
        'User',
        secondary=topic_subscribers,
        back_populates='subscriptions',
    )

    # Users who are allowed to post notifications in this topic
    posters: so.Mapped[List[User]] = so.relationship(
        'User',
        secondary=topic_posters,
        back_populates='posting_topics',
    )

    # All notifications posted under this topic
    notifications: so.Mapped[List['Notification']] = so.relationship(
        'Notification',
        back_populates='topic',
        cascade='all, delete-orphan',
    )

    def add_subscriber(self, user: User):
        """Subscribe a user to this topic if not already subscribed."""
        if user not in self.subscribers:
            self.subscribers.append(user)

    def remove_subscriber(self, user: User):
        """Unsubscribe a user from this topic if currently subscribed."""
        if user in self.subscribers:
            self.subscribers.remove(user)

    def add_poster(self, user: User):
        """Grant a user permission to post in this topic."""
        if user not in self.posters:
            self.posters.append(user)

    def post_notification(self, poster: User, content: str) -> 'Notification':
        """
        Create a new notification in this topic by an authorized poster,
        then distribute it to all current subscribers.
        """
        if poster not in self.posters:
            raise PermissionError(f"{poster.username} does not have posting rights for this topic")

        notif = Notification(
            content=content,
            poster=poster,
            topic=self,
            date=datetime.now()
        )
        db.session.add(notif)

        # Add each subscriber as a recipient of this notification
        for sub in self.subscribers:
            notif.recipients.append(sub)

        db.session.commit()
        return notif


class Notification(db.Model):
    __tablename__ = 'notifications'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    content: so.Mapped[str] = so.mapped_column(sa.Text)
    date: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=datetime.now)

    # The user who posted this notification
    poster_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'))
    poster: so.Mapped[User] = so.relationship('User', back_populates='posted_notifications')

    # The topic this notification belongs to
    topic_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('topics.id'))
    topic: so.Mapped[Topic] = so.relationship('Topic', back_populates='notifications')

    # Users who have received this notification
    recipients: so.Mapped[List[User]] = so.relationship(
        'User',
        secondary=notification_recipients,
        back_populates='received_notifications',
    )
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


