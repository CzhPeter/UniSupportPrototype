# file: test/test_views.py

import pytest
from urllib.parse import urlsplit

def test_login_page_get(client):
    """
    GET /login 应返回 200，并展示登录表单字段
    """
    rv = client.get("/login")
    assert rv.status_code == 200
    assert b'name="username"' in rv.data
    assert b'name="password"' in rv.data

def test_login_invalid_credentials(client):
    """
    POST 错误的用户名/密码，应该重定向回登录页，并闪现错误提示
    """
    rv = client.post(
        "/login",
        data={"username": "tom", "password": "wrong.pw"},
        follow_redirects=True
    )
    assert rv.status_code == 200
    assert b"Invalid username or password" in rv.data

def test_login_valid_credentials_redirect(client):
    """
    POST 正确的用户名/密码（tom / tom.pw），应该返回 302 到首页 (‘/’)
    """
    rv = client.post(
        "/login",
        data={"username": "tom", "password": "tom.pw"},
        follow_redirects=False
    )
    assert rv.status_code == 302
    # 断言跳转到首页
    loc = rv.headers["Location"]
    assert urlsplit(loc).path == "/"

def test_login_valid_credentials_follow_redirect(client):
    """
    同上，但直接 follow_redirects=True，最终应该拿到首页的 200
    并且页面标题中包含 Home
    """
    rv = client.post(
        "/login",
        data={"username": "tom", "password": "tom.pw"},
        follow_redirects=True
    )
    assert rv.status_code == 200
    assert b"<title>Home</title>" in rv.data

def test_logout_requires_login_and_redirects(logged_in_client):
    """
    对已登录的客户端访问 /logout，应该返回 302 并重定向到首页
    """
    rv = logged_in_client.get("/logout", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/"
