import pytest
from urllib.parse import urlsplit
import sqlalchemy as sa
from app import db
from app.models import Topic, Notification, NotificationRecipient

def count_notifications(topic_id: int) -> int:
    """
    Count Notification rows for a given topic_id.
    """
    stmt = (
        sa.select(sa.func.count())
        .select_from(Notification)
        .where(Notification.topic_id == topic_id)
    )
    return db.session.execute(stmt).scalar_one()

def count_recipients(topic_id: int) -> int:
    """
    Count NotificationRecipient rows for a given topic_id.
    """
    return (
        NotificationRecipient.query
        .join(Notification)
        .filter(Notification.topic_id == topic_id)
        .count()
    )


def test_topic_detail_get_host(logged_in_client):
    """
    Positive case: host user should see the notification form on GET.
    """
    topic = Topic.query.filter_by(name="General").one()
    rv = logged_in_client.get(f"/topic/{topic.id}", follow_redirects=False)
    assert rv.status_code == 200
    assert b'name="content"' in rv.data


def test_topic_detail_get_non_host(logged_in_client):
    """
    Negative case: non-host user should not see the form on GET.
    """
    # 'tom' is NOT a poster for 'Announcements'
    topic = Topic.query.filter_by(name="Announcements").one()
    rv = logged_in_client.get(f"/topic/{topic.id}", follow_redirects=False)
    assert rv.status_code == 200
    assert b'name="content"' not in rv.data


def test_post_notification_positive(logged_in_client):
    """
    Positive case: host user can post a notification.
    """
    topic = Topic.query.filter_by(name="General").one()
    before_notifs = count_notifications(topic.id)
    before_recips = count_recipients(topic.id)
    num_subs = len(topic.subscribers)

    rv = logged_in_client.post(
        f"/topic/{topic.id}",
        data={"content": "Test notification"},
        follow_redirects=False
    )
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == f"/topic/{topic.id}"

    assert count_notifications(topic.id) == before_notifs + 1
    assert count_recipients(topic.id) == before_recips + num_subs


def test_post_notification_validation_error(logged_in_client):
    """
    Negative case: host user submits empty content -> validation fails.
    """
    topic = Topic.query.filter_by(name="General").one()
    before_notifs = count_notifications(topic.id)
    before_recips = count_recipients(topic.id)

    rv = logged_in_client.post(
        f"/topic/{topic.id}",
        data={"content": ""},
        follow_redirects=False
    )
    assert rv.status_code == 200

    assert count_notifications(topic.id) == before_notifs
    assert count_recipients(topic.id) == before_recips


def test_post_notification_unauthorized(logged_in_client):
    """
    Negative case: non-host user cannot post; page is re-rendered.
    """
    topic = Topic.query.filter_by(name="Announcements").one()
    before_notifs = count_notifications(topic.id)
    before_recips = count_recipients(topic.id)

    rv = logged_in_client.post(
        f"/topic/{topic.id}",
        data={"content": "Not allowed"},
        follow_redirects=False
    )
    assert rv.status_code == 200

    assert count_notifications(topic.id) == before_notifs
    assert count_recipients(topic.id) == before_recips


def test_post_notification_invalid_topic(logged_in_client):
    """
    Negative case: posting to non-existent topic_id returns 404.
    """
    rv = logged_in_client.post(
        "/topic/99999",
        data={"content": "Irrelevant"},
        follow_redirects=False
    )
    assert rv.status_code == 404
