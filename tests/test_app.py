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


def test_invalid_order_shows_error_summary_and_marks_fields(client):
    resp = client.post("/orders", data={"merchant": "", "recipient_phone": "12", "speed": "express"})
    body = resp.get_data(as_text=True)
    assert resp.status_code == 422
    assert "Please fix" in body and 'href="#merchant"' in body
    assert 'aria-invalid="true"' in body and 'id="merchant-error"' in body
    assert 'value="express" checked' in body  # the chosen speed is kept


def test_form_shows_speed_options_and_pricing(client):
    body = client.get("/").get_data(as_text=True)
    assert 'id="speed-standard"' in body and 'id="speed-express"' in body
    assert "How pricing works" in body and "$1.20" in body


def test_confirmation_shows_route_and_total(client):
    body = client.post("/orders", data={
        "merchant": "Kofi Phones", "recipient_phone": "+2348012345678", "pickup_zone": "A",
        "dropoff_zone": "C", "weight_kg": "3.2", "speed": "standard", "fragile": "on"}).get_data(as_text=True)
    # base 2.50 + 2 rings x 1.20 + 2 extra kg x 0.40 + fragile 1.00 = 6.70
    assert "Delivery booked" in body and "$6.70" in body
    assert "Area A · Central" in body and "Area C · Outer suburbs" in body


def test_unknown_page_uses_the_styled_error_page(client):
    resp = client.get("/nope")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 404 and "Page not found" in body
    assert "i-0abc123" in body and resp.headers["Cache-Control"] == "no-store"


def test_wrong_method_uses_the_styled_error_page(client):
    resp = client.get("/orders")
    assert resp.status_code == 405 and "Use the booking form" in resp.get_data(as_text=True)
