import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = True  # <-- Add this
    with app.test_client() as client:
        yield client

def test_index(client):
    """Home/index loads successfully"""
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Home" in html
    # Check that summary cards exist
#    assert "Parkruns Analysed" in html
#    assert "Runners in Dataset" in html

def test_404(client):
    response = client.get("/nonexistent-page")
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Page Not Found" in html or "404" in html

def TODO_test_index_500(monkeypatch):
    client = app.test_client()

    # Monkeypatch the index function to raise an exception
    def fake_index():
        raise Exception("Simulated 500 error")

    monkeypatch.setattr("website.app.index", fake_index)

    # Calling the "/" route now triggers the 500 error
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Internal Server Error" in html or "Oops" in html
