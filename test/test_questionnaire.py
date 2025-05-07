import pytest
import sqlalchemy as sa
from urllib.parse import urlsplit
from app import app, db
from app.models import Question, AnswerRecord, User


def count_answer_records(user_id: int, questionnaire_name: str) -> int:
    """
    Count AnswerRecord rows for a given user and questionnaire.
    """
    stmt = (
        sa.select(sa.func.count())
        .select_from(AnswerRecord)
        .where(AnswerRecord.user_id == user_id)
        .where(AnswerRecord.questionnaire_name == questionnaire_name)
    )
    return db.session.execute(stmt).scalar_one()


def test_questionnaire1_get(logged_in_client):
    """
    Positive case: logged-in user should see questionnaire 1.
    """
    rv = logged_in_client.get("/questionnaire1", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Psychological Survey 1" in rv.data


def test_questionnaire2_get(logged_in_client):
    """
    Positive case: logged-in user should see questionnaire 2.
    """
    rv = logged_in_client.get("/questionnaire2", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Psychological Survey 2" in rv.data


def test_questionnaire_unauthorized_access():
    """
    Negative case: unauthenticated user should be redirected to login.
    """
    with app.test_client() as client:
        client.get('/logout', follow_redirects=True)
        rv1 = client.get("/questionnaire1", follow_redirects=False)
        assert rv1.status_code == 302
        assert '/login' in rv1.headers['Location']
