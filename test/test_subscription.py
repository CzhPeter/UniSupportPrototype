from urllib.parse import urlsplit
from app.models import Topic, topic_subscribers
import sqlalchemy as sa
from app import db

def test_subscribe_positive(logged_in_client, get_user):
    """
    Positive case: user 'tom' subscribes to an Announcement they are not already subscribed to.
    - Returns a 302 redirect to social_system
    - A new subscription relationship is actually created in the database
    """
    user = get_user("tom")
    topic = Topic.query.filter_by(name="Announcements").one()
    assert topic not in user.subscriptions

    rv = logged_in_client.get(f"/subscribe/{topic.id}", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/SocialSystem"
    assert topic in user.subscriptions

def test_subscribe_duplicate(logged_in_client, get_user):
    """
    Negative case: calling /subscribe/<id> again for a topic that is already subscribed to
    should result in a 302 redirect, and the number of subscriptions in the database remains unchanged.
    """
    user = get_user("amy")
    topic = Topic.query.filter_by(name="General").one()
    assert topic in user.subscriptions
    initial_count = len(topic.subscribers)
    rv = logged_in_client.get(f"/subscribe/{topic.id}", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/SocialSystem"
    updated_count = len(topic.subscribers)
    assert updated_count == initial_count

def test_subscribe_invalid_topic(logged_in_client):
    """
    Negative case 2: After logging in, accessing a non-existent topic_id should return a 404.
    """
    rv = logged_in_client.get("/subscribe/99999", follow_redirects=False)
    assert rv.status_code == 404

def count_subscriptions(topic_id: int) -> int:
    stmt = (
        sa.select(sa.func.count())
        .select_from(topic_subscribers)
        .where(topic_subscribers.c.topic_id == topic_id)
    )
    return db.session.execute(stmt).scalar_one()


def test_subscribe_requires_login(client):
    """
    Negative case: unauthenticated requests to subscribe should be
    redirected to the login page (302 -> /login).
    """
    # pick any existing topic
    topic = Topic.query.filter_by(name="General").one()
    rv = client.get(f"/subscribe/{topic.id}", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/login"


def test_unsubscribe_positive(logged_in_client):
    """
    Positive case: a logged-in user can unsubscribe from a topic they
    are subscribed to, and the subscriber count decreases by one.
    """
    topic = Topic.query.filter_by(name="General").one()
    before = count_subscriptions(topic.id)

    rv = logged_in_client.get(f"/unsubscribe/{topic.id}", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/SocialSystem"

    after = count_subscriptions(topic.id)
    assert after == before - 1


def test_unsubscribe_duplicate(logged_in_client):
    """
    Negative case: unsubscribing twice from the same topic should not error out,
    and the subscriber count remains unchanged on the second call.
    """
    topic = Topic.query.filter_by(name="General").one()
    before = count_subscriptions(topic.id)
    rv1 = logged_in_client.get(f"/unsubscribe/{topic.id}", follow_redirects=False)
    assert rv1.status_code == 302
    assert urlsplit(rv1.headers["Location"]).path == "/SocialSystem"
    mid = count_subscriptions(topic.id)
    assert mid == before - 1
    rv2 = logged_in_client.get(f"/unsubscribe/{topic.id}", follow_redirects=False)
    assert rv2.status_code == 302
    assert urlsplit(rv2.headers["Location"]).path == "/SocialSystem"
    after = count_subscriptions(topic.id)
    assert after == mid


def test_unsubscribe_requires_login(client):
    """
    Negative case: unauthenticated requests to unsubscribe should be
    redirected to the login page (302 -> /login).
    """
    topic = Topic.query.filter_by(name="General").one()
    rv = client.get(f"/unsubscribe/{topic.id}", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/login"


def test_unsubscribe_invalid_topic(logged_in_client):
    """
    Negative case: attempting to unsubscribe from a non-existent topic_id
    should return a 404 error.
    """
    rv = logged_in_client.get("/unsubscribe/99999", follow_redirects=False)
    assert rv.status_code == 404