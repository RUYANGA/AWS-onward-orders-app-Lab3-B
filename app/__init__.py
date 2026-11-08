"""Onward order desk on EC2: one full-stack Flask application.

The user interface (server-rendered HTML) and the order logic (app.orders) are
served together by one process on every server.

Routes
  GET  /         order form; shows owner, lab name and which server answered
  POST /orders   price and confirm an order
  GET  /health   load balancer health check
  GET  /whoami   JSON: instance, AZ, IP, version (used by the demo scripts)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, render_template, request

from . import orders, runtime

WAT = timezone(timedelta(hours=1), "WAT")


def create_app() -> Flask:
    app = Flask(__name__)

    @app.context_processor
    def page_context():
        return {
            "owner_name": runtime.OWNER_NAME,
            "lab_name": runtime.LAB_NAME,
            "version": runtime.version(),
            "environment": runtime.environment(),
            "server": runtime.server_info(),
            "zones": orders.ZONES,
            "speeds": orders.SPEEDS,
        }

    @app.get("/")
    def index():
        return render_template("index.html", form={}, errors={})

    @app.post("/orders")
    def create_order():
        try:
            order = orders.place_order(request.form.to_dict(), now=datetime.now(WAT))
        except orders.OrderError as exc:
            return render_template("index.html", form=request.form, errors=exc.errors), 422
        return render_template("confirmation.html", order=order), 201

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/whoami")
    def whoami():
        return jsonify(version=runtime.version(), environment=runtime.environment(), **runtime.server_info())

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
        # Never cache, so every refresh goes back through the load balancer
        # and may be answered by a different server.
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Served-By"] = runtime.server_info()["instance"]
        return resp

    return app
