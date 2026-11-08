"""Order logic for the Onward order desk.

Pure functions only: no web framework, no I/O. That keeps the business rules
easy to test and lets every container answer identically, which matters
because the load balancer may send each request to a different container.

Pricing model (lab simplification, prices in USD):
  * Service areas are rings around the hub: A (core) to D (outer).
  * Base fee depends on speed; each ring crossed adds a fee.
  * The first 2 kg are included; each extra kg (rounded up) is charged.
  * Fragile parcels pay a handling fee.
"""
from __future__ import annotations

import math
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

ZONES: dict[str, dict] = {
    "A": {"label": "A, central (hub district)", "ring": 0},
    "B": {"label": "B, inner suburbs", "ring": 1},
    "C": {"label": "C, outer suburbs", "ring": 2},
    "D": {"label": "D, peri-urban", "ring": 3},
}

SPEEDS: dict[str, dict] = {
    "standard": {"label": "Standard (same day if booked before 16:00)", "base": Decimal("2.50")},
    "express": {"label": "Express (within 3 hours)", "base": Decimal("4.50")},
}

RING_FEE = Decimal("1.20")
INCLUDED_KG = 2
EXTRA_KG_FEE = Decimal("0.40")
FRAGILE_FEE = Decimal("1.00")
MIN_WEIGHT_KG = 0.1
MAX_WEIGHT_KG = 30.0
STANDARD_CUTOFF_HOUR = 16
EXPRESS_HOURS = 3

# Unambiguous characters only (no 0/O, 1/I/L), so riders can read references aloud.
_REF_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_PHONE_RE = re.compile(r"^\+?[0-9 ]{8,16}$")


class OrderError(ValueError):
    """Raised when an order request breaks a business rule."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


@dataclass(frozen=True)
class OrderRequest:
    merchant: str
    recipient_phone: str
    pickup_zone: str
    dropoff_zone: str
    weight_kg: float
    speed: str
    fragile: bool = False


@dataclass(frozen=True)
class Quote:
    base: Decimal
    distance_fee: Decimal
    weight_fee: Decimal
    handling_fee: Decimal
    eta: datetime

    @property
    def total(self) -> Decimal:
        return self.base + self.distance_fee + self.weight_fee + self.handling_fee


@dataclass(frozen=True)
class Order:
    reference: str
    request: OrderRequest
    quote: Quote


def parse_request(form: dict) -> OrderRequest:
    """Turn raw form input into a validated OrderRequest, or raise OrderError."""
    errors: dict[str, str] = {}

    merchant = (form.get("merchant") or "").strip()
    if not 2 <= len(merchant) <= 80:
        errors["merchant"] = "Enter the merchant name (2 to 80 characters)."

    phone = (form.get("recipient_phone") or "").strip()
    if not _PHONE_RE.match(phone):
        errors["recipient_phone"] = "Enter a phone number with 8 to 15 digits, for example +233 24 123 4567."

    pickup = (form.get("pickup_zone") or "").upper()
    dropoff = (form.get("dropoff_zone") or "").upper()
    if pickup not in ZONES:
        errors["pickup_zone"] = "Choose a pickup area."
    if dropoff not in ZONES:
        errors["dropoff_zone"] = "Choose a delivery area."

    speed = (form.get("speed") or "").lower()
    if speed not in SPEEDS:
        errors["speed"] = "Choose standard or express."

    weight: float = 0.0
    try:
        weight = float(form.get("weight_kg") or "")
        if not MIN_WEIGHT_KG <= weight <= MAX_WEIGHT_KG:
            raise ValueError
    except ValueError:
        errors["weight_kg"] = f"Enter a weight between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG:g} kg."

    if errors:
        raise OrderError(errors)

    return OrderRequest(
        merchant=merchant,
        recipient_phone=phone,
        pickup_zone=pickup,
        dropoff_zone=dropoff,
        weight_kg=weight,
        speed=speed,
        fragile=str(form.get("fragile", "")).lower() in {"on", "true", "1", "yes"},
    )


def quote(req: OrderRequest, now: datetime) -> Quote:
    """Price a delivery and estimate its arrival time."""
    rings_crossed = abs(ZONES[req.pickup_zone]["ring"] - ZONES[req.dropoff_zone]["ring"])
    extra_kg = max(0, math.ceil(req.weight_kg - INCLUDED_KG))

    if req.speed == "express":
        eta = now + timedelta(hours=EXPRESS_HOURS)
    elif now.hour < STANDARD_CUTOFF_HOUR:
        eta = now.replace(hour=20, minute=0, second=0, microsecond=0)
    else:
        eta = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)

    return Quote(
        base=SPEEDS[req.speed]["base"],
        distance_fee=RING_FEE * rings_crossed,
        weight_fee=EXTRA_KG_FEE * extra_kg,
        handling_fee=FRAGILE_FEE if req.fragile else Decimal("0.00"),
        eta=eta,
    )


def new_reference(rand: secrets.SystemRandom | None = None) -> str:
    """Create an order reference such as ONW-7KQ2-MX9A."""
    rng = rand or secrets.SystemRandom()
    chars = "".join(rng.choice(_REF_ALPHABET) for _ in range(8))
    return f"ONW-{chars[:4]}-{chars[4:]}"


def place_order(form: dict, now: datetime) -> Order:
    req = parse_request(form)
    return Order(reference=new_reference(), request=req, quote=quote(req, now))
