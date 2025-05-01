from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from app import app
from app.models import User, Topic, Notification
from app.forms import ChooseForm, LoginForm
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
import sqlalchemy as sa
from app import db
from urllib.parse import urlsplit
import csv
import io
import datetime


@app.route("/")
def home():
    return render_template('home.html', title="Home")


@app.route("/account")
@login_required
def account():
    return render_template('account.html', title="Account")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('generic_form.html', title='Sign In', form=form)

from flask import jsonify
from app.debug_utils import reset_db
@app.route("/test/reset")
def test_reset():
    """Reset & seed database."""
    reset_db()
    return "Database has been reset and seeded.", 200


@app.route("/test/users")
def test_users():
    """List all users."""
    return "<br>".join(repr(u) for u in User.query.all())


@app.route("/test/topics")
def test_topics():
    """List all topics and their subscribers/posters."""
    lines = []
    for t in Topic.query.all():
        subs    = [u.username for u in t.subscribers]
        posters = [u.username for u in t.posters]
        lines.append(f"{t.name} — subscribers: {subs}, posters: {posters}")
    return "<br>".join(lines)


@app.route("/test/subscribe")
def test_subscribe():
    """
    Subscribe a user to a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.add_subscriber(u)
    db.session.commit()
    return f"{username} subscribed to {topic_name}", 200


@app.route("/test/unsubscribe")
def test_unsubscribe():
    """
    Unsubscribe a user from a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.remove_subscriber(u)
    db.session.commit()
    return f"{username} unsubscribed from {topic_name}", 200


@app.route("/test/grant_post")
def test_grant_post():
    """
    Grant a user posting rights on a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.add_poster(u)
    db.session.commit()
    return f"Granted posting rights on '{topic_name}' to {username}", 200


@app.route("/test/revoke_post")
def test_revoke_post():
    """
    Revoke a user's posting rights on a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    if u in t.posters:
        t.posters.remove(u)
        db.session.commit()
        return f"Revoked posting rights on '{topic_name}' from {username}", 200
    else:
        return f"{username} had no posting rights on '{topic_name}'", 400


@app.route("/test/post")
def test_post():
    """
    Post a notification in a topic.
    GET params: poster=<username>&topic=<topicname>&content=<text>
    """
    poster_name = request.args.get('poster')
    topic_name  = request.args.get('topic')
    content     = request.args.get('content', "Test notification")
    u = User.query.filter_by(username=poster_name).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "Poster or Topic not found", 404
    try:
        notif = t.post_notification(u, content)
    except PermissionError as e:
        return str(e), 403
    return (
        f"Posted notification:<br>"
        f"ID: {notif.id}<br>"
        f"Topic: {notif.topic.name}<br>"
        f"Content: {notif.content}<br>"
        f"From: {notif.poster.username}<br>"
        f"Date: {notif.date.isoformat()}"
    ), 200


@app.route("/test/notifications/<username>")
def test_notifications(username):
    """
    List all notifications received by a user.
    URL param: <username>
    """

    u = User.query.filter_by(username=username).first_or_404()
    lines = [
        f"{n.date.isoformat()} — {n.content} (from {n.poster.username})"
        for n in u.received_notifications
    ]
    return "<br>".join(lines)


@app.route("/test/posted/<username>")
def test_posted(username):
    """
    List all notifications posted by a user.
    URL param: <username>
    """
    u = User.query.filter_by(username=username).first()
    if not u:
        return "User not found", 404
    lines = [
        f"{n.date.isoformat()} — {n.content} (in topic {n.topic.name})"
        for n in u.posted_notifications
    ]
    return "<br>".join(lines)


@app.route("/test/delete_notification")
def test_delete_notification():
    """
    Delete a notification by its ID.
    GET params: id=<notification_id>
    """
    nid = request.args.get('id', type=int)
    n = Notification.query.get(nid)
    if not n:
        return "Notification not found", 404
    db.session.delete(n)
    db.session.commit()
    return f"Deleted notification {nid}", 200


@app.route("/test/all")
def test_all():
    """Dump all data as JSON, now with users' received notifications."""
    users = []
    for u in User.query.all():
        users.append({
            'username': u.username,
            'role':     u.role,
            'subscriptions': sorted(t.name for t in u.subscriptions),
            'posting_topics': sorted(t.name for t in u.posting_topics),
            'received_notifications': [
                {
                    'id':      n.id,
                    'content': n.content,
                    'topic':   n.topic.name,
                    'poster':  n.poster.username,
                    'date':    n.date.isoformat()
                }
                for n in u.received_notifications
            ]
        })

    topics = [{
        'name':        t.name,
        'description': t.description,
        'subscribers': sorted(u.username for u in t.subscribers),
        'posters':     sorted(u.username for u in t.posters),
    } for t in Topic.query.all()]

    notifications = [{
        'id':         n.id,
        'content':    n.content,
        'topic':      n.topic.name,
        'poster':     n.poster.username,
        'recipients': sorted(u.username for u in n.recipients),
        'date':       n.date.isoformat(),
    } for n in Notification.query.all()]

    return jsonify({
        'users': users,
        'topics': topics,
        'notifications': notifications
    })

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


# Error handlers
# See: https://en.wikipedia.org/wiki/List_of_HTTP_status_codes

# Error handler for 403 Forbidden
@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='Error'), 403

# Handler for 404 Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='Error'), 404

@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='Error'), 413

# 500 Internal Server Error
@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='Error'), 500