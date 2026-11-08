from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app import orders

WAT = timezone(timedelta(hours=1))
VALID = {
    "merchant": "Ama's Fabrics",
    "recipient_phone": "+233 24 123 4567",
    "pickup_zone": "A",
    "dropoff_zone": "C",
    "weight_kg": "3.4",
    "speed": "standard",
}


def test_valid_request_is_parsed():
    req = orders.parse_request(VALID)
    assert req.pickup_zone == "A" and req.dropoff_zone == "C"
    assert req.weight_kg == 3.4 and req.fragile is False


@pytest.mark.parametrize(
    "field,value",
    [("merchant", "x"), ("recipient_phone", "abc"), ("pickup_zone", "Z"),
     ("weight_kg", "0"), ("weight_kg", "31"), ("weight_kg", "heavy"), ("speed", "teleport")],
)
def test_invalid_fields_are_reported(field, value):
    with pytest.raises(orders.OrderError) as exc:
        orders.parse_request({**VALID, field: value})
    assert field in exc.value.errors


def test_quote_adds_distance_weight_and_fragile_fees():
    req = orders.parse_request({**VALID, "fragile": "on"})
    q = orders.quote(req, now=datetime(2026, 11, 9, 10, 0, tzinfo=WAT))
    assert q.base == Decimal("2.50")
    assert q.distance_fee == Decimal("2.40")    # 2 rings crossed
    assert q.weight_fee == Decimal("0.80")      # 3.4 kg -> 2 extra kg
    assert q.handling_fee == Decimal("1.00")
    assert q.total == Decimal("6.70")


def test_standard_before_cutoff_arrives_same_evening():
    req = orders.parse_request(VALID)
    q = orders.quote(req, now=datetime(2026, 11, 9, 15, 59, tzinfo=WAT))
    assert (q.eta.day, q.eta.hour) == (9, 20)


def test_standard_after_cutoff_arrives_next_day():
    req = orders.parse_request(VALID)
    q = orders.quote(req, now=datetime(2026, 11, 9, 16, 0, tzinfo=WAT))
    assert (q.eta.day, q.eta.hour) == (10, 14)


def test_express_arrives_within_three_hours():
    req = orders.parse_request({**VALID, "speed": "express"})
    now = datetime(2026, 11, 9, 17, 30, tzinfo=WAT)
    assert orders.quote(req, now).eta == now + timedelta(hours=3)


def test_reference_format_avoids_ambiguous_characters():
    ref = orders.new_reference()
    assert ref.startswith("ONW-") and len(ref) == 13
    assert not set(ref[4:].replace("-", "")) & set("01ILO")
