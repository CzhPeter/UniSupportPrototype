# file: test/conftest.py

import pytest
from app import app as _app, db as _db
from config import Config
from app.debug_utils import reset_db
from app.models import User

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
    """
    在每个测试函数之前，调用 reset_db()：
      - 清空并重建所有表
      - 插入预定义的用户/问题/话题/通知
    这样每个测试都在相同的初始数据状态下运行，互不干扰。
    """
    reset_db()
    yield

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def get_user():
    """
    返回一个函数，接受用户名，查询并返回当前会话中的 User 实例。
    """
    def _get(name):
        return User.query.filter_by(username=name).one()
    return _get

@pytest.fixture
def logged_in_client(client, get_user):
    """
    默认用 reset_db 插入的 tom 账号来登录。
    """
    user = get_user("tom")
    client.post(
        "/login",
        data={"username": user.username, "password": "tom.pw"},
        follow_redirects=True
    )
    return client
