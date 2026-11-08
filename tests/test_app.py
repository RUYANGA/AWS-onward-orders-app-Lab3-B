import pytest

import app.runtime as runtime
from app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(runtime, "OWNER_NAME", "Test Owner")
    runtime.server_info.cache_clear()
    monkeypatch.setattr(runtime, "server_info", lambda: {"instance": "i-0abc123", "az": "eu-west-1a", "ip": "10.30.10.5"})
    return create_app().test_client()


def test_home_shows_owner_lab_and_server(client):
    body = client.get("/").get_data(as_text=True)
    for text in ("Test Owner", "Handling Sales Day Demand", "i-0abc123", "eu-west-1a", "10.30.10.5"):
        assert text in body


def test_pages_are_not_cached_and_name_the_server(client):
    resp = client.get("/")
    assert resp.headers["Cache-Control"] == "no-store"
    assert resp.headers["X-Served-By"] == "i-0abc123"


def test_health_and_whoami(client):
    assert client.get("/health").status_code == 200
    assert client.get("/whoami").json["instance"] == "i-0abc123"


def test_order_is_confirmed(client):
    resp = client.post("/orders", data={
        "merchant": "Kofi Phones", "recipient_phone": "+2348012345678",
        "pickup_zone": "B", "dropoff_zone": "D", "weight_kg": "1", "speed": "express"})
    assert resp.status_code == 201 and "ONW-" in resp.get_data(as_text=True)


def test_runtime_falls_back_off_ec2():
    runtime.server_info.cache_clear()
    assert runtime.server_info()["instance"] in {"local"} or runtime.server_info()["instance"].startswith("i-")
