import pytest
from app import app as _app, db as _db
from config import Config
from app.debug_utils import reset_db
from app.models import User
from flask_login import login_user

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False


@pytest.fixture(scope="session")
def app():
    _app.config.from_object(TestConfig)
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()

@pytest.fixture(autouse=True)
def init_db(app):
    reset_db()
    yield

@pytest.fixture
def client(app):
    c = app.test_client(use_cookies=True)
    # 立即登出一次，清除可能残留的任何 cookie
    c.get("/logout", follow_redirects=True)
    return c

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def get_user():
    def _get(name):
        return User.query.filter_by(username=name).one()
    return _get

@pytest.fixture
def logged_in_client(app, get_user):
    user = get_user("tom")
    with app.test_request_context():
        login_user(user, remember=False, fresh=True)
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = user.get_id()
            sess['_fresh'] = True
    return client
