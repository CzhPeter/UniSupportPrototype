from app import db
from app.models import User, Topic,Question

def reset_db():
    db.drop_all()
    db.create_all()

    u1 = User(username='amy', email='a@b.com', role='Admin')
    u1.set_password('amy.pw')
    u2 = User(username='tom', email='t@b.com')
    u2.set_password('tom.pw')
    u3 = User(username='yin', email='y@b.com', role='Admin')
    u3.set_password('yin.pw')
    u4 = User(username='tariq', email='tariq@b.com')
    u4.set_password('tariq.pw')
    u5 = User(username='jo', email='jo@b.com')
    u5.set_password('jo.pw')

    db.session.add_all([u1, u2, u3, u4, u5])

    questions1 = [
        "Do you often feel tired?",
        "Do you frequently have trouble sleeping?",
        "Do you often feel sad or depressed?",
        "Do you feel anxious easily?",
        "Have you lost interest in activities you used to enjoy?",
        "Do you find it hard to concentrate?",
        "Do you feel overwhelmed by small matters?",
        "Do you experience frequent mood swings?",
        "Do you feel isolated even when around others?",
        "Do you often feel hopeless about the future?"
    ]

    for content in questions1:
        q = Question(questionnaire_name="Questionnaire 1", content=content)
        db.session.add(q)

    questions2 = [
        "Do you often feel lonely?",
        "Do you feel that life has no meaning?",
        "Do you frequently feel helpless?",
        "Do you get angry easily over trivial matters?",
        "Do you find it difficult to enjoy your daily activities?",
        "Do you often experience a loss of appetite?",
        "Do you feel exhausted even after resting?",
        "Do you worry excessively about the future?",
        "Do you often feel worthless?",
        "Do you find it hard to make decisions?"
    ]

    for content in questions2:
        q = Question(questionnaire_name="Questionnaire 2", content=content)
        db.session.add(q)

    db.session.commit()

    # Added for testing: create some topics
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

    # Added for testing: set up subscriptions
    for user in user_map.values():
        topic_map['General'].add_subscriber(user)
    for user in user_map.values():
        if user.role == 'Admin':
            topic_map['Announcements'].add_subscriber(user)

    # Added for testing: grant posting rights
    for name in ('tom', 'jo', 'tariq'):
        topic_map['General'].add_poster(user_map[name])
    for name in ('amy', 'yin'):
        topic_map['Announcements'].add_poster(user_map[name])

    db.session.commit()

    # Added for testing: create initial notifications
    topic_map['General'].post_notification(
        poster=user_map['tom'],
        content="Welcome to the General discussion!"
    )
    topic_map['Announcements'].post_notification(
        poster=user_map['amy'],
        content="System is now live. Stay tuned for updates."
    )
