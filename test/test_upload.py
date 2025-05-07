import io
import os
from flask import url_for
from app import app

def test_upload_positive(logged_in_admin):
    """
    Positive case:
    - Upload a valid .txt file
    - Returns 200 and success message in response HTML
    - The file should be saved to the upload folder
    """
    app.config["WTF_CSRF_ENABLED"] = False
    test_filename = "test_file.txt"
    data = {
        "file": (io.BytesIO(b"This is a test file."), test_filename),
        "submit": True
    }

    rv = logged_in_admin.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert rv.status_code == 200
    assert f"{test_filename} is uploaded successfully" in rv.get_data(as_text=True)

    uploaded_path = os.path.join(app.config["UPLOAD_FOLDER"], test_filename)
    assert os.path.exists(uploaded_path)

    # Clean up uploaded file
    os.remove(uploaded_path)


def test_upload_negative_invalid_filetype(logged_in_admin):
    """
    Negative case:
    - Try to upload a .exe file (which is not allowed)
    - Should not upload, and response should indicate validation failure
    """
    app.config["WTF_CSRF_ENABLED"] = False
    data = {
        "file": (io.BytesIO(b"This is not allowed."), "malicious.exe"),
        "submit": True
    }

    rv = logged_in_admin.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert b"This is not allowed." not in rv.data
    assert rv.status_code == 200
    assert "Upload files" in rv.get_data(as_text=True)


def test_upload_access_denied_for_normal_user(logged_in_client, get_user):
    """
    Negative case:
    - A logged-in user with role 'Normal' (e.g., 'tom') tries to access /upload
    - Should return 403 Forbidden
    """
    user = get_user("tom")
    assert user.role == "Normal"

    rv = logged_in_client.get("/upload")
    assert rv.status_code == 403