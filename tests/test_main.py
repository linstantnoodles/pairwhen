import os
import tempfile
import pytest
from main import app, get_db
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            get_db()
        yield client

def create_user(email, password):
    with app.app_context():
        db = get_db()
        with db.cursor() as cursor:
            sql = "INSERT INTO `users` (`email`, `password`) VALUES (%s, %s)"
            cursor.execute(sql, (email, generate_password_hash(password)))
        db.commit()

def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/')
    assert b'No entries here so far' in rv.data

def test_login_logout(client):
    """Make sure login and logout works."""
    existing_email = "test-user"
    existing_password = "test-pw"
    create_user(existing_email, existing_password)

    rv = login(client, existing_email, existing_password)
    assert b'You were logged in' in rv.data
    rv = logout(client)
    assert b'You were logged out' in rv.data
