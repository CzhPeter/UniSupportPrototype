import pytest
from urllib.parse import urlsplit

def test_login_page_get(client):
    """
    GET /login should return a 200 status and display the login form fields.
    """
    rv = client.get("/login")
    assert rv.status_code == 200
    assert b'name="username"' in rv.data
    assert b'name="password"' in rv.data

def test_login_invalid_credentials(client):
    """
    POST with incorrect username/password should redirect back to the login page and flash an error message
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
    POST with correct username/password (tom / tom.pw) should return a 302 redirect to the homepage ('/')
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

def test_logout_requires_login_and_redirects(logged_in_client):
    """
    Accessing /logout with a logged-in client should return a 302 redirect to the homepage.
    """
    rv = logged_in_client.get("/logout", follow_redirects=False)
    assert rv.status_code == 302
    assert urlsplit(rv.headers["Location"]).path == "/"
