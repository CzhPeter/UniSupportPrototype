from app import db
from app.models import User, Topic
import datetime


def reset_db():
    db.drop_all()
    db.create_all()

    users =[
        {'username': 'amy',   'email': 'amy@b.com', 'role': 'Admin', 'pw': 'amy.pw'},
        {'username': 'tom',   'email': 'tom@b.com',                  'pw': 'amy.pw'},
        {'username': 'yin',   'email': 'yin@b.com', 'role': 'Admin', 'pw': 'amy.pw'},
        {'username': 'tariq', 'email': 'trq@b.com',                  'pw': 'amy.pw'},
        {'username': 'jo',    'email': 'jo@b.com',                   'pw': 'amy.pw'}
    ]

    for u in users:
        # get the password value and remove it from the dict:
        pw = u.pop('pw')
        # create a new user object using the parameters defined by the remaining entries in the dict:
        user = User(**u)
        # set the password for the user object:
        user.set_password(pw)
        # add the newly created user object to the database session:
        db.session.add(user)
    db.session.commit()

    # --- Added for testing: create some topics ---
    topics_data = [
        {'name': 'General', 'description': 'General discussion area'},
        {'name': 'Announcements', 'description': 'Official announcements'}
    ]
    for t in topics_data:
        topic = Topic(name=t['name'], description=t['description'])
        db.session.add(topic)
    db.session.commit()

    # load objects into dicts for convenience
    user_map = {u.username: u for u in User.query.all()}
    topic_map = {t.name: t for t in Topic.query.all()}

    # --- Added for testing: set up subscriptions ---
    # everyone subscribes to "General"
    for user in user_map.values():
        topic_map['General'].add_subscriber(user)
    # only admins subscribe to "Announcements"
    for user in user_map.values():
        if user.role == 'Admin':
            topic_map['Announcements'].add_subscriber(user)

    # --- Added for testing: grant posting rights ---
    # tom, jo, tariq can post in General
    for name in ('tom', 'jo', 'tariq'):
        topic_map['General'].add_poster(user_map[name])
    # amy, yin can post in Announcements
    for name in ('amy', 'yin'):
        topic_map['Announcements'].add_poster(user_map[name])

    db.session.commit()

    # --- Added for testing: create initial notifications ---
    topic_map['General'].post_notification(
        poster=user_map['tom'],
        content="Welcome to the General discussion!"
    )
    topic_map['Announcements'].post_notification(
        poster=user_map['amy'],
        content="System is now live. Stay tuned for updates."
    )
