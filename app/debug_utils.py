from app import db
from app.models import User,Question

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
