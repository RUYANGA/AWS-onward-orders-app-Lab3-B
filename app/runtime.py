"""Which server answered: read from the EC2 instance metadata service (IMDSv2).

IMDSv2 needs a session token first; the launch template makes v2 mandatory and
limits the hop count to 1, so containers or proxies on the host cannot reach it.
"""
from __future__ import annotations

import os
import urllib.request
from functools import lru_cache

OWNER_NAME = os.environ.get("OWNER_NAME", "Merci RUYANGA")
LAB_NAME = "Handling Sales Day Demand"
_IMDS = "http://169.254.169.254/latest"


def version() -> str:
    commit = os.environ.get("APP_COMMIT", "")
    ref = os.environ.get("APP_VERSION", "local")
    return f"{ref}@{commit}" if commit else ref


def environment() -> str:
    return os.environ.get("ENVIRONMENT", "local")


def simulate_failure() -> bool:
    return os.environ.get("SIMULATE_FAILURE", "false").lower() == "true"


def _imds(path: str, token: str) -> str:
    req = urllib.request.Request(f"{_IMDS}/meta-data/{path}", headers={"X-aws-ec2-metadata-token": token})
    with urllib.request.urlopen(req, timeout=1) as resp:
        return resp.read().decode()


@lru_cache(maxsize=1)
def server_info() -> dict:
    """Instance ID, Availability Zone and private IP of this server."""
    try:
        req = urllib.request.Request(
            f"{_IMDS}/api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            token = resp.read().decode()
        return {
            "instance": _imds("instance-id", token),
            "az": _imds("placement/availability-zone", token),
            "ip": _imds("local-ipv4", token),
        }
    except OSError:
        return {"instance": "local", "az": "local", "ip": "127.0.0.1"}
