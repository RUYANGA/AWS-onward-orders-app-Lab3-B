# onward-orders-app

The Onward Logistics order application: one full-stack Python app (Flask) that serves the
order form and the order logic together. It runs on the EC2 servers created by
[onward-orders-infrastructure](https://github.com/RUYANGA/onward-orders-infrastructure).

The page shows the owner's name, the lab name, and the instance ID, Availability Zone and
private IP of the server that answered (read from IMDSv2). Responses are never cached, so
each refresh goes back through the load balancer.

## Repository layout

```
app/                  the Flask application (routes, order validation, IMDSv2 lookup, templates)
tests/                pytest tests for the routes and order validation
wsgi.py               gunicorn entry point
gunicorn.conf.py      gunicorn settings for a t3.micro (port 8000)
requirements.txt      runtime dependencies (installed on the servers)
requirements-dev.txt  runtime + test dependencies
scripts/cpu_spike.py  time-limited CPU burner for the scaling demo, run on servers only via Run Command
```

## Routes

| Route | Purpose |
| --- | --- |
| `GET /` | order form; shows owner, lab name and which server answered |
| `POST /orders` | validates and confirms an order |
| `GET /health` | load balancer health check |
| `GET /whoami` | JSON: app version, environment and server details |

## Settings

The servers set these in `/etc/onward/app.env`; all are optional locally.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OWNER_NAME` | `Merci RUYANGA` | name shown on the page |
| `ENVIRONMENT` | `local` | `dev`, `test` or `prod` |
| `APP_VERSION` / `APP_COMMIT` | `local` | version shown on the page |

## Run locally

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt && python -m pytest -q
flask --app wsgi run --port 8000
```

## How it reaches the servers

At first boot each server clones this repository at the `AppVersion` set in
`deployments/dev/orders.yaml` in onward-orders-infrastructure, installs `requirements.txt`
into a virtualenv and runs gunicorn from the repository root. This repository must stay
**public** so the servers can clone it without credentials.

**Releasing a new version:** merge to `main`, tag it (for example `v1.1.0`), then set
`AppVersion: v1.1.0` in onward-orders-infrastructure and commit there. CloudFormation
replaces the servers one at a time.
